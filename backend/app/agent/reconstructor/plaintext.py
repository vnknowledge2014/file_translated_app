"""Plaintext (txt, md, csv) deterministic reconstruction.

Handles two segment types:
- 'body': Replaces the entire line content (preserving prefixes).
- 'diagram_token': Replaces individual JP tokens within a line,
  preserving ASCII box-drawing structure with visual column expansion.

Completely independent from OOXML processing.
"""

from __future__ import annotations

import logging
import os
import re

import wcwidth

logger = logging.getLogger(__name__)


# ── Visual width helpers for CJK diagram grid expansion ──


def visual_width(text: str) -> int:
    """Calculate the visual width of a string (East Asian Width)."""
    return sum(max(0, wcwidth.wcwidth(c)) for c in text)


def insert_at_visual_col(text: str, insert_vcol: int, diff: int) -> str:
    """Insert diff visual columns at a specific visual column index.

    Used to expand all lines in a code block when a translated token
    is wider than the original.
    """
    current_vw = 0
    new_text = ""
    inserted = False
    prev_c = " "

    for c in text:
        w = max(0, wcwidth.wcwidth(c))
        if current_vw >= insert_vcol and not inserted:
            if prev_c in "─-=":
                dup_char = prev_c
            elif c in "─-=":
                dup_char = c
            else:
                dup_char = " "
            new_text += dup_char * diff
            inserted = True

        new_text += c
        current_vw += w
        prev_c = c

    if not inserted:
        if current_vw < insert_vcol:
            new_text += " " * (insert_vcol - current_vw)
        new_text += " " * diff

    return new_text


def _truncate_to_visual_width(text: str, max_vw: int) -> str:
    """Truncate a string to at most max_vw visual columns.

    Respects wide (CJK, fullwidth) characters that count as 2 columns.
    Used to fit translated diagram tokens within their original box cell.

    Args:
        text: String to truncate.
        max_vw: Maximum visual width allowed.

    Returns:
        Truncated string that fits within max_vw visual columns.
    """
    result = ""
    current_vw = 0
    for c in text:
        w = max(0, wcwidth.wcwidth(c))
        if current_vw + w > max_vw:
            break
        result += c
        current_vw += w
    return result


# ── LLM hallucination prefix stripping ──

_MD_PREFIXES = ["### ", "## ", "# ", "- ", "* ", "> "]


def _strip_hallucinated_prefix(translated: str, original_prefix: str) -> str:
    """Strip markdown prefix that the LLM may have hallucinated into the translation.

    e.g. original "## 見出し" → LLM returns "## Heading"
    Without stripping: "## ## Heading" (doubled prefix).

    Also strips leading/trailing pipe characters occasionally hallucinated by the LLM,
    e.g. "|### 2.3 Heading" on a body line becomes "2.3 Heading".

    Args:
        translated: The translated text from the LLM.
        original_prefix: The detected markdown prefix from the original line.

    Returns:
        Cleaned translation without duplicate prefix.
    """
    # Strip trailing pipe hallucination (e.g. "Danh mục dịch vụ|")
    if translated.endswith("|"):
        translated = translated[:-1].rstrip()

    # Strip leading pipe hallucination (e.g. "|### 2.3 ..." or "| text")
    if translated.startswith("|"):
        translated = translated[1:].lstrip()

    # After stripping pipe, the LLM may have left a heading prefix (e.g. "### text")
    # Strip ALL heading prefixes BEFORE checking original_prefix
    for md_pfx in _MD_PREFIXES:
        if translated.startswith(md_pfx):
            translated = translated[len(md_pfx) :]
            break

    if original_prefix:
        # Strip exact same prefix if still present
        if translated.startswith(original_prefix):
            translated = translated[len(original_prefix) :]
        # Strip any other heading prefix the LLM may have added
        for md_pfx in _MD_PREFIXES:
            if translated.startswith(md_pfx):
                translated = translated[len(md_pfx) :]
                break
    else:
        # No prefix on original — still strip if LLM hallucinated one
        for md_pfx in ["### ", "## ", "# "]:
            if translated.startswith(md_pfx):
                translated = translated[len(md_pfx) :]
                break
    return translated


# ── Main entry point ──


