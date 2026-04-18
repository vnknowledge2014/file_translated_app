"""Shared OOXML (Office Open XML) processing utilities.

XML namespace management, run serialization/deserialization,
and paragraph-level text replacement used by docx, xlsx, and pptx
reconstructors.
"""

import logging
import re
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# ── XML Namespace constants ──

NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'xdr': 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing',
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'a14': 'http://schemas.microsoft.com/office/drawing/2010/main',
    'a16': 'http://schemas.microsoft.com/office/drawing/2014/main',
}


def register_namespaces():
    """Register known OOXML namespaces globally to prevent ns0/ns1 junk."""
    ET.register_namespace('', NS['main'])
    ET.register_namespace('w', NS['w'])
    ET.register_namespace('a', NS['a'])
    ET.register_namespace('r', NS['r'])
    ET.register_namespace('p', NS['p'])
    ET.register_namespace('xdr', NS['xdr'])
    ET.register_namespace('mc', NS['mc'])
    ET.register_namespace('a14', NS['a14'])
    ET.register_namespace('a16', NS['a16'])


def register_document_namespaces(buffer: bytes) -> None:
    """Dynamically register ALL xmlns declarations found in an XML buffer.

    Python's ET generates ns0/ns1/ns2 prefixes for any namespace not
    registered via ET.register_namespace(). OOXML files (especially PPTX)
    often declare many namespaces beyond our known set (p14, dc, cp, vt, etc.).
    If ET mangles these to ns0/ns1, Office apps report the file as corrupted.

    This function scans the raw XML for xmlns declarations and registers
    each one BEFORE parsing, ensuring ET preserves the original prefixes.
    """
    raw = buffer.decode('utf-8', errors='replace') if isinstance(buffer, bytes) else buffer

    # Register prefixed namespaces: xmlns:prefix="uri"
    for prefix, uri in re.findall(r'xmlns:(\w+)="([^"]+)"', raw):
        try:
            ET.register_namespace(prefix, uri)
        except ValueError:
            pass  # Some URIs may be invalid — skip gracefully

    # Register default namespace: xmlns="uri"
    default_ns = re.search(r'\bxmlns="([^"]+)"', raw)
    if default_ns:
        try:
            ET.register_namespace('', default_ns.group(1))
        except ValueError:
            pass


# Register known namespaces on import
register_namespaces()


def deserialize_tags_to_xml(
    translated_text: str,
    original_runs: list[ET.Element],
    namespace_prefix: str,
) -> list[ET.Element]:
    """Convert <tagX> string back to valid OOXML run elements.

    Preserves original rPr formatting from the source runs.

    Args:
        translated_text: Text with <tag1>...<tag1> markers.
        original_runs: Original <r> elements to copy rPr from.
        namespace_prefix: Namespace key ('w', 'a', or 'main').

    Returns:
        List of new <r> elements with translated text and original formatting.
    """
    rpr_map = {}
    default_r = (
        original_runs[0]
        if original_runs
        else ET.Element(f'{{{NS[namespace_prefix]}}}r')
    )

    for idx, r in enumerate(original_runs):
        tag_id = idx + 1
        rpr = r.find(f'{namespace_prefix}:rPr', NS)
        rpr_map[str(tag_id)] = rpr

    new_runs = []
    parts = re.split(r'(</?tag\d+>)', translated_text)

    current_tag = None
    buffer = ""

    for part in parts:
        if part.startswith('<tag'):
            current_tag = part[4:-1]
        elif part.startswith('</tag'):
            if buffer:
                nr = ET.Element(f'{{{NS[namespace_prefix]}}}r')
                rpr = rpr_map.get(current_tag)
                if rpr is not None:
                    nr.append(ET.fromstring(ET.tostring(rpr)))
                nt = ET.SubElement(nr, f'{{{NS[namespace_prefix]}}}t')
                # Only add xml:space="preserve" when text has leading/trailing
                # whitespace.  Original PPTX never uses it on <a:t>; original
                # DOCX only uses it on whitespace-only runs like " ".
                if buffer != buffer.strip() or '  ' in buffer:
                    nt.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                nt.text = buffer
                new_runs.append(nr)
                buffer = ""
            current_tag = None
        else:
            if current_tag:
                buffer += part
            elif part:  # Preserve whitespace-only parts too — dropping them merges words
                nr = ET.Element(f'{{{NS[namespace_prefix]}}}r')
                rpr = default_r.find(f'{namespace_prefix}:rPr', NS)
                if rpr is not None:
                    nr.append(ET.fromstring(ET.tostring(rpr)))
                nt = ET.SubElement(nr, f'{{{NS[namespace_prefix]}}}t')
                if part != part.strip() or '  ' in part:
                    nt.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                nt.text = part
                new_runs.append(nr)

    return new_runs


