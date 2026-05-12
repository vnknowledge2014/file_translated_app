import logging
from urllib.parse import urlparse
from typing import Generator
import base64

from minio import Minio
from minio.error import S3Error
from minio.sse import SseCustomerKey
from minio.commonconfig import Filter
from minio.lifecycleconfig import LifecycleConfig, Rule, Expiration

from app.config import settings

logger = logging.getLogger(__name__)


class StorageClient:
    def __init__(self):
        # Parse URL to get host:port and secure flag
        parsed_url = urlparse(settings.MINIO_URL)
        endpoint = parsed_url.netloc
        secure = parsed_url.scheme == "https"

        self.client = Minio(
            endpoint,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=secure,
        )
        self.uploads_bucket = "uploads"
        self.outputs_bucket = "outputs"

        # Configure SSE-C key if provided AND connection is HTTPS
        # SSE-C requires HTTPS — MinIO will reject SSE-C requests over plain HTTP.
        self.sse_key = None
        if settings.STORAGE_ENCRYPTION_KEY:
            if secure:
                try:
                    key_bytes = base64.b64decode(settings.STORAGE_ENCRYPTION_KEY)
                    self.sse_key = SseCustomerKey(key_bytes)
                    logger.info("SSE-C encryption enabled (HTTPS connection)")
                except Exception as e:
                    logger.error(f"Invalid STORAGE_ENCRYPTION_KEY: {e}")
                    raise
            else:
                logger.warning(
                    "STORAGE_ENCRYPTION_KEY is set but MinIO connection is HTTP (not HTTPS). "
                    "SSE-C encryption is DISABLED. To enable, use MINIO_URL=https://..."
                )

    def init_buckets(self):
        """Initialize required buckets if they don't exist."""
        try:
            # Configure bucket lifecycle rule
            config = None
            if settings.FILE_RETENTION_DAYS > 0:
                config = LifecycleConfig(
                    [
                        Rule(
                            "Enabled",
                            rule_filter=Filter(prefix=""),
                            rule_id=f"auto-delete-{settings.FILE_RETENTION_DAYS}d",
                            expiration=Expiration(days=settings.FILE_RETENTION_DAYS),
                        )
                    ]
                )

            for bucket in [self.uploads_bucket, self.outputs_bucket]:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    logger.info(f"Created MinIO bucket: {bucket}")
                else:
                    logger.debug(f"MinIO bucket {bucket} already exists.")

                # Apply lifecycle config
                if config:
                    try:
                        self.client.set_bucket_lifecycle(bucket, config)
                        logger.info(
                            f"Applied {settings.FILE_RETENTION_DAYS}-day retention policy to {bucket}"
                        )
                    except S3Error as e:
                        logger.error(f"Failed to set lifecycle on {bucket}: {e}")
        except S3Error as e:
            logger.error(f"Failed to initialize MinIO buckets: {e}")
            raise

    def upload_file(self, bucket_name: str, object_name: str, file_path: str) -> str:
        """Upload a local file to MinIO bucket. Returns the object URI (s3://bucket/object)."""
        try:
            self.client.fput_object(
                bucket_name, object_name, file_path, sse=self.sse_key
            )
            return f"s3://{bucket_name}/{object_name}"
        except S3Error as e:
            logger.error(
                f"Error uploading {file_path} to {bucket_name}/{object_name}: {e}"
            )
            raise

    def download_file(self, bucket_name: str, object_name: str, file_path: str):
        """Download an object from MinIO to a local file path."""
        try:
            self.client.fget_object(
                bucket_name, object_name, file_path, ssec=self.sse_key
            )
        except S3Error as e:
            logger.error(
                f"Error downloading {bucket_name}/{object_name} to {file_path}: {e}"
            )
            raise

    def get_object_stream(
        self, bucket_name: str, object_name: str
    ) -> Generator[bytes, None, None]:
        """Get an object as a stream (generator) for streaming responses."""
        response = None
        try:
            response = self.client.get_object(
                bucket_name, object_name, ssec=self.sse_key
            )
            for chunk in response.stream(32 * 1024):
                yield chunk
        except S3Error as e:
            logger.error(f"Error streaming {bucket_name}/{object_name}: {e}")
            raise
        finally:
            if response:
                response.release_conn()

    def delete_object(self, bucket_name: str, object_name: str) -> bool:
        """Delete an object from a MinIO bucket. Returns True if deleted, False if not found."""
        try:
            self.client.remove_object(bucket_name, object_name)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            logger.error(f"Error deleting {bucket_name}/{object_name}: {e}")
            raise

    def object_exists(self, bucket_name: str, object_name: str) -> bool:
        """Check if an object exists in a MinIO bucket."""
        try:
            self.client.stat_object(bucket_name, object_name, ssec=self.sse_key)
            return True
        except S3Error:
            return False

    def delete_job_outputs(self, job_id: str) -> int:
        """Delete all output files for a job (output + xliff) from the outputs bucket."""
        deleted = 0
        try:
            objects = list(
                self.client.list_objects(
                    self.outputs_bucket, prefix=f"{job_id}/", recursive=True
                )
            )
            for obj in objects:
                self.client.remove_object(self.outputs_bucket, obj.object_name)
                deleted += 1
        except S3Error as e:
            logger.warning(f"Error cleaning outputs for job {job_id}: {e}")
        return deleted

    def parse_s3_uri(self, s3_uri: str) -> tuple[str, str]:
        """Parse an s3://bucket/object URI into (bucket, object_name)."""
        if not s3_uri.startswith("s3://"):
            raise ValueError(f"Invalid S3 URI: {s3_uri}")
        parts = s3_uri[5:].split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid S3 URI format: {s3_uri}")
        return parts[0], parts[1]


# Global storage client
storage = StorageClient()
