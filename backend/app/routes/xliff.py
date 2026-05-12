"""XLIFF routes — import reviewed XLIFF and download XLIFF for jobs."""

import logging
import os

import uuid

from fastapi import APIRouter, File, UploadFile, Depends
from fastapi.responses import StreamingResponse

from app.auth import get_current_user

from app.agent.extractor import extract_document
from app.agent.reconstructor import reconstruct_document, reconstruct_plaintext
from app.agent.xliff import import_xliff, merge_xliff_into_segments
from app.config import settings
from app.utils.file_detect import detect_file_type

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/import-xliff")
async def import_xliff_route(
    xliff_file: UploadFile = File(..., description="Reviewed XLIFF (.xlf) file"),
    original_file: UploadFile = File(..., description="Original source document"),
    current_user: dict = Depends(get_current_user),
):
    """Import reviewed XLIFF and reconstruct translated document.

    Steps:
    1. Save both files to temp
    2. Extract segments from original
    3. Import XLIFF translations
    4. Merge translations into segments
    5. Reconstruct output document

    Returns:
        Translated file as download.
    """
    original_filename = original_file.filename or "unknown"
    safe_filename = original_filename.replace("/", "").replace("\\", "")
    file_type = detect_file_type(safe_filename)
    if not file_type:
        return {"error": f"Unsupported file type: {safe_filename}"}

    from app.storage import storage

    # Save files with UUID prefix to TEMP_DIR
    temp_dir = settings.TEMP_DIR
    os.makedirs(temp_dir, exist_ok=True)

    unique_prefix = uuid.uuid4().hex[:8]

    original_path = os.path.join(temp_dir, f"{unique_prefix}_{safe_filename}")
    with open(original_path, "wb") as f:
        f.write(await original_file.read())

    safe_xliff = (
        (xliff_file.filename or "import.xlf").replace("/", "").replace("\\", "")
    )
    xliff_path = os.path.join(temp_dir, f"{unique_prefix}_{safe_xliff}")
    with open(xliff_path, "wb") as f:
        f.write(await xliff_file.read())

    try:
        # Extract → Import XLIFF → Merge → Reconstruct
        segments = extract_document(file_type, original_path)
        xliff_segs = import_xliff(xliff_path)
        segments = merge_xliff_into_segments(segments, xliff_segs)

        base, ext = os.path.splitext(safe_filename)
        output_filename = f"{unique_prefix}_{base}_vi{ext}"
        temp_output_path = os.path.join(temp_dir, output_filename)

        if file_type in ("txt", "md", "csv"):
            reconstruct_plaintext(original_path, segments, temp_output_path)
        else:
            reconstruct_document(file_type, original_path, segments, temp_output_path)

        # Upload reconstructed file to MinIO
        final_s3_uri = storage.upload_file(
            storage.outputs_bucket, f"xliff_imports/{output_filename}", temp_output_path
        )
        logger.info(f"XLIFF import reconstructed → {final_s3_uri}")

        # Stream back to user
        return StreamingResponse(
            storage.get_object_stream(
                storage.outputs_bucket, f"xliff_imports/{output_filename}"
            ),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{base}_vi{ext}"'},
        )

    except Exception as e:
        logger.error(f"XLIFF import failed: {e}", exc_info=True)
        return {"error": str(e)}
    finally:
        for p in [
            original_path,
            xliff_path,
            temp_output_path if "temp_output_path" in locals() else None,
        ]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
