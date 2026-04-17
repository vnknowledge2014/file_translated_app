"""DOCX (Word) deterministic reconstruction.

Strategy: Read original ZIP → replace JP text in all word/*.xml → write new ZIP.
Processes: document.xml, headers, footers, footnotes, endnotes.
All formatting (runs, styles, headers, footers, tables, textboxes) are preserved.
"""

from __future__ import annotations

import logging
import os
import shutil
import xml.etree.ElementTree as ET
import zipfile

from ._common import build_translation_map
from ._ooxml import NS, preserve_xml_declaration, replace_paragraph_runs

logger = logging.getLogger(__name__)

# DOCX text-bearing XML file patterns
_DOCX_XML_PATTERNS = [
    "word/document.xml",
    "word/header",
    "word/footer",
    "word/footnotes.xml",
    "word/endnotes.xml",
]


def _is_docx_xml(filename: str) -> bool:
    """Check if filename is a DOCX XML file that may contain translatable text."""
    if not filename.endswith(".xml"):
        return False
    return any(
        filename.startswith(pattern) or filename == pattern
        for pattern in _DOCX_XML_PATTERNS
    )


def reconstruct_docx(file_path: str, segments: list[dict], output_path: str) -> str:
    """Deterministic DOCX reconstruction.

    Processes all text-bearing XML files including:
    - Main document (word/document.xml)
    - Headers (word/header*.xml)
    - Footers (word/footer*.xml)
    - Footnotes (word/footnotes.xml)
    - Endnotes (word/endnotes.xml)

    Handles: paragraphs, tables, textboxes, shapes.

    Args:
        file_path: Path to original .docx file.
        segments: Translated segments with 'text' and 'translated_text'.
        output_path: Target output path.

    Returns:
        Path to reconstructed file.
    """
    tmap = build_translation_map(segments)
    if not tmap:
        shutil.copy2(file_path, output_path)
        return output_path

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    replaced = 0

    with (
        zipfile.ZipFile(file_path, "r") as zin,
        zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zout,
    ):
        for item in zin.infolist():
            buffer = zin.read(item.filename)

            # Process all DOCX XML files that may contain text
            if _is_docx_xml(item.filename):
                try:
                    root = ET.fromstring(buffer)
                    para_tag = f"{{{NS['w']}}}p"
                    r_tag = f"{{{NS['w']}}}r"
                    t_tag = f"{{{NS['w']}}}t"

                    count = replace_paragraph_runs(
                        root,
                        tmap,
                        para_tag,
                        r_tag,
                        t_tag,
                        "w",
                    )
                    if count > 0:
                        buffer = preserve_xml_declaration(root, buffer)
                        replaced += count

                except ET.ParseError as e:
                    logger.warning(f"XML parse error for {item.filename}: {e}")
                except Exception as e:
                    logger.error(f"Error processing {item.filename}: {e}")

            zout.writestr(item, buffer)

    logger.info(f"DOCX reconstruction: {replaced} replacements → {output_path}")
    return output_path
