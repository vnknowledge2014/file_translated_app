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


# ---------------------------------------------------------------------------
#  Algorithmic ASCII-box reshape (pure Python, no LLM)
# ---------------------------------------------------------------------------

def _box_top_re():
    """Regex matching a box top border like ┌───────┐."""
    return re.compile(r'┌─+┐')


def _box_bottom_re():
    """Regex matching a box bottom border like └───────┘ or └───┬───┘."""
    return re.compile(r'└[─┬┴┼]+┘')


def _split_cells(line: str, num_boxes: int) -> list[str]:
    """Extract cell texts from a content line by splitting on │.

    Handles both nested (inside outer container) and non-nested layouts.
    Cells are matched by ORDER, not by column position, so this works
    even after inline replacement shifted │ positions.
    """
    parts = line.split('│')
    n = len(parts) - 1  # number of │ characters

    if n >= 2 * num_boxes + 2:
        # Nested inside outer container — cells at indices 2, 4, …
        return [
            parts[2 + 2 * i] if 2 + 2 * i < len(parts) else ''
            for i in range(num_boxes)
        ]
    if n >= 2 * num_boxes:
        # Not nested — cells at indices 1, 3, …
        return [
            parts[1 + 2 * i] if 1 + 2 * i < len(parts) else ''
            for i in range(num_boxes)
        ]
    return [''] * num_boxes


def _rebuild_border(line: str, matches, new_widths: list[int],
                    left_ch: str, right_ch: str) -> str:
    """Rebuild a border line with new box widths.

    Preserves special characters (┬ ┴ ┼) inside bottom borders by
    re-centering them in the new width.
    """
    parts: list[str] = []
    prev_end = 0

    for i, m in enumerate(matches):
        parts.append(line[prev_end:m.start()])
        inner = line[m.start() + 1 : m.end() - 1]
        new_w = new_widths[i]

        # Find special char (┬ ┴ ┼) in original inner border
        special = next((ch for ch in inner if ch != '─'), None)
        if special:
            center = new_w // 2
            new_inner = '─' * center + special + '─' * (new_w - center - 1)
        else:
            new_inner = '─' * new_w

        parts.append(left_ch + new_inner + right_ch)
        prev_end = m.end()

    parts.append(line[prev_end:])
    return ''.join(parts)


def _rebuild_cell_line(line: str, num_boxes: int,
                       new_widths: list[int]) -> str:
    """Rebuild a content line with cells padded to new box widths."""
    parts = line.split('│')
    n = len(parts) - 1

    if n >= 2 * num_boxes + 2:
        cell_start = 2
    elif n >= 2 * num_boxes:
        cell_start = 1
    else:
        return line  # can't parse

    for bi in range(num_boxes):
        idx = cell_start + bi * 2
        if idx >= len(parts):
            break
        # Collapse multi-space runs left by per-token padding
        content = re.sub(r'  +', ' ', parts[idx].strip())
        vw = visual_width(content)
        pad = new_widths[bi] - vw
        parts[idx] = ' ' + content + ' ' * max(0, pad - 1)

    return '│'.join(parts)


def _expand_containers(lines: list[str]) -> None:
    """Expand outer container boxes to fit their (possibly wider) content.

    After inner box rows are resized, outer containers may be too narrow.
    This finds each outer ┌─┐ … └─┘ pair and adjusts its width to the
    widest inner line, then pads all inner lines to match.
    """
    idx = 0
    while idx < len(lines):
        stripped = lines[idx].rstrip('\n').strip()
        # Outer top border: starts with ┌, ends with ┐, no │ on same line
        if (stripped.startswith('┌') and stripped.endswith('┐')
                and '│' not in stripped):
            for j in range(idx + 1, min(idx + 60, len(lines))):
                s = lines[j].rstrip('\n').strip()
                if s.startswith('└') and '┘' in s and '│' not in s:
                    _expand_one_container(lines, idx, j)
                    idx = j + 1
                    break
            else:
                idx += 1
        else:
            idx += 1


