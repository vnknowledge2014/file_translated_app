"""Deterministic text extraction for all supported document formats.

Walks every text-bearing node in the document tree exhaustively.
No LLM involved — pure library traversal + Japanese detection.

Supported: DOCX, XLSX, PPTX, TXT, MD, CSV
"""

import logging
import os
import re

from app.utils.japanese import has_japanese

logger = logging.getLogger(__name__)

# ── Patterns to skip ──

_SKIP_PATTERNS = [
    re.compile(r"^https?://"),           # URLs
    re.compile(r"^[a-zA-Z0-9._%+-]+@"),  # Emails
    re.compile(r"^=\w+\("),              # Excel formulas
    re.compile(r"^[\d\s.,:%/+\-×÷()]+$"),  # Pure numbers/math
]


def _is_translatable(text: str) -> bool:
    """Check if text should be translated.

    A segment is translatable if:
    1. It contains Japanese characters
    2. It's not a URL, email, formula, or pure number

    Args:
        text: Text to check.

    Returns:
        True if the text should be translated.
    """
    if not text or not text.strip():
        return False

    stripped = text.strip()

    # Must contain Japanese
    if not has_japanese(stripped):
        return False

    # Skip known non-translatable patterns
    for pattern in _SKIP_PATTERNS:
        if pattern.match(stripped):
            return False

    return True


def _dedup_segments(segments: list[dict]) -> list[dict]:
    """Remove duplicate segments (same text), keeping first occurrence.

    Args:
        segments: List of segment dicts with 'text' field.

    Returns:
        Deduplicated list preserving order.
    """
    seen: set[str] = set()
    result: list[dict] = []
    for seg in segments:
        key = seg["text"].strip()
        if key not in seen:
            seen.add(key)
            result.append(seg)
    return result


# ── DOCX Extractor ──


import zipfile
import xml.etree.ElementTree as ET

# Namespaces map
NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
}

# Footnote/citation marker pattern: only [N] with brackets required.
# Old pattern ^\[?\d+\]?$ also matched standalone numbers (30, 1975, 177)
# which dropped important numeric runs from paragraph text.
_DOCX_FOOTNOTE_PAT = re.compile(r'^\[\d+\]$')

# Max chars per segment before splitting at sentence boundaries
_MAX_SEG_CHARS = 400
_JP_SENTENCE_END = re.compile(r'(?<=[。！？])\s*')


def _split_long_segment(text: str, location: str, seg_type: str) -> list[dict]:
    """Split a long text segment at Japanese sentence boundaries.

    If text is shorter than _MAX_SEG_CHARS, returns a single-item list.
    Otherwise splits at 。！？ boundaries to keep each chunk under the limit.

    Args:
        text: The segment text to potentially split.
        location: Original location string (will be suffixed with part index).
        seg_type: Segment type (body, heading, etc.).

    Returns:
        List of segment dicts, one per chunk.
    """
    if len(text) <= _MAX_SEG_CHARS:
        return [{"text": text, "location": location, "type": seg_type}]

    # Split at sentence-ending punctuation
    parts = _JP_SENTENCE_END.split(text)
    chunks: list[dict] = []
    current = ""
    for part in parts:
        if not part:
            continue
        if current and len(current) + len(part) > _MAX_SEG_CHARS:
            chunks.append({"text": current.strip(), "location": f"{location}[p{len(chunks)}]", "type": seg_type})
            current = part
        else:
            current += part
    if current.strip():
        chunks.append({"text": current.strip(), "location": f"{location}[p{len(chunks)}]", "type": seg_type})

    return chunks if chunks else [{"text": text, "location": location, "type": seg_type}]