def replace_paragraph_runs(
    root: ET.Element,
    tmap: dict[str, str],
    para_tag: str,
    r_tag: str,
    t_tag: str,
    ns_key: str,
    strip_phonetic_fn=None,
) -> int:
    """Replace translated text in OOXML paragraph runs.

    Generic logic shared by docx, pptx, and xlsx reconstructors.

    Args:
        root: Parsed XML root element.
        tmap: Translation map {original: translated}.
        para_tag: Full tag name for paragraph elements.
        r_tag: Full tag name for run elements.
        t_tag: Full tag name for text elements.
        ns_key: Namespace key for run property lookups.
        strip_phonetic_fn: Optional function to strip phonetic annotations.

    Returns:
        Number of replacements made.
    """
    from ._common import replace_in_text

    # Same pattern used by extractor to skip footnote/citation markers
    footnote_pat = re.compile(r'^\[\d+\]$')

    replaced = 0

    for p in root.iter(para_tag):
        runs = p.findall(r_tag)
        if not runs:
            t_node = p.find(t_tag)
            if t_node is not None and t_node.text:
                text = t_node.text.strip()
                trans = replace_in_text(text, tmap)
                if trans:
                    t_node.text = trans
                    if strip_phonetic_fn:
                        strip_phonetic_fn(p)
                    replaced += 1
            continue

        # Aggregate runs with <tagX> markers, skipping footnote runs
        # to match extractor behavior (consistent tag numbering).
        agg_runs = []
        agg_run_elements = []     # runs contributing to tagged text
        footnote_runs = []        # footnote runs to preserve as-is
        tag_idx = 1
        for r in runs:
            t_node = r.find(t_tag)
            if t_node is not None and t_node.text:
                # Skip footnote markers [1], [2] etc.
                if footnote_pat.match(t_node.text.strip()):
                    footnote_runs.append(r)
                    continue
                rpr = r.find(f'{ns_key}:rPr', NS)
                if rpr is not None:
                    agg_runs.append(f"<tag{tag_idx}>{t_node.text}</tag{tag_idx}>")
                    tag_idx += 1
                else:
                    agg_runs.append(t_node.text)
                agg_run_elements.append(r)

        full_text = "".join(agg_runs).strip()
        if not full_text:
            continue

        trans = replace_in_text(full_text, tmap)
        if not trans:
            # Fallback: try plain text match (tags stripped).
            # This handles paragraphs where extractor stripped tags due to
            # too many inline tags — tmap keys are plain text.
            plain = re.sub(r'</?tag\d+>', '', full_text)
            trans = replace_in_text(plain, tmap)
            if trans:
                # Plain text match: create a single run with merged text
                # (no tag structure to preserve)
                nr = ET.Element(f'{{{NS[ns_key]}}}r')
                # Use formatting from first run
                if agg_run_elements:
                    rpr = agg_run_elements[0].find(f'{ns_key}:rPr', NS)
                    if rpr is not None:
                        nr.append(ET.fromstring(ET.tostring(rpr)))
                nt = ET.SubElement(nr, f'{{{NS[ns_key]}}}t')
                nt.set(
                    '{http://www.w3.org/XML/1998/namespace}space', 'preserve'
                )
                nt.text = trans
                # Find insertion point and do replacement
                p_children = list(p)
                insert_idx = len(p_children)
                for r in agg_run_elements:
                    try:
                        insert_idx = min(insert_idx, p_children.index(r))
                    except ValueError:
                        pass
                for r in agg_run_elements:
                    p.remove(r)
                p.insert(insert_idx, nr)
                if strip_phonetic_fn:
                    strip_phonetic_fn(p)
                replaced += 1
                continue

        if trans:
            new_runs = deserialize_tags_to_xml(trans, agg_run_elements, ns_key)
            # Fix missing spaces at Vietnamese word boundaries between runs
            _fix_run_boundaries(new_runs, t_tag)
            # Find insertion index (before endParaRPr)
            p_children = list(p)
            insert_idx = len(p_children)
            for r in agg_run_elements:
                try:
                    insert_idx = min(insert_idx, p_children.index(r))
                except ValueError:
                    pass
            # Remove only the aggregated runs (not footnote runs)
            for r in agg_run_elements:
                p.remove(r)
            # Insert new runs at original position
            for i, nr in enumerate(new_runs):
                p.insert(insert_idx + i, nr)
            if strip_phonetic_fn:
                strip_phonetic_fn(p)
            replaced += 1

    return replaced