def _expand_one_container(lines: list[str], top: int, bottom: int) -> None:
    """Expand a single outer container to fit its widest inner line."""
    max_inner_vw = 0
    for k in range(top + 1, bottom):
        raw = lines[k].rstrip('\n')
        if raw.startswith('│') and '│' in raw[1:]:
            inner = raw[1 : raw.rindex('│')]
            max_inner_vw = max(max_inner_vw, visual_width(inner))
    if max_inner_vw == 0:
        return

    new_iw = max_inner_vw  # new inner width of outer container

    # --- Rebuild top border ┌─…─┐ ---
    nl_top = '\n' if lines[top].endswith('\n') else ''
    lines[top] = '┌' + '─' * new_iw + '┐' + nl_top

    # --- Rebuild bottom border └─…─┘ (preserve ┼/┬) ---
    orig_bot = lines[bottom].rstrip('\n').strip()
    inner_orig = orig_bot[1:-1]
    specials: dict[float, str] = {}
    for ci, ch in enumerate(inner_orig):
        if ch != '─':
            specials[ci / max(len(inner_orig), 1)] = ch

    if specials:
        inner_new = list('─' * new_iw)
        for rel, ch in specials.items():
            pos = min(int(rel * new_iw), new_iw - 1)
            inner_new[pos] = ch
        nl_bot = '\n' if lines[bottom].endswith('\n') else ''
        lines[bottom] = '└' + ''.join(inner_new) + '┘' + nl_bot
    else:
        nl_bot = '\n' if lines[bottom].endswith('\n') else ''
        lines[bottom] = '└' + '─' * new_iw + '┘' + nl_bot

    # --- Expand wide inner boxes BEFORE padding ---
    # Must run before pad/trim so inner box content has correct pipe positions
    _expand_wide_inner_boxes(lines, top, bottom, new_iw)

    # --- Pad/trim inner lines ---
    for k in range(top + 1, bottom):
        raw = lines[k].rstrip('\n')
        nl_k = '\n' if lines[k].endswith('\n') else ''
        if raw.startswith('│') and '│' in raw[1:]:
            last_pipe = raw.rindex('│')
            inner = raw[1:last_pipe]
            vw = visual_width(inner)
            pad = new_iw - vw
            if pad > 0:
                lines[k] = '│' + inner + ' ' * pad + '│' + nl_k
            else:
                lines[k] = '│' + inner + '│' + nl_k