def extract_docx(file_path: str) -> list[dict]:
    """Extract all translatable text from a DOCX file using Native Zip XML parsing."""
    segments = []
    with zipfile.ZipFile(file_path, 'r') as z:
        for filename in [n for n in z.namelist() if n.startswith('word/') and n.endswith('.xml')]:
            try:
                root = ET.fromstring(z.read(filename))

                # Collect runs that live inside hyperlinks — these are citation
                # anchors that produce noise like "26_M9_JM7" and should not
                # be extracted as translatable text.
                hyperlink_run_ids: set[int] = set()
                for hl in root.iter(f"{{{NS['w']}}}hyperlink"):
                    for r in hl.iter(f"{{{NS['w']}}}r"):
                        hyperlink_run_ids.add(id(r))

                for p_idx, p in enumerate(root.iter(f"{{{NS['w']}}}p")):
                    runs = []
                    tag_idx = 1
                    for r in p.findall('w:r', NS):
                        # Skip runs inside hyperlinks (citation anchors)
                        if id(r) in hyperlink_run_ids:
                            continue
                        t = r.find('w:t', NS)
                        if t is not None and t.text:
                            text = t.text
                            # Skip standalone footnote/citation markers: [1], [2]
                            if _DOCX_FOOTNOTE_PAT.match(text.strip()):
                                continue
                            # Rich formatting preservation
                            if r.find('w:rPr', NS) is not None:
                                runs.append(f"<tag{tag_idx}>{text}</tag{tag_idx}>")
                                tag_idx += 1
                            else:
                                runs.append(text)

                    full_text = "".join(runs).strip()
                    if full_text and _is_translatable(full_text):
                        # OOXML segments must NOT be split because splitting
                        # breaks tag pairs across chunks, making reconstruction
                        # impossible.  The translator handles long segments via
                        # tag stripping (>8 tags → translate as plain text).
                        segments.append({
                            "text": full_text,
                            "location": f"{filename}:p[{p_idx}]",
                            "type": "body",
                        })
            except ET.ParseError:
                pass

    result = _dedup_segments(segments)
    logger.info(f"DOCX Native extraction: {len(result)} segments from {file_path}")
    return result


# ── XLSX Extractor ──


def extract_xlsx(file_path: str) -> list[dict]:
    """Extract all translatable text from an XLSX file using Native Zip XML parsing."""
    segments = []
    with zipfile.ZipFile(file_path, 'r') as z:
        # --- 1. Extract sheet names from workbook.xml ---
        if 'xl/workbook.xml' in z.namelist():
            try:
                root = ET.fromstring(z.read('xl/workbook.xml'))
                for idx, sheet in enumerate(root.iter(f"{{{NS['main']}}}sheet")):
                    name = sheet.get('name', '')
                    if name and _is_translatable(name):
                        segments.append({
                            "text": name,
                            "location": f"xl/workbook.xml:sheet[{idx}]",
                            "type": "sheet_name"
                        })
            except ET.ParseError:
                pass

        # --- 2. Extract text from sharedStrings + worksheets + drawings ---
        target_files = [n for n in z.namelist() if n == 'xl/sharedStrings.xml' or n.startswith('xl/drawings/') or (n.startswith('xl/worksheets/') and n.endswith('.xml'))]
        for filename in target_files:
            try:
                root = ET.fromstring(z.read(filename))
                
                if filename == 'xl/sharedStrings.xml':
                    for idx, si in enumerate(root.findall('main:si', NS)):
                        runs = []
                        t = si.find('main:t', NS)
                        if t is not None and t.text:
                            runs.append(t.text)
                        
                        tag_idx = 1
                        for r in si.findall('main:r', NS):
                            rt = r.find('main:t', NS)
                            if rt is not None and rt.text:
                                # In xlsx, rich text wraps <r><t>text</t></r>
                                if r.find('main:rPr', NS) is not None:
                                    runs.append(f"<tag{tag_idx}>{rt.text}</tag{tag_idx}>")
                                    tag_idx += 1
                                else:
                                    runs.append(rt.text)
                                    
                        full_text = "".join(runs).strip()
                        if full_text and _is_translatable(full_text):
                            segments.append({
                                "text": full_text,
                                "location": f"{filename}:si[{idx}]",
                                "type": "body"
                            })
                            
                elif filename.startswith('xl/worksheets/') and filename.endswith('.xml'):
                    for idx, c in enumerate(root.iter(f"{{{NS['main']}}}c")):
                        if c.get('t') == 'inlineStr':
                            is_node = c.find('main:is', NS)
                            if is_node is not None:
                                runs = []
                                t = is_node.find('main:t', NS)
                                if t is not None and t.text:
                                    runs.append(t.text)
                                    
                                tag_idx = 1
                                for r in is_node.findall('main:r', NS):
                                    rt = r.find('main:t', NS)
                                    if rt is not None and rt.text:
                                        if r.find('main:rPr', NS) is not None:
                                            runs.append(f"<tag{tag_idx}>{rt.text}</tag{tag_idx}>")
                                            tag_idx += 1
                                        else:
                                            runs.append(rt.text)
                                            
                                full_text = "".join(runs).strip()
                                if full_text and _is_translatable(full_text):
                                    segments.append({
                                        "text": full_text,
                                        "location": f"{filename}:is[{idx}]",
                                        "type": "body"
                                    })

                            
                elif filename.startswith('xl/drawings/'):
                    for p_idx, p in enumerate(root.iter(f"{{{NS['a']}}}p")):
                        runs = []
                        tag_idx = 1
                        for r in p.findall('a:r', NS):
                            t = r.find('a:t', NS)
                            if t is not None and t.text:
                                if r.find('a:rPr', NS) is not None:
                                    runs.append(f"<tag{tag_idx}>{t.text}</tag{tag_idx}>")
                                    tag_idx += 1
                                else:
                                    runs.append(t.text)
                                    
                        full_text = "".join(runs).strip()
                        if full_text and _is_translatable(full_text):
                            segments.append({
                                "text": full_text,
                                "location": f"{filename}:p[{p_idx}]",
                                "type": "drawing"
                            })
            except ET.ParseError:
                pass

    result = _dedup_segments(segments)
    logger.info(f"XLSX Native extraction: {len(result)} segments from {file_path}")
    return result


