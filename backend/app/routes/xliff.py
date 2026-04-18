"""XLIFF routes — import reviewed XLIFF and download XLIFF for jobs."""

import logging
import os
import tempfile

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse

from app.agent.extractor import extract_document
from app.agent.reconstructor import reconstruct_document, reconstruct_plaintext
from app.agent.xliff import import_xliff, merge_xliff_into_segments, export_xliff
from app.config import settings
from app.utils.file_detect import detect_file_type

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/import-xliff")
async def import_xliff_route(
    xliff_file: UploadFile = File(..., description="Reviewed XLIFF (.xlf) file"),
    original_file: UploadFile = File(..., description="Original source document"),
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
    file_type = detect_file_type(original_filename)
    if not file_type:
        return {"error": f"Unsupported file type: {original_filename}"}

    # Save files
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    original_path = os.path.join(upload_dir, original_filename)
    with open(original_path, "wb") as f:
        f.write(await original_file.read())

    xliff_path = os.path.join(upload_dir, xliff_file.filename or "import.xlf")
    with open(xliff_path, "wb") as f:
        f.write(await xliff_file.read())

    try:
        # Extract → Import XLIFF → Merge → Reconstruct
        segments = extract_document(file_type, original_path)
        xliff_segs = import_xliff(xliff_path)
        segments = merge_xliff_into_segments(segments, xliff_segs)

        base, ext = os.path.splitext(original_filename)
        output_filename = f"{base}_vi{ext}"
        output_path = os.path.join(settings.OUTPUT_DIR, output_filename)
        os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

        if file_type in ("txt", "md", "csv"):
            reconstruct_plaintext(original_path, segments, output_path)
        else:
            reconstruct_document(file_type, original_path, segments, output_path)

        return FileResponse(
            output_path,
            media_type="application/octet-stream",
            filename=output_filename,
        )

    except Exception as e:
        logger.error(f"XLIFF import failed: {e}", exc_info=True)
        return {"error": str(e)}