def _expand_wide_inner_boxes(
    lines: list[str], top: int, bottom: int, container_iw: int
) -> None:
    """Expand wide single-span inner boxes to fill the outer container width.

    After the outer container is expanded, wide inner boxes (e.g. REST API
    Layer, PostgreSQL) stay at their original width creating large gaps.
    This finds such boxes and stretches them to fill the container.

    A "wide inner box" is detected as a single ┌─┐ on a │-prefixed line
    occupying >50% of the container inner width.
    """
    top_re = _box_top_re()
    bot_re = _box_bottom_re()

    k = top + 1
    while k < bottom:
        raw = lines[k].rstrip('\n')
        nl_k = '\n' if lines[k].endswith('\n') else ''

        # Only process │-prefixed lines (inside container)
        if not raw.startswith('│'):
            k += 1
            continue

        # Find single ┌─┐ on this line
        tops = list(top_re.finditer(raw))
        if len(tops) != 1:
            k += 1
            continue

        m = tops[0]
        inner_box_w = m.end() - m.start() - 2  # width between ┌ and ┐

        # Only wide boxes (>50% of container width)
        if inner_box_w < container_iw * 0.5:
            k += 1
            continue

        # Find margin: │  ┌ = left_margin chars before ┌
        left_margin = m.start() - 1  # chars between outer │ and ┌

        # Calculate right_margin from the ORIGINAL line to maintain container width
        # Original line: │  ┌──...──┐    │
        # right_margin = chars between ┐ and outer │ (inclusive of trailing space)
        outer_right = raw.rindex('│')
        orig_right_margin = outer_right - m.end()  # chars between old ┐ and outer │

        # Target box inner width: fill from left_margin to right edge
        # Total: │(1) + left_margin + ┌(1) + target_w + ┐(1) + right_gap + │(1) = line_len
        # So: target_w = container_iw - left_margin - 2 (for ┌ and ┐)
        # But we also need the right gap: right_gap >= 1 (at least 1 space before outer │)
        # Let's compute: everything between outer │...│ = container_iw
        # left_margin + ┌(1) + target_w + ┐(1) + right_gap = container_iw
        # We want right_gap to stay consistent with the original proportions
        right_gap = max(orig_right_margin, 1)
        target_w = container_iw - left_margin - 2 - right_gap

        if target_w <= inner_box_w:
            k += 1
            continue

        # Find matching bottom border
        bot_k = None
        for j in range(k + 1, min(k + 8, bottom)):
            bots = list(bot_re.finditer(lines[j].rstrip('\n')))
            if len(bots) == 1:
                bot_k = j
                break

        if bot_k is None:
            k += 1
            continue

        trailing_spaces = ' ' * right_gap

        # --- Expand top border ---
        before = raw[:m.start()]
        new_top_border = '┌' + '─' * target_w + '┐'
        lines[k] = before + new_top_border + trailing_spaces + '│' + nl_k

        # --- Expand bottom border ---
        bot_raw = lines[bot_k].rstrip('\n')
        nl_b = '\n' if lines[bot_k].endswith('\n') else ''
        bot_m = list(bot_re.finditer(bot_raw))
        if bot_m:
            bm = bot_m[0]
            before_b = bot_raw[:bm.start()]
            new_bot_border = '└' + '─' * target_w + '┘'
            lines[bot_k] = before_b + new_bot_border + trailing_spaces + '│' + nl_b

        # --- Expand content lines between top and bottom ---
        for c in range(k + 1, bot_k):
            c_raw = lines[c].rstrip('\n')
            nl_c = '\n' if lines[c].endswith('\n') else ''
            inner_pipes = [ii for ii, ch in enumerate(c_raw) if ch == '│']
            if len(inner_pipes) >= 3:
                inner_left = inner_pipes[1]
                # Extract content between 2nd and 2nd-to-last │
                # But after _expand_one_container, pipes may have shifted.
                # Safer: take everything after inner_left│, strip trailing │+spaces+│
                after_inner_left = c_raw[inner_left + 1:]
                # Remove trailing: │ spaces │
                # Find the content by stripping from the right
                stripped_right = after_inner_left.rstrip()
                if stripped_right.endswith('│'):
                    stripped_right = stripped_right[:-1]  # remove last │
                    stripped_right = stripped_right.rstrip()
                    if stripped_right.endswith('│'):
                        stripped_right = stripped_right[:-1]  # remove 2nd last │
                content_text = stripped_right.strip()
                # Rebuild: center-pad to target_w (with 1 leading space)
                content_vw = visual_width(content_text)
                # Keep original leading whitespace pattern (centered)
                # Find leading spaces in original content
                orig_content = c_raw[inner_left + 1:]
                orig_leading = len(orig_content) - len(orig_content.lstrip())
                leading = ' ' * orig_leading if orig_leading > 0 else ' '
                text_with_lead = leading + content_text
                pad = target_w - visual_width(text_with_lead)
                new_content = text_with_lead + ' ' * max(0, pad)
                before_c = c_raw[:inner_left + 1]
                lines[c] = before_c + new_content + '│' + trailing_spaces + '│' + nl_c

        k = bot_k + 1
        continue

    return


def _align_connectors_below(
    lines: list[str],
    source_line: int,
    old_cols: list[int],
    new_cols: list[int],
) -> None:
    """Fix vertical connector positions below a resized box row.

    After a box row is resized its ┬ positions shift, but the │ ▼ ┼
    characters on lines below still sit at the OLD column positions.
    This function rewrites those lines so connectors match the new ┬ cols.

    Scans downward from *source_line* (the bottom border of the resized
    row) until it hits a new box top border (┌…┐).

    Four line types are handled:
      1. Outer bottom with ┼:   └───────┼───┼───┼───┼──────────────┘
      2. Outer bottom no ┼:     └──────────────────────────────────┘
         (after Pass 2 expansion removed ┼ — re-insert them)
      3. Inside-container:      │       │   │   │   │              │
         (first │ at column 0, inner │ are connectors)
      4. Freestanding:                  │   │   │   │   or  ▼ ▼ ▼ ▼
         (first │/▼ is indented — no container walls)
    """
    if len(old_cols) != len(new_cols):
        return

    for k in range(source_line + 1, min(source_line + 15, len(lines))):
        raw = lines[k].rstrip('\n')
        nl = '\n' if lines[k].endswith('\n') else ''

        # Stop at the next inner box top border (┌…┐ with │ margin)
        if '┌' in raw and '┐' in raw:
            break

        stripped = raw.strip()

        # ---- Case 1 & 2: outer bottom border (└ … ┘) ----
        if stripped.startswith('└') and stripped.endswith('┘'):
            lead = len(raw) - len(raw.lstrip())
            old_inner = stripped[1:-1]
            # Need enough width for the rightmost ┼
            needed_inner = max(len(old_inner), max(new_cols) - lead)
            new_inner = list('─' * needed_inner)

            # Place ┼ at new positions
            for new_c in new_cols:
                rel = new_c - lead - 1  # position inside └...┘
                if 0 <= rel < needed_inner:
                    new_inner[rel] = '┼'

            lines[k] = ' ' * lead + '└' + ''.join(new_inner) + '┘' + nl
            continue

        # Collect all │ ▼ characters and their positions
        connectors = [(j, ch) for j, ch in enumerate(raw) if ch in '│▼']
        if not connectors:
            continue

        first_col = connectors[0][0]

        # ---- Case 3: inside container (first │ at column 0) ----
        if first_col == 0 and raw.rstrip().endswith('│') and len(connectors) >= 3:
            inner_connectors = connectors[1:-1]  # exclude outer walls
            if len(inner_connectors) != len(old_cols):
                continue

            last_wall = connectors[-1][0]
            # Build new line: outer walls + inner connectors at new positions
            total_w = max(last_wall + 1, max(new_cols) + 2)
            chars = list(' ' * total_w)
            chars[0] = '│'  # left outer wall
            right_pos = max(last_wall, max(new_cols) + 2)
            if right_pos >= len(chars):
                chars.extend([' '] * (right_pos - len(chars) + 1))
            chars[right_pos] = '│'  # right outer wall
            for (_, ch), new_c in zip(inner_connectors, new_cols):
                if 0 < new_c < len(chars):
                    chars[new_c] = ch
            lines[k] = ''.join(chars).rstrip() + nl
            continue

        # ---- Case 4: freestanding (indented │ or ▼) ----
        if len(connectors) == len(old_cols):
            max_new = max(new_cols) + 1
            chars = list(' ' * max_new)
            for (_, ch), new_c in zip(connectors, new_cols):
                if new_c < len(chars):
                    chars[new_c] = ch
            lines[k] = ''.join(chars).rstrip() + nl