# ── PPTX Extractor ──


def extract_pptx(file_path: str) -> list[dict]:
    """Extract all translatable text from a PPTX file using Native Zip XML parsing."""
    segments = []
    with zipfile.ZipFile(file_path, 'r') as z:
        for filename in [n for n in z.namelist() if n.startswith('ppt/') and n.endswith('.xml')]:
            try:
                root = ET.fromstring(z.read(filename))
                for p_idx, p in enumerate(root.iter(f"{{{NS['a']}}}p")):
                    runs = []
                    tag_idx = 1
                    for r in p.findall('a:r', NS):
                        t = r.find('a:t', NS)
                        if t is not None and t.text:
                            if r.find('a:rPr', NS) is not None:
                                runs.append(f"<tag{tag_idx}>{t.text}</tag{tag_idx}>")
                                tag_idx += 1
                            else:
                                runs.append(t.text)
                                
                    full_text = "".join(runs).strip()
                    if full_text and _is_translatable(full_text):
                        segments.append({
                            "text": full_text,
                            "location": f"{filename}:p[{p_idx}]",
                            "type": "body"
                        })
            except ET.ParseError:
                pass

    result = _dedup_segments(segments)
    logger.info(f"PPTX Native extraction: {len(result)} segments from {file_path}")
    return result


# ── ASCII Diagram Support ──

# Box-drawing characters used in ASCII diagrams
_BOX_CHARS = set("┌┐└┘│├┤─┬┴┼╔╗╚╝║╠╣═╦╩╬+|")

# Regex to extract Japanese text tokens from diagram lines
_JP_TOKEN_RE = re.compile(
    r'([\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\uFF10-\uFF19'
    r'\uFF21-\uFF5A\uFF65-\uFF9F]+'
    r'(?:[\s\u3000]*[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF'
    r'\uFF10-\uFF19\uFF21-\uFF5A\uFF65-\uFF9F]+)*)'
)


def _is_diagram_block(lines: list[str], start: int, end: int) -> bool:
    """Check if a code block contains ASCII diagram art.

    Args:
        lines: All file lines (raw, not stripped).
        start: Code fence opening line index.
        end: Code fence closing line index.

    Returns:
        True if the block contains box-drawing characters.
    """
    for j in range(start + 1, end):
        if any(c in lines[j] for c in _BOX_CHARS):
            return True
    return False


