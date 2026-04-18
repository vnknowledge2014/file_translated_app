"""Interactive CLI review tool for XLIFF translation segments.

Reads a .xlf file, shows segments that need review (LOW/MEDIUM confidence),
and allows the user to edit translations directly in the terminal.

Usage:
    python scripts/review_cli.py data/output/sample_vi.xlf
    python scripts/review_cli.py data/output/sample_vi.xlf --show-all
"""

import argparse
import os
import re
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.agent.xliff import import_xliff, export_xliff, detect_xliff_version
from app.agent.confidence import score_segment


# ── ANSI Colors ──
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
BLUE = "\033[94m"
BG_RED = "\033[41m"
BG_YELLOW = "\033[43m"
BG_GREEN = "\033[42m"


def _conf_color(confidence: float) -> str:
    if confidence >= 0.85:
        return GREEN
    elif confidence >= 0.60:
        return YELLOW
    return RED


def _conf_label(confidence: float) -> str:
    if confidence >= 0.85:
        return "HIGH"
    elif confidence >= 0.60:
        return "MEDIUM"
    return "LOW"


def _print_box(title: str, width: int = 60):
    print(f"\n{CYAN}╔{'═' * width}╗{RESET}")
    print(f"{CYAN}║{RESET} {BOLD}{title:<{width - 1}}{RESET}{CYAN}║{RESET}")
    print(f"{CYAN}╠{'═' * width}╣{RESET}")


def _print_box_end(width: int = 60):
    print(f"{CYAN}╚{'═' * width}╝{RESET}")


def main():
    parser = argparse.ArgumentParser(description="Review XLIFF translations interactively")
    parser.add_argument("xliff", help="Path to .xlf file to review")
    parser.add_argument("--show-all", action="store_true", help="Show all segments (not just LOW/MEDIUM)")
    parser.add_argument("--threshold", type=float, default=0.85, help="Confidence threshold for auto-skip (default: 0.85)")
    args = parser.parse_args()

    if not os.path.exists(args.xliff):
        print(f"{RED}Error: File not found: {args.xliff}{RESET}")
        sys.exit(1)

    # Import segments
    print(f"\n{CYAN}📝 Loading:{RESET} {args.xliff}")
    segments = import_xliff(args.xliff)
    version = detect_xliff_version(args.xliff)

    # Score confidence
    for seg in segments:
        seg["confidence"] = score_segment(seg)

    total = len(segments)
    high = sum(1 for s in segments if s["confidence"] >= args.threshold)
    needs_review = [s for s in segments if s["confidence"] < args.threshold]

    if not args.show_all and not needs_review:
        print(f"\n{GREEN}✅ Tất cả {total} đoạn đều đạt HIGH confidence. Không cần review!{RESET}")
        sys.exit(0)

    review_list = segments if args.show_all else needs_review

    # Header
    _print_box(f"📝 Review: {os.path.basename(args.xliff)}  ({len(review_list)} / {total} đoạn)")
    print(f"{CYAN}║{RESET}  {GREEN}● HIGH:{RESET} {high}   {YELLOW}● MEDIUM/LOW:{RESET} {len(needs_review)}   {DIM}(XLIFF {version}){RESET}")
    print(f"{CYAN}║{RESET}  {DIM}Enter: giữ nguyên  |  Gõ text: thay thế  |  q: thoát{RESET}")
    _print_box_end()

    edited_count = 0
    skipped_count = 0

    for i, seg in enumerate(review_list):
        source = seg.get("text", "")
        target = seg.get("translated_text", "")
        conf = seg.get("confidence", 0.0)
        color = _conf_color(conf)
        label = _conf_label(conf)

        print(f"\n{DIM}{'─' * 60}{RESET}")
        print(f"  {BOLD}#{i + 1}/{len(review_list)}{RESET}  [{color}{label} {conf:.0%}{RESET}]")
        print(f"  {DIM}JP:{RESET} {source}")
        print(f"  {DIM}VI:{RESET} {target}")
        print()

        try:
            user_input = input(f"  {CYAN}Sửa (Enter giữ nguyên, 'q' thoát):{RESET} ")
        except (EOFError, KeyboardInterrupt):
            print(f"\n{YELLOW}Interrupted.{RESET}")
            break

        if user_input.strip().lower() == "q":
            break
        elif user_input.strip():
            seg["translated_text"] = user_input.strip()
            edited_count += 1
            print(f"  {GREEN}✓ Đã cập nhật{RESET}")
        else:
            skipped_count += 1

    # Save back
    if edited_count > 0:
        print(f"\n{CYAN}💾 Ghi lại file XLIFF...{RESET}")

        # Reconstruct full segment list with edits merged
        all_segments = segments  # edits are in-place
        original_filename = os.path.basename(args.xliff).replace("_vi.xlf", "").replace(".xlf", "")
        export_xliff(
            all_segments,
            original_filename,
            "docx",  # placeholder type
            args.xliff,
            version=version,
        )
        print(f"{GREEN}✅ Đã lưu: {args.xliff}{RESET}")

    # Summary
    print(f"\n{'═' * 60}")
    print(f"  {BOLD}TÓM TẮT REVIEW{RESET}")
    print(f"{'═' * 60}")
    print(f"  Tổng đoạn review: {len(review_list)}")
    print(f"  Đã sửa:           {GREEN}{edited_count}{RESET}")
    print(f"  Giữ nguyên:        {skipped_count}")
    print(f"  File:              {args.xliff}")
    print()

    if edited_count > 0:
        print(f"  {CYAN}Bước tiếp theo:{RESET} Chạy lệnh sau để xuất file Word:")
        base = original_filename
        print(f"  {BOLD}python scripts/translate_cli.py --file <original.docx> --import-xliff {args.xliff}{RESET}")
    print()


if __name__ == "__main__":
    main()