def _algorithmic_reshape(block_lines: list[str]) -> list[str]:
    """Reshape ASCII box diagram to fit translated text (pure Python).

    Two-pass algorithm:
      Pass 1 — resize inner box rows (┌──┐ … └──┘) to fit their content.
      Pass 2 — expand outer containers to fit the (now wider) inner rows.

    Preserves line count: no lines are added or removed.
    """
    lines = list(block_lines)  # work on a copy
    top_re = _box_top_re()
    bot_re = _box_bottom_re()
    processed: set[int] = set()
    connector_fixups: list[tuple[int, list[int], list[int]]] = []

    # ── Pass 1: resize inner box rows ──
    idx = 0
    while idx < len(lines):
        if idx in processed:
            idx += 1
            continue

        top_matches = list(top_re.finditer(lines[idx]))
        if not top_matches:
            idx += 1
            continue

        # Skip outer container borders (handled in Pass 2).
        # Outer tops start with ┌ (no leading │ margin).
        stripped = lines[idx].rstrip('\n').strip()
        if stripped.startswith('┌') and stripped.endswith('┐') and '│' not in stripped:
            idx += 1
            continue

        num_boxes = len(top_matches)
        orig_widths = [m.end() - m.start() - 2 for m in top_matches]

        # Find matching bottom border with same box count
        bottom_idx = None
        for j in range(idx + 1, min(idx + 15, len(lines))):
            if j in processed:
                continue
            bot_matches = list(bot_re.finditer(lines[j]))
            if len(bot_matches) == num_boxes:
                bottom_idx = j
                break

        if bottom_idx is None:
            idx += 1
            continue

        content_indices = list(range(idx + 1, bottom_idx))

        # Calculate required widths from cell content
        max_cw = [0] * num_boxes
        for ci in content_indices:
            cells = _split_cells(lines[ci], num_boxes)
            for bi, cell in enumerate(cells):
                max_cw[bi] = max(max_cw[bi], visual_width(cell.strip()))

        new_widths = [
            max(ow, cw + 2) for ow, cw in zip(orig_widths, max_cw)
        ]

        if new_widths != orig_widths:
            # Record old ┬ positions before rebuild
            old_t_cols = [
                j for j, ch in enumerate(lines[bottom_idx]) if ch == '┬'
            ]

            lines[idx] = _rebuild_border(
                lines[idx], top_matches, new_widths, '┌', '┐'
            )
            bot_matches = list(bot_re.finditer(lines[bottom_idx]))
            lines[bottom_idx] = _rebuild_border(
                lines[bottom_idx], bot_matches, new_widths, '└', '┘'
            )
            for ci in content_indices:
                lines[ci] = _rebuild_cell_line(
                    lines[ci], num_boxes, new_widths
                )

            # Record new ┬ positions after rebuild
            new_t_cols = [
                j for j, ch in enumerate(lines[bottom_idx]) if ch == '┬'
            ]

            # Store mapping for Pass 3
            if old_t_cols and new_t_cols and old_t_cols != new_t_cols:
                connector_fixups.append((bottom_idx, old_t_cols, new_t_cols))

            logger.info(
                f"Resized {num_boxes} box(es) on lines "
                f"{idx}-{bottom_idx}: {orig_widths} → {new_widths}"
            )

        processed.update(range(idx, bottom_idx + 1))
        idx = bottom_idx + 1

    # ── Pass 2: expand outer containers ──
    _expand_containers(lines)

    # ── Pass 3: align vertical connectors to new ┬ positions ──
    for bottom_idx, old_t_cols, new_t_cols in connector_fixups:
        _align_connectors_below(lines, bottom_idx, old_t_cols, new_t_cols)

    # ── Pass 4: collapse multi-space runs in plain text content lines ──
    # Per-token padding leaves gaps like "Đại lý       / Quản trị viên".
    # Only affects │…│ container lines that have NO box-drawing characters
    # (i.e. pure text, not box border/cell lines).
    _box_chars = set('┌┐└┘─┬┼')
    for k in range(len(lines)):
        raw = lines[k].rstrip('\n')
        nl = '\n' if lines[k].endswith('\n') else ''
        stripped = raw.strip()
        if not (stripped.startswith('│') and stripped.endswith('│')):
            continue
        inner = raw[raw.index('│') + 1 : raw.rindex('│')]
        # Skip lines with box-drawing chars (borders, cells)
        if any(ch in _box_chars for ch in inner):
            continue
        # Also skip lines with inner │ (box cell separators)
        if '│' in inner:
            continue
        # Collapse non-leading multi-spaces
        lead_len = len(inner) - len(inner.lstrip())
        leading = inner[:lead_len]
        rest = inner[lead_len:]
        collapsed = re.sub(r'  +', ' ', rest)
        if collapsed != rest:
            # Re-pad to maintain container width
            old_vw = visual_width(inner)
            new_content = leading + collapsed
            pad = old_vw - visual_width(new_content)
            new_inner = new_content + ' ' * max(0, pad)
            left_wall = raw[:raw.index('│')]
            lines[k] = left_wall + '│' + new_inner + '│' + nl

    return lines



