"""Deterministic document reconstruction — per-format modules.

Public API (backward compatible):
    - reconstruct_document(file_type, file_path, segments, output_path)
    - reconstruct_plaintext(file_path, segments, output_path)
    - reconstruct_xlsx(file_path, segments, output_path)
    - reconstruct_docx(file_path, segments, output_path)
    - reconstruct_pptx(file_path, segments, output_path)

Internal modules:
    - _common: Shared pure functions (translation map, text matching)
    - _ooxml: Shared OOXML XML processing (namespaces, run serialization)
    - xlsx: Excel-specific logic
    - docx: Word-specific logic
    - pptx: PowerPoint-specific logic
    - plaintext: txt/md/csv logic
"""

from .plaintext import reconstruct_plaintext
from .xlsx import reconstruct_xlsx
from .docx import reconstruct_docx
from .pptx import reconstruct_pptx

# Also re-export internal utilities used by tests
from ._common import build_translation_map as _build_translation_map
from ._common import replace_in_text as _replace_in_text

RECONSTRUCTORS = {
    "docx": reconstruct_docx,
    "xlsx": reconstruct_xlsx,
    "pptx": reconstruct_pptx,
}


def reconstruct_document(
    file_type: str, file_path: str, segments: list[dict], output_path: str
) -> str:
    """Dispatch to the correct deterministic reconstructor.

    Args:
        file_type: File type string (docx, xlsx, pptx).
        file_path: Path to original file.
        segments: Translated segments.
        output_path: Target output path.

    Returns:
        Path to reconstructed file.

    Raises:
        ValueError: If file_type has no deterministic reconstructor.
    """
    func = RECONSTRUCTORS.get(file_type)
    if func is None:
        raise ValueError(f"No deterministic reconstructor for: {file_type}")
    return func(file_path, segments, output_path)


__all__ = [
    "reconstruct_document",
    "reconstruct_plaintext",
    "reconstruct_xlsx",
    "reconstruct_docx",
    "reconstruct_pptx",
    # Internal utilities (used by tests)
    "_build_translation_map",
    "_replace_in_text",
]
