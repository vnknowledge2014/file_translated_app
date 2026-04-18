"""XLSX (Excel) deterministic reconstruction.

Handles all Excel-specific concerns:
- Sheet name translation & sanitization (31-char limit, forbidden chars)
- Shared strings (xl/sharedStrings.xml) text replacement
- Worksheet inline strings and formula sheet-ref fixing
- Drawing/chart sheet-ref fixing
- Japanese font → Latin font patching
- Phonetic annotation (rPh/phoneticPr) stripping
- calcChain.xml removal for forced recalculation
- Stale cached <v> value stripping for JP formula cells
"""

import html
import logging
import os
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile

from ._common import build_translation_map, replace_in_text
from ._ooxml import NS, preserve_xml_declaration, register_document_namespaces, replace_paragraph_runs

logger = logging.getLogger(__name__)

# ── Constants ──

_FORBIDDEN_SHEET_CHARS = '\\/?*[]:\n\r\t|'

_JP_FONT_MAP = {
    'ＭＳ Ｐゴシック': 'Arial',
    'ＭＳ ゴシック': 'Arial',
    'ＭＳ 明朝': 'Times New Roman',
    'メイリオ': 'Arial',
    'Meiryo UI': 'Arial',
}

_FONT_PATCH_FILES = {
    'xl/styles.xml', 'xl/theme/theme1.xml', 'xl/sharedStrings.xml',
}

_JP_CHAR_RE = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')


# ── Sheet name helpers ──


def _sanitize_sheet_name(name: str) -> str:
    """Strip forbidden Excel characters and truncate to 31 chars."""
    for c in _FORBIDDEN_SHEET_CHARS:
        name = name.replace(c, '_')
    name = name.strip('_ ')
    return name[:31] if name else ''


def _build_sheet_name_map(
    file_path: str, tmap: dict[str, str]
) -> dict[str, str]:
    """Pre-pass: read workbook.xml and build old→new sheet name map.

    Ensures collision-free, sanitized names within the 31-char Excel limit.
    """
    sheet_name_map: dict[str, str] = {}
    try:
        with zipfile.ZipFile(file_path, 'r') as zp:
            if 'xl/workbook.xml' not in zp.namelist():
                return sheet_name_map
            wb_raw = zp.read('xl/workbook.xml').decode('utf-8')
            all_names = re.findall(r'<sheet\b[^>]+\bname="([^"]*)"', wb_raw)

            seen: set[str] = set()
            for name in all_names:
                if not name:
                    seen.add('')
                    continue
                trans = replace_in_text(name, tmap)
                final = _sanitize_sheet_name(trans if trans else name)
                if not final:
                    final = name[:31]
                base, ctr = final, 1
                while final.lower() in seen:
                    sfx = f"_{ctr}"
                    final = base[:31 - len(sfx)] + sfx
                    ctr += 1
                seen.add(final.lower())
                if final != name:
                    sheet_name_map[name] = final
    except Exception as e:
        logger.warning(f"Pre-pass sheet name map failed: {e}")

    return sheet_name_map


# ── Sheet-ref replacement helpers ──


def _safe_replace(t: str, search: str, replacement: str) -> str:
    """Replace `search` in `t`, but skip occurrences preceded by ] (external refs)."""
    out: list[str] = []
    i = 0
    while i < len(t):
        idx = t.find(search, i)
        if idx == -1:
            out.append(t[i:])
            break
        if idx > 0 and t[idx - 1] == ']':
            out.append(t[i:idx + len(search)])
        else:
            out.append(t[i:idx])
            out.append(replacement)
        i = idx + len(search)
    return ''.join(out)


def _fix_sheet_refs_in_text(text: str, name_map: dict[str, str]) -> str:
    """Replace old sheet names in formula/defined-name text.

    Handles quoted ('Sheet'!) and unquoted (Sheet!) forms.
    Skips external workbook refs ([N]Sheet!).
    """
    for old, new in sorted(name_map.items(), key=lambda x: -len(x[0])):
        new_esc = html.escape(new) if '<' in new or '&' in new else new
        text = _safe_replace(text, f"'{old}'!", f"'{new_esc}'!")
        if ' ' not in old and not any(c in old for c in "![]'"):
            text = _safe_replace(text, f"{old}!", f"{new_esc}!")
    return text


def _fix_formula_sheet_refs(formula_text: str, sheet_name_map: dict[str, str]) -> str:
    """Replace old sheet names in worksheet formulas.

    Handles quoting for new names with spaces/symbols.
    """
    result = formula_text
    for old, new in sorted(sheet_name_map.items(), key=lambda x: -len(x[0])):
        result = _safe_replace(result, f"'{old}'!", f"'{new}'!")
        if ' ' not in old and not any(c in old for c in "![\\'"):
            needs_quotes = ' ' in new or any(c in new for c in r"![]''\"<>*+")
            if needs_quotes:
                result = _safe_replace(result, f"{old}!", f"'{new}'!")
            else:
                result = _safe_replace(result, f"{old}!", f"{new}!")
    return result