def _fix_viet_latin_spacing(text: str) -> str:
    """Insert spaces between Vietnamese words and ASCII Latin/digits.

    Handles three cases:
    1. Vietnamese lowercase + ASCII uppercase:  'nghiệpA'  → 'nghiệp A'
    2. Vietnamese lowercase + ASCII digit:       'phần2'    → 'phần 2'
    3. Abbreviation + CamelCase word:            'RAGTrò'   → 'RAG Trò'
       (2+ uppercase letters followed by uppercase + lowercase)
    """
    if not text:
        return text

    # Pass 1: abbreviation boundary  (e.g. RAGTrò → RAG Trò)
    # Pattern: 2+ uppercase ASCII followed by uppercase+lowercase
    text = re.sub(
        r'([A-Z]{2,})([A-Z][a-zà-ỹ])',
        r'\1 \2',
        text,
    )

    # Pass 2: Insert spaces at Vietnamese↔ASCII boundaries
    result = []
    i = 0
    while i < len(text):
        result.append(text[i])
        if i + 1 < len(text):
            curr = text[i]
            nxt = text[i + 1]

            if curr != ' ' and nxt != ' ':
                insert_space = False

                # Case A: lowercase → ASCII uppercase/digit
                # Only at Vietnamese boundaries (has Vietnamese char nearby)
                # Skips pure-ASCII words like SaaS, OAuth2
                if curr.islower() and (
                    (nxt.isupper() and nxt.isascii())
                    or (nxt.isdigit() and nxt.isascii())
                ):
                    has_viet = any(
                        not text[j].isascii() and text[j].isalpha()
                        for j in range(max(0, i - 2), i + 1)
                    )
                    if has_viet:
                        insert_space = True

                # Case B: ASCII letter → start of Vietnamese word
                # e.g. "SaaSNền" → "SaaS Nền"
                # curr is ASCII alpha, nxt starts a Vietnamese word.
                # A Vietnamese word starts with an uppercase letter followed
                # by a non-ASCII char within the next 2 chars (e.g. Nề, Đạ).
                elif curr.isascii() and curr.isalpha() and nxt.isupper():
                    # nxt is directly non-ASCII uppercase → Vietnamese
                    if not nxt.isascii():
                        insert_space = True
                    else:
                        # nxt is ASCII uppercase (e.g. 'N'), check ahead
                        has_viet_ahead = any(
                            i + 2 + k < len(text)
                            and not text[i + 2 + k].isascii()
                            and text[i + 2 + k].isalpha()
                            for k in range(3)
                        )
                        # Only insert if surrounding context is ASCII
                        # (we're leaving an English word)
                        all_ascii_before = all(
                            text[j].isascii()
                            for j in range(max(0, i - 3), i + 1)
                            if text[j].isalpha()
                        )
                        if has_viet_ahead and all_ascii_before:
                            insert_space = True

                if insert_space:
                    result.append(' ')
        i += 1

    return ''.join(result)


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

    # Process diagram blocks with inline replacement.
    # Strategy: Replace each token IN-PLACE on its own line.
    # - Consume trailing spaces after the JP token to make room
    # - If translation is shorter: pad with spaces
    # - If translation fits in available space (token_vw + trailing): use it
    # - If translation is still longer: place it and accept overflow
    # After inline replacement, if any overflow occurred, send the block
    # to the LLM for box reshaping.
    replaced_count = 0

    for start, end in code_blocks:
        block_lines = lines[start : end + 1]

        # Check if this block has any tokens to replace
        has_tokens = any(i in diagram_lookup for i in range(start, end + 1))
        if not has_tokens:
            continue

        block_has_overflow = False

        for i in range(start, end + 1):
            if i not in diagram_lookup:
                continue
            idx_in_block = i - start
            line = block_lines[idx_in_block]

            # Collect ALL occurrences of each JP token on this line.
            token_occurrences: list[tuple[int, str, str]] = []
            for jp_text, vi_text in diagram_lookup[i]:
                search_start = 0
                while True:
                    pos = line.find(jp_text, search_start)
                    if pos == -1:
                        break
                    token_occurrences.append((pos, jp_text, vi_text))
                    search_start = pos + len(jp_text)

            # Deduplicate
            seen_positions: set[tuple[int, str]] = set()
            unique_occurrences: list[tuple[int, str, str]] = []
            for pos, jp_text, vi_text in token_occurrences:
                key = (pos, jp_text)
                if key not in seen_positions:
                    seen_positions.add(key)
                    unique_occurrences.append((pos, jp_text, vi_text))

            # Sort right-to-left to prevent index shifting
            unique_occurrences.sort(key=lambda x: -x[0])

            for str_idx, jp_text, vi_text in unique_occurrences:
                vi_text = _fix_viet_latin_spacing(vi_text)
                vw_orig = visual_width(jp_text)
                vw_new = visual_width(vi_text)

                # Calculate available space: original token width + trailing spaces
                suffix = line[str_idx + len(jp_text):]
                trailing_spaces = len(suffix) - len(suffix.lstrip(' '))
                available = vw_orig + trailing_spaces

                if vw_new <= available:
                    # Fits: replace and pad with spaces
                    pad = available - vw_new
                    span_end = str_idx + len(jp_text) + trailing_spaces
                    line = (
                        line[:str_idx]
                        + vi_text + " " * pad
                        + line[span_end:]
                    )
                else:
                    # Doesn't fit: replace and accept overflow
                    block_has_overflow = True
                    span_end = str_idx + len(jp_text) + trailing_spaces
                    line = (
                        line[:str_idx]
                        + vi_text
                        + line[span_end:]
                    )

                replaced_count += 1

            block_lines[idx_in_block] = _fix_viet_latin_spacing(line)

        # Algorithmic reshape: fix box borders to fit translated text.
        # Only for blocks with box-drawing corners (┌) — tree diagrams
        # (├── └──) never use ┌, so they are skipped.
        has_boxes = any("┌" in line_str for line_str in block_lines)
        if block_has_overflow and has_boxes:
            logger.info(
                f"Diagram overflow in block [{start}:{end}], "
                f"reshaping boxes algorithmically..."
            )
            block_lines = _algorithmic_reshape(block_lines)

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
                current_line = current_line.replace(jp_cell, _fix_viet_latin_spacing(vi_cell), 1)
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

            translated = _fix_viet_latin_spacing(_strip_hallucinated_prefix(body_lookup[i], prefix))
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