def _extract_diagram_tokens(line: str, line_idx: int) -> list[dict]:
    """Extract individual Japanese tokens from a diagram line.

    Given: '│  │サービス   │ │ナレッジ  │'
    Returns: [
        {"text": "サービス", "location": "line[18]", "type": "diagram_token"},
        {"text": "ナレッジ", "location": "line[18]", "type": "diagram_token"},
    ]

    Args:
        line: Raw diagram line text.
        line_idx: Line index in the file.

    Returns:
        List of diagram token segments.
    """
    tokens = _JP_TOKEN_RE.findall(line)
    segments = []
    for token in tokens:
        token = token.strip()
        if token and has_japanese(token):
            segments.append({
                "text": token,
                "location": f"line[{line_idx}]",
                "type": "diagram_token",
            })
    return segments


# ── Plaintext Extractor (TXT, MD, CSV) ──


def extract_plaintext(file_path: str) -> list[dict]:
    """Extract translatable lines from a plaintext file.

    Each line with Japanese text becomes a segment.
    Location is line[N] (0-indexed) for reconstruction.

    For ASCII diagram code blocks (containing box-drawing chars),
    individual JP tokens are extracted instead of whole lines,
    so the box structure is preserved during reconstruction.

    Args:
        file_path: Path to TXT/MD/CSV file.

    Returns:
        List of segment dicts with 'text', 'location', 'type'.
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    # Pre-scan: find all code block ranges and classify them
    code_blocks: list[tuple[int, int, bool]] = []  # (start, end, is_diagram)
    fence_stack: list[int] = []

    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            if fence_stack:
                start = fence_stack.pop()
                is_diag = _is_diagram_block(lines, start, i)
                code_blocks.append((start, i, is_diag))
            else:
                fence_stack.append(i)

    # Build lookup: line_index → (in_code, is_diagram)
    line_state: dict[int, tuple[bool, bool]] = {}
    for start, end, is_diag in code_blocks:
        for j in range(start, end + 1):
            line_state[j] = (True, is_diag)

    segments: list[dict] = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip code fence markers
        if stripped.startswith("```"):
            continue

        state = line_state.get(i)

        if state is not None:
            in_code, is_diagram = state

            if in_code and not is_diagram:
                # Real code block — skip entirely
                continue

            if in_code and is_diagram:
                # ASCII diagram block — extract JP tokens only
                if has_japanese(stripped):
                    tokens = _extract_diagram_tokens(line, i)
                    segments.extend(tokens)
                continue

        # Normal line (outside any code block)
        if not _is_translatable(stripped):
            continue

        # Markdown table row → extract individual cells instead of whole row
        # This prevents the LLM from corrupting | pipe delimiters
        if stripped.startswith("|") and stripped.endswith("|"):
            inner = stripped[1:-1]
            # Skip separator rows like |---|---|
            if re.match(r'^[\s\-:|]+$', inner):
                continue
            cells = inner.split("|")
            for cell_idx, cell in enumerate(cells):
                cell_text = cell.strip()
                if cell_text and _is_translatable(cell_text):
                    segments.append({
                        "text": cell_text,
                        "location": f"line[{i}]",
                        "type": "table_cell",
                        "cell_index": cell_idx,
                    })
            continue

        segments.append({
            "text": stripped,
            "location": f"line[{i}]",
            "type": "body",
        })

    # Note: we do NOT dedup plaintext segments because
    # the reconstructor uses line-index-based replacement
    logger.info(f"Plaintext extraction: {len(segments)} segments from {file_path}")
    return segments


# ── Public dispatcher ──

EXTRACTORS = {
    "docx": extract_docx,
    "xlsx": extract_xlsx,
    "pptx": extract_pptx,
    "txt": extract_plaintext,
    "md": extract_plaintext,
    "csv": extract_plaintext,
}


def extract_document(file_type: str, file_path: str) -> list[dict]:
    """Dispatch to the correct deterministic extractor.

    Args:
        file_type: File type string (docx, xlsx, pptx, txt, md, csv).
        file_path: Path to the input file.

    Returns:
        List of extracted segments.

    Raises:
        ValueError: If file_type has no deterministic extractor.
        FileNotFoundError: If file_path doesn't exist.
    """
    func = EXTRACTORS.get(file_type)
    if func is None:
        raise ValueError(f"No deterministic extractor for: {file_type}")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file not found: {file_path}")

    return func(file_path)