# ── Phonetic annotation stripping ──


def _strip_phonetic(si_element: ET.Element) -> None:
    """Remove all <rPh> and <phoneticPr> from an <si> element.

    Japanese XLSX files contain <rPh sb="X" eb="Y"> phonetic (furigana)
    annotations tied to character positions in the original text.
    After translation, these sb/eb indices point to invalid positions,
    causing Excel to flag the file as corrupted.
    """
    rph_tag = f"{{{NS['main']}}}rPh"
    ppr_tag = f"{{{NS['main']}}}phoneticPr"
    for child in list(si_element):
        if child.tag in (rph_tag, ppr_tag):
            si_element.remove(child)


def _strip_all_phonetics(root: ET.Element) -> None:
    """Strip ALL <rPh> and <phoneticPr> from every <si> in the tree.

    _strip_phonetic is called per-paragraph by replace_paragraph_runs,
    but only for entries that matched a translation. Entries that didn't
    match (unchanged JP text) still carry phoneticPr with indices that
    may become invalid after other entries are modified, causing Excel
    to flag the file as corrupted.
    """
    si_tag = f"{{{NS['main']}}}si"
    for si in root.iter(si_tag):
        _strip_phonetic(si)


# ── Font patching ──


def _patch_japanese_fonts(buffer: bytes, filename: str) -> bytes:
    """Replace Japanese fonts with Latin equivalents in XML content."""
    try:
        s = buffer.decode('utf-8')
        for jp_f, lat_f in _JP_FONT_MAP.items():
            s = s.replace(f'val="{jp_f}"', f'val="{lat_f}"')
            s = s.replace(f'typeface="{jp_f}"', f'typeface="{lat_f}"')
        logger.debug(f"Replaced Japanese fonts in {filename}")
        return s.encode('utf-8')
    except Exception as e:
        logger.error(f"Error patching fonts in {filename}: {e}")
        return buffer


# ── Workbook.xml processing ──


def _patch_workbook_xml(
    buffer: bytes,
    tmap: dict[str, str],
    sheet_name_map: dict[str, str],
) -> tuple[bytes, int]:
    """Process xl/workbook.xml: translate sheet names, fix definedNames, inject calcPr.

    Uses regex byte surgery instead of ET to avoid namespace prefix corruption.

    Returns:
        Tuple of (modified buffer, replacement count).
    """
    replaced = 0
    try:
        raw_str = buffer.decode('utf-8')

        # Build collision-free name map
        all_names = re.findall(r'<sheet\b[^>]+\bname="([^"]*)"', raw_str)
        seen_names: set[str] = set()
        name_map: dict[str, str] = {}

        for name in all_names:
            if not name:
                seen_names.add('')
                continue
            trans = replace_in_text(name, tmap)
            final_name = _sanitize_sheet_name(trans if trans else name)
            if not final_name:
                final_name = name[:31]

            original_base = final_name
            counter = 1
            while final_name.lower() in seen_names:
                suffix = f"_{counter}"
                final_name = original_base[:31 - len(suffix)] + suffix
                counter += 1

            seen_names.add(final_name.lower())
            name_map[name] = final_name

        # Replace sheet name attributes
        def _replace_sheet_name(m):
            nonlocal replaced
            old = m.group(1)
            new = name_map.get(old, old)
            if new != old and replace_in_text(old, tmap):
                replaced += 1
            return m.group(0).replace(
                f'name="{old}"', f'name="{html.escape(new)}"', 1
            )

        new_str = re.sub(
            r'<sheet\b[^>]+\bname="([^"]*)"[^>]*/?>',
            _replace_sheet_name, raw_str,
        )

        # Fix <definedName> formula refs
        if name_map:
            new_str = re.sub(
                r'<definedName([^>]*)>([^<]*)</definedName>',
                lambda m: (
                    f"<definedName{m.group(1)}>"
                    f"{_fix_sheet_refs_in_text(m.group(2), name_map)}"
                    f"</definedName>"
                ),
                new_str,
            )

        # Inject fullCalcOnLoad to force Excel recalculation (only if not already present)
        if '<calcPr ' in new_str and 'fullCalcOnLoad' not in new_str:
            new_str = re.sub(r'<calcPr\s', '<calcPr fullCalcOnLoad="1" ', new_str)

        if new_str != raw_str:
            buffer = new_str.encode('utf-8')

    except Exception as e:
        logger.error(f"Error processing workbook.xml: {e}")

    return buffer, replaced