def reconstruct_plaintext(
    file_path: str, segments: list[dict], output_path: str
) -> str:
    """Deterministic reconstruction for plaintext files (txt, md, csv).

    Args:
        file_path: Original file path.
        segments: Translated segments with location like "line[N]".
        output_path: Target output path.

    Returns:
        Path to reconstructed file.
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    # Build lookup for body lines: line_index → translated_text
    body_lookup: dict[int, str] = {}
    # Build lookup for diagram tokens: line_index → [(original, translated)]
    diagram_lookup: dict[int, list[tuple[str, str]]] = {}
    # Build lookup for table cells: line_index → [(original, translated)]
    table_cell_lookup: dict[int, list[tuple[str, str]]] = {}

    for seg in segments:
        translated = seg.get("translated_text", "")
        if not translated:
            continue
        loc = seg.get("location", "")
        match = re.match(r"line\[(\d+)\]", loc)
        if not match:
            continue
        idx = int(match.group(1))
        seg_type = seg.get("type", "body")

        if seg_type == "diagram_token":
            original = seg.get("text", "")
            if original and original != translated:
                diagram_lookup.setdefault(idx, []).append((original, translated))
        elif seg_type == "table_cell":
            original = seg.get("text", "")
            if original and original != translated:
                table_cell_lookup.setdefault(idx, []).append((original, translated))
        else:
            body_lookup[idx] = translated

    # Group lines by code blocks to enable diagram grid expansion
    code_blocks = []
    fence_stack = []
    for i, line in enumerate(lines):
        if line.strip().startswith("```") or line.strip().startswith("~~~"):
            if fence_stack:
                start = fence_stack.pop()
                code_blocks.append((start, i))
            else:
                fence_stack.append(i)

    # Process diagram blocks with simple per-line inline replacement.
    # Strategy: Replace each token IN-PLACE on its own line only.
    # - Consume trailing spaces after the JP token to make room
    # - If translation is shorter: pad with spaces
    # - If translation fits in available space (token_vw + trailing): use it
    # - If translation is still longer: place it and accept minor overflow
    # NEVER modify other lines — grid expansion across lines is unsafe
    # because different lines have different content at the same visual column
    # (e.g., box borders vs. Japanese text), and expanding at a fixed column
    # tears apart text on non-target lines.
    replaced_count = 0

    for start, end in code_blocks:
        block_lines = lines[start : end + 1]

        for i in range(start, end + 1):
            if i not in diagram_lookup:
                continue
            idx_in_block = i - start
            line = block_lines[idx_in_block]

            # Collect ALL occurrences of each JP token on this line.
            # We need this because .find() always returns the FIRST match,
            # which fails when the same token appears multiple times
            # (e.g., "│管理│ │管理│" — two separate boxes with same text).
            token_occurrences: list[tuple[int, str, str]] = []
            for jp_text, vi_text in diagram_lookup[i]:
                # Find ALL positions of this token in the line
                search_start = 0
                while True:
                    pos = line.find(jp_text, search_start)
                    if pos == -1:
                        break
                    token_occurrences.append((pos, jp_text, vi_text))
                    search_start = pos + len(jp_text)

            # Deduplicate: if the same (pos, jp_text) pair appears multiple
            # times (from duplicate segments), keep only one
            seen_positions: set[tuple[int, str]] = set()
            unique_occurrences: list[tuple[int, str, str]] = []
            for pos, jp_text, vi_text in token_occurrences:
                key = (pos, jp_text)
                if key not in seen_positions:
                    seen_positions.add(key)
                    unique_occurrences.append((pos, jp_text, vi_text))

            # Sort by position descending (right-to-left) to prevent
            # index shifting when we modify the line
            unique_occurrences.sort(key=lambda x: -x[0])

            for str_idx, jp_text, vi_text in unique_occurrences:
                vw_orig = visual_width(jp_text)
                vw_new = visual_width(vi_text)

                # Calculate available space: original token width + trailing spaces
                suffix = line[str_idx + len(jp_text):]
                trailing_spaces = len(suffix) - len(suffix.lstrip(' '))
                available = vw_orig + trailing_spaces

                if vw_new <= available:
                    # Fits: replace and pad with spaces to fill remaining width
                    pad = available - vw_new
                    span_end = str_idx + len(jp_text) + trailing_spaces
                    line = (
                        line[:str_idx]
                        + vi_text + " " * pad
                        + line[span_end:]
                    )
                else:
                    # Doesn't fit: place full translation and accept minor overflow.
                    # Readable translation > perfect alignment. Truncation produced
                    # unreadable fragments like 'Thành viên nộ', 'Quản tr'.
                    span_end = str_idx + len(jp_text) + trailing_spaces
                    line = (
                        line[:str_idx]
                        + vi_text
                        + line[span_end:]
                    )

                replaced_count += 1

            block_lines[idx_in_block] = line

        lines[start : end + 1] = block_lines

    # Replace regular body lines and table cells
    output_lines = []
    for i, line in enumerate(lines):
        if i in table_cell_lookup:
            # Replace each cell's content within the original line,
            # preserving all | pipe delimiters intact.
            # Sort by JP text length descending to prevent shorter substrings
            # from corrupting longer matches (e.g., '管理' inside 'イベント管理')
            current_line = line
            sorted_cells = sorted(table_cell_lookup[i], key=lambda x: len(x[0]), reverse=True)
            for jp_cell, vi_cell in sorted_cells:
                current_line = current_line.replace(jp_cell, vi_cell, 1)
            output_lines.append(current_line)
            replaced_count += 1
        elif i in body_lookup:
            stripped = line.rstrip("\n")
            indent = len(stripped) - len(stripped.lstrip())

            lstripped = stripped.lstrip()
            prefix = ""
            for md_prefix in ["### ", "## ", "# ", "- ", "* ", "> ", "  - ", "  * "]:
                if lstripped.startswith(md_prefix):
                    prefix = md_prefix
                    break

            translated = _strip_hallucinated_prefix(body_lookup[i], prefix)
            output_lines.append(
                " " * indent + (prefix + translated if prefix else translated) + "\n"
            )
            replaced_count += 1
        else:
            output_lines.append(line)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    logger.info(
        f"Plaintext reconstruction: {replaced_count} replacements → {output_path}"
    )
    return output_path
