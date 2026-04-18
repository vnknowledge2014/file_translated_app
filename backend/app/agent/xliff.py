"""XLIFF bilingual translation exchange — dual-version (1.2 + 2.1).

Export translated segments to XLIFF for human review in CAT tools
(Trados, memoQ, OmegaT, etc.) and import reviewed XLIFF back into
the reconstruction pipeline.

Supported:
  - XLIFF 1.2 (urn:oasis:names:tc:xliff:document:1.2) — default, max compatibility
  - XLIFF 2.1 (urn:oasis:names:tc:xliff:document:2.1) — modern, cleaner

Inline tag mapping:
  - <tag1>text</tag1> ↔ <bpt>/<ept> (1.2) or <pc> (2.1)
  - <tag2/> ↔ <x/> (1.2) or <ph/> (2.1)
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

_NS_V12 = "urn:oasis:names:tc:xliff:document:1.2"
_NS_V21 = "urn:oasis:names:tc:xliff:document:2.1"
_NS_XML = "http://www.w3.org/XML/1998/namespace"

_PAIRED_TAG_RE = re.compile(r"<(tag\d+)>(.*?)</\1>", re.DOTALL)
_SELF_CLOSING_TAG_RE = re.compile(r"<(tag\d+)/>")
_TAG_ANY_RE = re.compile(r"</?tag\d+/?>")


# ── Inline Tag Conversion ──

def _tags_to_xliff_v12(text: str) -> str:
    """Convert <tagN>text</tagN> to XLIFF 1.2 inline elements."""
    if not _TAG_ANY_RE.search(text):
        return text
    result = text
    for m in _SELF_CLOSING_TAG_RE.finditer(text):
        tag_name = m.group(1)
        tag_id = tag_name.replace("tag", "")
        result = result.replace(m.group(0), f'<x id="{tag_id}" ctype="x-{tag_name}"/>', 1)
    def _replace_paired(m):
        tag_name = m.group(1)
        inner = m.group(2)
        tag_id = tag_name.replace("tag", "")
        bpt = f'<bpt id="{tag_id}" ctype="x-{tag_name}">&lt;{tag_name}&gt;</bpt>'
        ept = f'<ept id="{tag_id}">&lt;/{tag_name}&gt;</ept>'
        return f"{bpt}{inner}{ept}"
    result = _PAIRED_TAG_RE.sub(_replace_paired, result)
    return result


def _xliff_v12_to_tags(text: str) -> str:
    """Convert XLIFF 1.2 inline elements back to <tagN> format."""
    if not text:
        return text
    result = text
    result = re.sub(r'<x\s+id="(\d+)"[^/]*/>', lambda m: f'<tag{m.group(1)}/>', result)
    result = re.sub(
        r'<bpt\s+id="(\d+)"[^>]*>[^<]*</bpt>(.*?)<ept\s+id="\1">[^<]*</ept>',
        lambda m: f'<tag{m.group(1)}>{m.group(2)}</tag{m.group(1)}>',
        result, flags=re.DOTALL,
    )
    return result


def _tags_to_xliff_v21(text: str) -> str:
    """Convert <tagN>text</tagN> to XLIFF 2.1 inline elements."""
    if not _TAG_ANY_RE.search(text):
        return text
    result = text
    for m in _SELF_CLOSING_TAG_RE.finditer(text):
        tag_name = m.group(1)
        tag_id = tag_name.replace("tag", "")
        result = result.replace(m.group(0), f'<ph id="{tag_id}" type="other"/>', 1)
    def _replace_paired(m):
        tag_name = m.group(1)
        inner = m.group(2)
        tag_id = tag_name.replace("tag", "")
        return f'<pc id="{tag_id}" type="fmt">{inner}</pc>'
    result = _PAIRED_TAG_RE.sub(_replace_paired, result)
    return result


def _xliff_v21_to_tags(text: str) -> str:
    """Convert XLIFF 2.1 inline elements back to <tagN> format."""
    if not text:
        return text
    result = text
    result = re.sub(r'<ph\s+id="(\d+)"[^/]*/>', lambda m: f'<tag{m.group(1)}/>', result)
    result = re.sub(
        r'<pc\s+id="(\d+)"[^>]*>(.*?)</pc>',
        lambda m: f'<tag{m.group(1)}>{m.group(2)}</tag{m.group(1)}>',
        result, flags=re.DOTALL,
    )
    return result


# ── Version Detection ──

def detect_xliff_version(path: str) -> str:
    """Detect XLIFF version from file. Returns '1.2' or '2.1'."""
    for event, elem in ET.iterparse(path, events=("start",)):
        version = elem.get("version", "")
        if version:
            return version
        if _NS_V21 in elem.tag:
            return "2.1"
        if _NS_V12 in elem.tag:
            return "1.2"
        break
    return "1.2"


# ── Helpers ──

def _state_for_segment(seg: dict) -> str:
    """Determine XLIFF state from segment data."""
    if "xliff_state" in seg:
        return seg["xliff_state"]
    target = seg.get("translated_text", "")
    if not target or not target.strip():
        return "new"
    confidence = seg.get("confidence", None)
    if confidence is not None and confidence < 0.6:
        return "needs-review-translation"
    return "translated"


def _set_mixed_content(element: ET.Element, text_with_inline: str):
    """Set element content that may contain inline XML elements."""
    if not re.search(r"<(?:bpt|ept|x |pc |ph )", text_with_inline):
        element.text = text_with_inline
        return
    try:
        wrapper = ET.fromstring(f"<tmp>{text_with_inline}</tmp>")
        element.text = wrapper.text
        for child in wrapper:
            element.append(child)
    except ET.ParseError:
        element.text = text_with_inline


def _get_mixed_content(element: ET.Element) -> str:
    """Extract text + inline elements as a string."""
    if element is None:
        return ""
    parts: list[str] = []
    if element.text:
        parts.append(element.text)
    for child in element:
        parts.append(ET.tostring(child, encoding="unicode", short_empty_elements=True))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _add_notes(parent: ET.Element, seg: dict):
    """Add metadata notes to a trans-unit or unit."""
    for key, prefix in [("location", "location"), ("type", "type")]:
        val = seg.get(key, "")
        if val:
            note = ET.SubElement(parent, "note", {"from": "system"})
            note.text = f"{prefix}: {val}"
    confidence = seg.get("confidence")
    if confidence is not None:
        note = ET.SubElement(parent, "note", {"from": "system"})
        note.text = f"confidence: {confidence:.2f}"


def _read_notes(parent: ET.Element, seg: dict, ns: str):
    """Read metadata notes back into segment dict."""
    for note in parent.findall(f"{{{ns}}}note"):
        t = note.text or ""
        if t.startswith("location: "):
            seg["location"] = t[10:]
        elif t.startswith("type: "):
            seg["type"] = t[6:]
        elif t.startswith("confidence: "):
            try:
                seg["confidence"] = float(t[12:])
            except ValueError:
                pass


def _map_state_to_v21(state_v12: str) -> str:
    return {"new": "initial", "needs-translation": "initial",
            "translated": "translated", "needs-review-translation": "reviewed",
            "final": "final", "signed-off": "final"}.get(state_v12, "initial")


def _map_state_from_v21(state_v21: str) -> str:
    return {"initial": "new", "translated": "translated",
            "reviewed": "needs-review-translation", "final": "final"}.get(state_v21, "new")


# ── XLIFF 1.2 ──

def _export_v12(segments, original_filename, file_type, output_path, source_lang, target_lang):
    ET.register_namespace("", _NS_V12)
    xliff = ET.Element("xliff", {"version": "1.2", "xmlns": _NS_V12})
    file_el = ET.SubElement(xliff, "file", {
        "original": original_filename, "source-language": source_lang,
        "target-language": target_lang, "datatype": f"x-{file_type}",
        "tool-id": "jp-vi-translator",
    })
    header = ET.SubElement(file_el, "header")
    ET.SubElement(header, "tool", {"tool-id": "jp-vi-translator", "tool-name": "JP-VI Translation System"})
    body = ET.SubElement(file_el, "body")
    for idx, seg in enumerate(segments):
        source_text = seg.get("text", "")
        if not source_text or not source_text.strip():
            continue
        tu = ET.SubElement(body, "trans-unit", {"id": str(idx + 1), "translate": "yes"})
        source_el = ET.SubElement(tu, "source")
        source_el.set(f"{{{_NS_XML}}}lang", source_lang)
        _set_mixed_content(source_el, _tags_to_xliff_v12(source_text))
        target_text = seg.get("translated_text", "")
        state = _state_for_segment(seg)
        target_el = ET.SubElement(tu, "target")
        target_el.set(f"{{{_NS_XML}}}lang", target_lang)
        target_el.set("state", state)
        if target_text and target_text.strip():
            _set_mixed_content(target_el, _tags_to_xliff_v12(target_text))
        _add_notes(tu, seg)
    tree = ET.ElementTree(xliff)
    ET.indent(tree, space="  ", level=0)
    tree.write(output_path, encoding="UTF-8", xml_declaration=True)
    logger.info(f"XLIFF 1.2 export: {len([s for s in segments if s.get('text','').strip()])} trans-units → {output_path}")
    return output_path


def _import_v12(xliff_path):
    tree = ET.parse(xliff_path)
    root = tree.getroot()
    segments = []
    for tu in root.iter(f"{{{_NS_V12}}}trans-unit"):
        source_el = tu.find(f"{{{_NS_V12}}}source")
        target_el = tu.find(f"{{{_NS_V12}}}target")
        source_text = _xliff_v12_to_tags(_get_mixed_content(source_el)) if source_el is not None else ""
        target_text = _xliff_v12_to_tags(_get_mixed_content(target_el)) if target_el is not None else ""
        seg = {"text": source_text, "translated_text": target_text if target_text.strip() else ""}
        if target_el is not None:
            state = target_el.get("state", "")
            if state:
                seg["xliff_state"] = state
        _read_notes(tu, seg, _NS_V12)
        segments.append(seg)
    logger.info(f"XLIFF 1.2 import: {len(segments)} trans-units ← {xliff_path}")
    return segments


# ── XLIFF 2.1 ──

def _export_v21(segments, original_filename, file_type, output_path, source_lang, target_lang):
    ET.register_namespace("", _NS_V21)
    xliff = ET.Element("xliff", {"version": "2.1", "xmlns": _NS_V21, "srcLang": source_lang, "trgLang": target_lang})
    file_el = ET.SubElement(xliff, "file", {"id": "f1", "original": original_filename})
    for idx, seg in enumerate(segments):
        source_text = seg.get("text", "")
        if not source_text or not source_text.strip():
            continue
        unit = ET.SubElement(file_el, "unit", {"id": f"u{idx + 1}"})
        segment_el = ET.SubElement(unit, "segment")
        state = _state_for_segment(seg)
        segment_el.set("state", _map_state_to_v21(state))
        source_el = ET.SubElement(segment_el, "source")
        _set_mixed_content(source_el, _tags_to_xliff_v21(source_text))
        target_el = ET.SubElement(segment_el, "target")
        target_text = seg.get("translated_text", "")
        if target_text and target_text.strip():
            _set_mixed_content(target_el, _tags_to_xliff_v21(target_text))
        _add_notes(unit, seg)
    tree = ET.ElementTree(xliff)
    ET.indent(tree, space="  ", level=0)
    tree.write(output_path, encoding="UTF-8", xml_declaration=True)
    logger.info(f"XLIFF 2.1 export: {len([s for s in segments if s.get('text','').strip()])} units → {output_path}")
    return output_path


def _import_v21(xliff_path):
    tree = ET.parse(xliff_path)
    root = tree.getroot()
    segments = []
    for unit in root.iter(f"{{{_NS_V21}}}unit"):
        for seg_el in unit.findall(f"{{{_NS_V21}}}segment"):
            source_el = seg_el.find(f"{{{_NS_V21}}}source")
            target_el = seg_el.find(f"{{{_NS_V21}}}target")
            source_text = _xliff_v21_to_tags(_get_mixed_content(source_el)) if source_el is not None else ""
            target_text = _xliff_v21_to_tags(_get_mixed_content(target_el)) if target_el is not None else ""
            seg = {"text": source_text, "translated_text": target_text if target_text.strip() else ""}
            state = seg_el.get("state", "")
            if state:
                seg["xliff_state"] = _map_state_from_v21(state)
            _read_notes(unit, seg, _NS_V21)
            segments.append(seg)
    logger.info(f"XLIFF 2.1 import: {len(segments)} segments ← {xliff_path}")
    return segments


# ── Public API ──

def export_xliff(segments, original_filename, file_type, output_path,
                 source_lang="ja", target_lang="vi", version="1.2"):
    """Export translated segments to XLIFF bilingual file.

    Args:
        segments: List of segment dicts with 'text' and optional 'translated_text'.
        original_filename: Original document filename.
        file_type: Document type (docx, xlsx, pptx, txt, md, csv).
        output_path: Where to write the .xlf file.
        source_lang: BCP-47 source language tag.
        target_lang: BCP-47 target language tag.
        version: XLIFF version — '1.2' (default) or '2.1'.

    Returns:
        Path to the written .xlf file.
    """
    if version.startswith("2"):
        return _export_v21(segments, original_filename, file_type, output_path, source_lang, target_lang)
    return _export_v12(segments, original_filename, file_type, output_path, source_lang, target_lang)


def import_xliff(xliff_path):
    """Import segments from XLIFF file (auto-detect version)."""
    version = detect_xliff_version(xliff_path)
    if version.startswith("2"):
        return _import_v21(xliff_path)
    return _import_v12(xliff_path)


def merge_xliff_into_segments(original_segments, xliff_segments):
    """Merge XLIFF imports back into original segment list.

    Matches by source text. Updates translated_text from XLIFF target.
    Preserves original metadata (location, type).
    """
    xliff_map = {}
    for seg in xliff_segments:
        source = seg.get("text", "").strip()
        target = seg.get("translated_text", "").strip()
        if source and target:
            xliff_map[source] = target
    merged_count = 0
    for seg in original_segments:
        source = seg.get("text", "").strip()
        if source in xliff_map:
            seg["translated_text"] = xliff_map[source]
            merged_count += 1
    logger.info(f"XLIFF merge: {merged_count}/{len(original_segments)} segments matched")
    return original_segments