def _is_viet_char(ch: str) -> bool:
    """Check if a character is a Vietnamese alphabetic character (including diacritics)."""
    if not ch or not ch.isalpha():
        return False
    # Vietnamese uses Latin + diacritics; check for non-ASCII letters
    # or common Vietnamese tonal letters
    return True  # All alpha chars can be Vietnamese word chars


def _needs_space_between(left: str, right: str) -> bool:
    """Check if a space is needed between two adjacent run texts.

    Returns True if left ends with a letter and right starts with a letter,
    indicating a missing word boundary. Does NOT insert spaces next to
    punctuation, digits, or whitespace.
    """
    if not left or not right:
        return False
    last = left.rstrip()
    first = right.lstrip()
    if not last or not first:
        return False
    # Only inject if both sides are letters (word chars)
    return last[-1].isalpha() and first[0].isalpha()


def _fix_run_boundaries(runs: list[ET.Element], t_tag: str) -> None:
    """Fix missing spaces at word boundaries between adjacent OOXML runs.

    When the LLM translates tagged text like '<tag1>栽培法</tag1>と<tag2>品種</tag2>'
    into '<tag1>trồng trọt</tag1>và<tag2>giống</tag2>', the runs get joined
    as 'trồng trọtvàgiống' without spaces.

    This function checks each pair of adjacent runs and injects a leading
    space on the right run when a word boundary is missing.
    """
    for i in range(len(runs) - 1):
        t_left = runs[i].find(t_tag)
        t_right = runs[i + 1].find(t_tag)
        if t_left is None or t_right is None:
            continue
        left_text = t_left.text or ""
        right_text = t_right.text or ""

        if _needs_space_between(left_text, right_text):
            # Append trailing space to left run (more robust for Word rendering).
            # Word sometimes trims leading spaces on the next run even with
            # xml:space="preserve" when run styles differ.
            t_left.text = left_text + " "
            t_left.set(
                '{http://www.w3.org/XML/1998/namespace}space', 'preserve'
            )


def preserve_xml_declaration(modified_root: ET.Element, original_buffer: bytes) -> bytes:
    """Serialize modified XML preserving original declaration AND root element tag.

    ET.tostring() strips xmlns declarations not used by child element tags.
    Office apps (Word, PowerPoint, Excel) require ALL original namespace
    declarations to be present for validation.

    Strategy:
    1. Serialize the entire modified tree with ET (valid XML with all namespaces).
    2. Extract the original root opening tag from the raw buffer.
    3. Replace ET's generated root opening tag with the original one.
    This avoids dangerous regex-based namespace stripping that could corrupt XML.

    Args:
        modified_root: The modified XML root element.
        original_buffer: The raw bytes of the original XML file.

    Returns:
        Complete XML bytes with preserved declaration and namespaces.
    """
    raw = original_buffer if isinstance(original_buffer, bytes) else original_buffer.encode('utf-8')
    raw_str = raw.decode('utf-8')

    # 1. Extract original XML declaration + whitespace
    orig_decl = ''
    body = raw_str
    if raw_str.startswith('<?xml'):
        decl_end = raw_str.find('?>') + 2
        orig_decl = raw_str[:decl_end]
        body = raw_str[decl_end:]
        # Preserve whitespace between declaration and root element
        ws = ''
        for c in body:
            if c in '\r\n \t':
                ws += c
            else:
                break
        orig_decl += ws
        body = body[len(ws):]

    # 2. Extract original root opening tag (preserves ALL xmlns:* declarations)
    root_end = 0
    for idx, c in enumerate(body):
        if c == '>':
            root_end = idx + 1
            break
    orig_root_open = body[:root_end]

    # 3. Serialize entire modified tree via ET (valid, self-contained XML)
    et_xml = ET.tostring(modified_root, encoding='unicode', xml_declaration=False)

    # 4. Find end of ET's generated root opening tag
    et_root_end = 0
    for idx, c in enumerate(et_xml):
        if c == '>':
            et_root_end = idx + 1
            break
    et_inner = et_xml[et_root_end:]

    # 5. Reassemble: declaration + original root tag + ET's inner content
    # ET's inner content already has proper closing tag, so we just substitute
    # the root opening tag to preserve all original xmlns declarations.
    result = orig_decl + orig_root_open + et_inner

    # 6. Normalize self-closing tags: Python ET always serializes as " />"
    #    but Office XML uses "/>" (no space).
    result = result.replace(' />', '/>')

    return result.encode('utf-8')