# ── Worksheet processing ──


def _process_worksheet(
    buffer: bytes,
    sheet_name_map: dict[str, str],
) -> bytes:
    """Process a worksheet XML: fix formula sheet refs and strip stale cached values."""
    # Fix formula sheet references
    if sheet_name_map:
        buf_str = buffer.decode('utf-8')
        new_buf = re.sub(
            r'<f([^>]*)>([^<]*)</f>',
            lambda m: (
                f"<f{m.group(1)}>"
                f"{_fix_formula_sheet_refs(m.group(2), sheet_name_map)}"
                f"</f>"
            ),
            buf_str,
        )
        if new_buf != buf_str:
            buffer = new_buf.encode('utf-8')

    # Strip stale cached <v> values from formula cells with Japanese text
    buf_str_v = buffer.decode('utf-8')

    def _strip_jp_cached(m):
        cached_val = m.group(2)
        if _JP_CHAR_RE.search(cached_val):
            return m.group(1)  # drop <v>...</v>
        return m.group(0)

    cleaned = re.sub(r'(</f>)(<v>[^<]*</v>)', _strip_jp_cached, buf_str_v)
    if cleaned != buf_str_v:
        buffer = cleaned.encode('utf-8')

    return buffer


# ── Drawing/chart processing ──


def _process_drawing(buffer: bytes, sheet_name_map: dict[str, str]) -> bytes:
    """Fix sheet name references in drawings and charts."""
    if not sheet_name_map:
        return buffer

    buf_str = buffer.decode('utf-8')
    changed = buf_str
    for old, new in sorted(sheet_name_map.items(), key=lambda x: -len(x[0])):
        changed = _safe_replace(changed, f"'{old}'!", f"'{new}'!")
        if ' ' not in old and not any(c in old for c in "!['"):
            changed = _safe_replace(changed, f"{old}!", f"{new}!")
    if changed != buf_str:
        return changed.encode('utf-8')
    return buffer


def _process_drawing_text(buffer: bytes, tmap: dict[str, str]) -> tuple[bytes, int]:
    """Replace translated text in drawing XML using regex (not ET).

    Drawings use inline xmlns declarations (mc:, a14:, a16:) on child elements
    rather than the root element. ET parse → serialize strips these inline
    declarations, producing invalid XML that causes Excel corruption.

    This function uses regex byte surgery to replace <a:t> text content
    directly, preserving all original XML structure and namespaces.

    Returns:
        Tuple of (modified buffer, replacement count).
    """
    replaced = 0
    try:
        buf_str = buffer.decode('utf-8')
        changed = buf_str

        # Match <a:t ...>text</a:t> or <a:t>text</a:t>
        def _replace_t(m):
            nonlocal replaced
            text = m.group(2)
            if not text or not text.strip():
                return m.group(0)
            trans = replace_in_text(text.strip(), tmap)
            if trans:
                replaced += 1
                return f"{m.group(1)}{trans}</a:t>"
            return m.group(0)

        changed = re.sub(
            r'(<a:t[^>]*>)([^<]+)</a:t>',
            _replace_t,
            changed,
        )

        if changed != buf_str:
            buffer = changed.encode('utf-8')

    except Exception as e:
        logger.error(f"Error processing drawing text: {e}")

    return buffer, replaced


# ── Main entry point ──


