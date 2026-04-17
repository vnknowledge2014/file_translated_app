"""PPTX (PowerPoint) deterministic reconstruction.

Strategy: Read original ZIP → replace JP text in all ppt/*.xml → write new ZIP.
Processes: slides, slideLayouts, slideMasters, notesSlides, presentation.xml
All formatting (runs, styles, layouts, slide masters, tables, shapes) are preserved.
"""

from __future__ import annotations

import logging
import os
import shutil
import xml.etree.ElementTree as ET
import zipfile

from ._common import build_translation_map
from ._ooxml import NS, preserve_xml_declaration, register_document_namespaces, replace_paragraph_runs

logger = logging.getLogger(__name__)

# PPTX text-bearing XML file patterns
_PPTX_XML_PATTERNS = [
    "ppt/slides/",
    "ppt/slideLayouts/",
    "ppt/slideMasters/",
    "ppt/notesSlides/",
    "ppt/presentation.xml",
    "ppt/handoutMasters/",
    "ppt/notesMasters/",
]


def _is_pptx_xml(filename: str) -> bool:
    """Check if filename is a PPTX XML file that may contain translatable text."""
    if not filename.endswith(".xml"):
        return False
    return any(filename.startswith(pattern) for pattern in _PPTX_XML_PATTERNS)


def reconstruct_pptx(file_path: str, segments: list[dict], output_path: str) -> str:
    """Deterministic PPTX reconstruction.

    Processes all text-bearing XML files including:
    - Slides (ppt/slides/slide*.xml)
    - Slide layouts (ppt/slideLayouts/*.xml)
    - Slide masters (ppt/slideMasters/*.xml)
    - Notes slides (ppt/notesSlides/*.xml)
    - Presentation.xml (slide titles, notes)
    - Handout masters, notes masters

    Handles: paragraphs, tables, shapes, textboxes, SmartArt containers.

    Args:
        file_path: Path to original .pptx file.
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

            # Process all PPTX XML files that may contain text
            if _is_pptx_xml(item.filename):
                try:
                    register_document_namespaces(buffer)
                    root = ET.fromstring(buffer)

                    # Process paragraphs in slides/layouts/masters
                    # This handles: shapes, textboxes, table cells, SmartArt
                    para_tag = f"{{{NS['a']}}}p"
                    r_tag = f"{{{NS['a']}}}r"
                    t_tag = f"{{{NS['a']}}}t"

                    count = replace_paragraph_runs(
                        root,
                        tmap,
                        para_tag,
                        r_tag,
                        t_tag,
                        "a",
                    )
                    if count > 0:
                        buffer = preserve_xml_declaration(root, buffer)
                        replaced += count

                except ET.ParseError as e:
                    logger.warning(f"XML parse error for {item.filename}: {e}")
                except Exception as e:
                    logger.error(f"Error processing {item.filename}: {e}")

            zout.writestr(item, buffer)

    logger.info(f"PPTX reconstruction: {replaced} replacements → {output_path}")
    return output_path