def reconstruct_xlsx(
    file_path: str, segments: list[dict], output_path: str
) -> str:
    """Deterministic XLSX reconstruction.

    Strategy: Read original ZIP → process each entry → write new ZIP.
    All formatting, images, charts, and structure are preserved.

    Args:
        file_path: Path to original .xlsx file.
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

    # Pre-pass: build sheet name map for cross-reference fixing
    sheet_name_map = _build_sheet_name_map(file_path, tmap)

    with zipfile.ZipFile(file_path, 'r') as zin, \
         zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED) as zout:

        for item in zin.infolist():
            buffer = zin.read(item.filename)
            fn = item.filename

            # Drop calcChain.xml to force Excel to rebuild formula caches
            if fn == 'xl/calcChain.xml':
                continue

            # ── Clean calcChain references from Content_Types and rels ──
            # When we drop calcChain.xml, references to it in these files
            # cause Excel to report corruption ("file not found").
            if fn == '[Content_Types].xml':
                buf_str = buffer.decode('utf-8')
                buf_str = re.sub(
                    r'<Override[^>]*PartName="/xl/calcChain\.xml"[^>]*/>', '', buf_str
                )
                buffer = buf_str.encode('utf-8')
                zout.writestr(item, buffer)
                continue

            if fn == 'xl/_rels/workbook.xml.rels':
                buf_str = buffer.decode('utf-8')
                buf_str = re.sub(
                    r'<Relationship[^>]*Target="calcChain\.xml"[^>]*/>', '', buf_str
                )
                buffer = buf_str.encode('utf-8')
                zout.writestr(item, buffer)
                continue

            # ── Workbook.xml: sheet name translation ──
            if fn == 'xl/workbook.xml':
                buffer, wb_replaced = _patch_workbook_xml(buffer, tmap, sheet_name_map)
                replaced += wb_replaced
                zout.writestr(item, buffer)
                continue

            # ── Font patching (styles, theme, sharedStrings, drawings) ──
            if fn in _FONT_PATCH_FILES or fn.startswith('xl/drawings/'):
                buffer = _patch_japanese_fonts(buffer, fn)

            # ── Identify text-bearing XML files ──
            is_shared_strings = fn == 'xl/sharedStrings.xml'
            is_worksheet = fn.startswith('xl/worksheets/') and fn.endswith('.xml')
            is_drawing = (
                fn.startswith('xl/drawings/') or fn.startswith('xl/charts/')
            ) and fn.endswith('.xml')

            # ── Worksheet: formula ref fixing + cached value stripping ──
            if is_worksheet:
                buffer = _process_worksheet(buffer, sheet_name_map)
                # Only process via ET if it has inline strings
                if b'inlineStr' not in buffer:
                    zout.writestr(item, buffer)
                    continue

            # ── Drawing/chart: sheet ref fixing + text replacement ──
            # Drawings use ET for paragraph-level text aggregation (needed for
            # multi-run text matching), but serialize via ET.tostring() directly
            # instead of preserve_xml_declaration(). Drawings have inline xmlns
            # (mc:, a14:, a16:) that ET hoists to the root element during
            # serialization — this is valid XML. preserve_xml_declaration()
            # would replace ET's root (with xmlns) with the original root
            # (without xmlns), causing corruption.
            if is_drawing:
                buffer = _process_drawing(buffer, sheet_name_map)
                try:
                    register_document_namespaces(buffer)
                    root = ET.fromstring(buffer)

                    para_tag = f"{{{NS['a']}}}p"
                    r_tag = f"{{{NS['a']}}}r"
                    t_tag = f"{{{NS['a']}}}t"
                    ns_key = 'a'

                    count = replace_paragraph_runs(
                        root, tmap, para_tag, r_tag, t_tag, ns_key,
                    )
                    if count > 0:
                        # Extract original XML declaration
                        raw_str = buffer.decode('utf-8')
                        xml_decl = ''
                        if raw_str.startswith('<?xml'):
                            decl_end = raw_str.find('?>') + 2
                            xml_decl = raw_str[:decl_end]
                        if not xml_decl:
                            xml_decl = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                        # Use ET.tostring directly (xmlns hoisted to root = valid)
                        et_xml = ET.tostring(root, encoding='unicode', xml_declaration=False)
                        et_xml = et_xml.replace(' />', '/>')
                        buffer = (xml_decl + '\r\n' + et_xml).encode('utf-8')
                        replaced += count

                except Exception as e:
                    logger.error(f"Error parsing drawing XML {fn}: {e}")
                zout.writestr(item, buffer)
                continue

            # ── XML text replacement (sharedStrings, inline worksheet strings) ──
            if is_shared_strings or (is_worksheet and b'inlineStr' in buffer):
                try:
                    register_document_namespaces(buffer)
                    root = ET.fromstring(buffer)

                    if is_shared_strings:
                        para_tag = f"{{{NS['main']}}}si"
                    else:
                        para_tag = f"{{{NS['main']}}}is"

                    r_tag = f"{{{NS['main']}}}r"
                    t_tag = f"{{{NS['main']}}}t"
                    ns_key = 'main'

                    count = replace_paragraph_runs(
                        root, tmap, para_tag, r_tag, t_tag, ns_key,
                        strip_phonetic_fn=_strip_phonetic,
                    )

                    # For sharedStrings: also strip orphaned phoneticPr from
                    # entries that weren't translated (replace_paragraph_runs
                    # only strips from entries it actually modified).
                    if is_shared_strings:
                        _strip_all_phonetics(root)

                    if count > 0 or is_shared_strings:
                        buffer = preserve_xml_declaration(root, buffer)
                        replaced += count

                except Exception as e:
                    logger.error(f"Error parsing XML {fn}: {e}")

            zout.writestr(item, buffer)

    logger.info(f"XLSX reconstruction: {replaced} replacements → {output_path}")
    return output_path
