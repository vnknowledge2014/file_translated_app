#!/usr/bin/env python3
"""Unified CLI tool for the Multilingual Translation System.

Subcommands:
    translate   Translate document(s) between languages
    review      Interactive XLIFF review in terminal
    setup       Setup Ollama model for deployment
    project-map Regenerate PROJECT_MAP.md from source
    test-matrix Generate synthetic test files for all language/format combos
    scaffold    Generate prompt skeleton files for new languages/domains

Usage:
    python cli.py translate -f document.docx
    python cli.py translate -f doc.docx --source ja --target vi --domain legal
    python cli.py translate -f doc.docx --export-xliff --xliff-version 2.1
    python cli.py translate -f doc.docx --import-xliff data/output/doc_vi.xlf
    python cli.py review data/output/sample_vi.xlf
    python cli.py setup
    python cli.py project-map
    python cli.py test-matrix --count 10
    python cli.py scaffold
"""

import argparse
import asyncio
import csv
import logging
import os
import subprocess
import sys

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cli")


# ════════════════════════════════════════════════════════════
#  translate — Translate documents
# ════════════════════════════════════════════════════════════

_BAR_WIDTH = 30


def _progress_bar(phase: str, progress: float, message: str):
    filled = int(_BAR_WIDTH * progress)
    bar = "█" * filled + "░" * (_BAR_WIDTH - filled)
    print(f"\r  [{bar}] {progress*100:5.1f}% | {phase:<15} | {message}", end="", flush=True)
    if progress >= 1.0:
        print()


async def _translate_one(
    file_path: str,
    output_dir: str,
    export_xliff_flag: bool = False,
    xliff_version: str = "1.2",
    import_xliff_path: str | None = None,
    no_translate: bool = False,
    glossary: list[dict] | None = None,
    domain_code: str = "general",
) -> dict:
    """Translate a single file through the pipeline."""
    from app.ollama.client import OllamaClient
    from app.ollama.model_manager import ModelManager
    from app.agent.translator import Translator
    from app.agent.orchestrator import Orchestrator
    from app.utils.file_detect import detect_file_type
    from app.config import settings

    abs_path = os.path.abspath(file_path)
    filename = os.path.basename(abs_path)
    file_type = detect_file_type(filename)
    if not file_type:
        logger.error(f"Unsupported file type: {filename}")
        return {"file": filename, "status": "skipped", "error": "unsupported type"}

    base, ext = os.path.splitext(filename)
    output_path = os.path.join(os.path.abspath(output_dir), f"{base}_{settings.TARGET_LANG}{ext}")

    logger.info("=" * 60)
    logger.info(f"Translating: {filename} (type={file_type})")
    logger.info(f"  Input:  {file_path}")
    logger.info(f"  Output: {output_path}")
    logger.info("=" * 60)

    client = OllamaClient(settings.OLLAMA_URL, timeout=600.0)
    model_manager = ModelManager(client)
    translator = Translator(client, settings.MODEL)
    orchestrator = Orchestrator(
        model_manager=model_manager,
        translator=translator,
        model=settings.MODEL,
        on_progress=_progress_bar,
    )

    job_id = f"{base}_{file_type}"
    result = await orchestrator.translate_file(
        file_path=abs_path,
        file_type=file_type,
        job_id=job_id,
        output_path=output_path,
        export_xliff_flag=export_xliff_flag,
        xliff_version=xliff_version,
        import_xliff_path=import_xliff_path,
        no_translate=no_translate,
        glossary=glossary,
        domain_code=domain_code,
    )

    return {"file": filename, **result}


async def cmd_translate(args):
    """Execute the translate subcommand."""
    from app.utils.file_detect import detect_file_type
    from app.config import settings
    from app.ollama.client import OllamaClient

    # Apply overrides
    if args.source:
        settings.SOURCE_LANG = args.source
    if args.target:
        settings.TARGET_LANG = args.target
    if args.domain:
        settings.DEFAULT_DOMAIN = args.domain

    output_dir = settings.OUTPUT_DIR
    if output_dir == "/data/output":
        output_dir = os.path.join(os.path.dirname(__file__), "data", "output")

    logger.info(f"Language pair: {settings.SOURCE_LANG} → {settings.TARGET_LANG} | Domain: {settings.DEFAULT_DOMAIN}")

    # Verify Ollama
    client = OllamaClient(settings.OLLAMA_URL, timeout=90.0)
    try:
        await client.list_models()
        logger.info(f"Ollama connected at {settings.OLLAMA_URL}")
    except Exception as e:
        logger.error(f"Cannot connect to Ollama at {settings.OLLAMA_URL}: {e}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    # Load glossary
    glossary_terms = []
    if args.glossary:
        if not os.path.isfile(args.glossary):
            logger.error(f"Glossary file not found: {args.glossary}")
            sys.exit(1)
        with open(args.glossary, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    first_lower = row[0].strip().lower()
                    if first_lower in ("jp", "japanese", "source", "source_text", "原文"):
                        continue
                    glossary_terms.append({
                        "source_text": row[0].strip(),
                        "target_text": row[1].strip(),
                        "context": row[2].strip() if len(row) > 2 else "",
                    })
        logger.info(f"Loaded {len(glossary_terms)} glossary terms from {args.glossary}")

    # Collect files
    files = []
    if args.file:
        files.extend(args.file)
    elif args.dir:
        for f in sorted(os.listdir(args.dir)):
            if detect_file_type(f):
                files.append(os.path.join(args.dir, f))

    # Translate each file
    results = []
    for f in files:
        r = await _translate_one(
            f, output_dir,
            export_xliff_flag=args.export_xliff,
            xliff_version=args.xliff_version,
            import_xliff_path=args.import_xliff,
            no_translate=args.no_translate,
            glossary=glossary_terms if args.glossary else None,
            domain_code=settings.DEFAULT_DOMAIN,
        )
        status_emoji = "✅" if r.get("status") == "completed" else "❌"
        segs = r.get("segments_count", 0)
        dur = r.get("duration_seconds", 0)
        logger.info(f"{status_emoji} {r['file']} → {segs} segments in {dur:.1f}s")

        conf_stats = r.get("confidence_stats")
        if conf_stats:
            logger.info(
                f"   Confidence: {conf_stats['high_count']} HIGH, "
                f"{conf_stats['medium_count']} MEDIUM, {conf_stats['low_count']} LOW "
                f"(avg={conf_stats['avg_confidence']:.2f})"
            )
        if r.get("xliff_path"):
            logger.info(f"   XLIFF: {r['xliff_path']}")

        results.append(r)

    # Summary
    print()
    print("=" * 60)
    print("  TRANSLATION SUMMARY")
    print("=" * 60)
    total_time = 0
    ok = 0
    for r in results:
        status = "✅" if r.get("status") == "completed" else "❌"
        segs = r.get("segments_count", 0)
        dur = r.get("duration_seconds", 0)
        total_time += dur
        if r.get("status") == "completed":
            ok += 1
        print(f"  {status} {r['file']:<40} | {segs:>4} segs | {dur:.1f}s")

    print(f"\n  Total: {ok}/{len(results)} succeeded in {total_time:.1f}s")
    print(f"  Output directory: {os.path.abspath(output_dir)}")


# ════════════════════════════════════════════════════════════
#  review — Interactive XLIFF review
# ════════════════════════════════════════════════════════════

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"


def _conf_color(c: float) -> str:
    return GREEN if c >= 0.85 else (YELLOW if c >= 0.60 else RED)


def _conf_label(c: float) -> str:
    return "HIGH" if c >= 0.85 else ("MEDIUM" if c >= 0.60 else "LOW")


def cmd_review(args):
    """Execute the review subcommand."""
    from app.agent.xliff import import_xliff, export_xliff, detect_xliff_version
    from app.agent.confidence import score_segment

    if not os.path.exists(args.xliff):
        print(f"{RED}Error: File not found: {args.xliff}{RESET}")
        sys.exit(1)

    print(f"\n{CYAN}📝 Loading:{RESET} {args.xliff}")
    segments = import_xliff(args.xliff)
    version = detect_xliff_version(args.xliff)

    for seg in segments:
        seg["confidence"] = score_segment(seg)

    total = len(segments)
    needs_review = [s for s in segments if s["confidence"] < args.threshold]
    high = total - len(needs_review)

    if not args.show_all and not needs_review:
        print(f"\n{GREEN}✅ All {total} segments are HIGH confidence. No review needed!{RESET}")
        sys.exit(0)

    review_list = segments if args.show_all else needs_review

    print(f"\n{CYAN}╔{'═' * 60}╗{RESET}")
    print(f"{CYAN}║{RESET} {BOLD}📝 Review: {os.path.basename(args.xliff)}  ({len(review_list)} / {total}){' ' * 10}{RESET}{CYAN}║{RESET}")
    print(f"{CYAN}╠{'═' * 60}╣{RESET}")
    print(f"{CYAN}║{RESET}  {GREEN}● HIGH:{RESET} {high}   {YELLOW}● MEDIUM/LOW:{RESET} {len(needs_review)}   {DIM}(XLIFF {version}){RESET}")
    print(f"{CYAN}║{RESET}  {DIM}Enter: keep  |  Type text: replace  |  q: quit{RESET}")
    print(f"{CYAN}╚{'═' * 60}╝{RESET}")

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
        print(f"  {DIM}SRC:{RESET} {source}")
        print(f"  {DIM}TGT:{RESET} {target}")
        print()

        try:
            user_input = input(f"  {CYAN}Edit (Enter to keep, 'q' to quit):{RESET} ")
        except (EOFError, KeyboardInterrupt):
            print(f"\n{YELLOW}Interrupted.{RESET}")
            break

        if user_input.strip().lower() == "q":
            break
        elif user_input.strip():
            seg["translated_text"] = user_input.strip()
            edited_count += 1
            print(f"  {GREEN}✓ Updated{RESET}")
        else:
            skipped_count += 1

    if edited_count > 0:
        print(f"\n{CYAN}💾 Saving XLIFF...{RESET}")
        original_filename = os.path.basename(args.xliff).replace("_vi.xlf", "").replace(".xlf", "")
        export_xliff(segments, original_filename, "docx", args.xliff, version=version)
        print(f"{GREEN}✅ Saved: {args.xliff}{RESET}")

    print(f"\n{'═' * 60}")
    print(f"  {BOLD}REVIEW SUMMARY{RESET}")
    print(f"{'═' * 60}")
    print(f"  Reviewed:  {len(review_list)}")
    print(f"  Edited:    {GREEN}{edited_count}{RESET}")
    print(f"  Unchanged: {skipped_count}")
    print()

    if edited_count > 0:
        print(f"  {CYAN}Next step:{RESET} Reconstruct with:")
        print(f"  {BOLD}python cli.py translate -f <original.docx> --import-xliff {args.xliff}{RESET}")
    print()


# ════════════════════════════════════════════════════════════
#  setup — Ollama model setup
# ════════════════════════════════════════════════════════════

def cmd_setup(args):
    """Setup Ollama model for deployment."""
    from app.config import settings

    model = args.model or settings.MODEL

    print("=" * 50)
    print(f"  Multilingual Translation — Model Setup")
    print("=" * 50)

    # Check Ollama
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print("ERROR: Ollama is not running. Start it first: ollama serve")
            sys.exit(1)
    except FileNotFoundError:
        print("ERROR: 'ollama' command not found. Install Ollama first.")
        sys.exit(1)

    print(f"\n[1/2] Pulling {model}...")
    subprocess.run(["ollama", "pull", model], check=True)

    print(f"\n[2/2] Verifying model...")
    subprocess.run(["ollama", "list"], check=True)

    print(f"\n✅ Model ready!")
    print(f"   For air-gapped deployment: transfer ~/.ollama/models to target server.")
    print(f"   Then run: docker compose up -d")


# ════════════════════════════════════════════════════════════
#  project-map — Regenerate PROJECT_MAP.md
# ════════════════════════════════════════════════════════════

def cmd_project_map(args):
    """Regenerate PROJECT_MAP.md from source analysis."""
    import ast
    import json

    ROOT_DIR = os.path.dirname(__file__) or "."
    GRAPH_FILE = os.path.join(ROOT_DIR, ".omni/knowledge-graph.json")
    OUTPUT_FILE = os.path.join(ROOT_DIR, "PROJECT_MAP.md")

    EXCLUDE_DIRS = {
        ".agent", ".git", "__pycache__", "venv", "data", ".pytest_cache", ".omni", "scripts",
        "node_modules", "models", "samples", ".svelte-kit", "build", "paraglide", "project.inlang",
    }
    EXCLUDE_FILES = {"AGENTS.md", "omni.config.yaml", "translation_cache.db"}
    EXCLUDE_EXTS = {".pyc", ".db", ".png", ".jpg", ".patch", ".so"}

    def should_process(filepath):
        parts = filepath.split(os.sep)
        if any(e in parts for e in EXCLUDE_DIRS):
            return False
        fn = os.path.basename(filepath)
        if fn in EXCLUDE_FILES:
            return False
        _, ext = os.path.splitext(fn)
        return ext not in EXCLUDE_EXTS

    def extract_py_meta(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            docstring = ast.get_docstring(tree) or ""
            classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)][:5]
            functions = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)][:5]
            return {"docstring": docstring.split("\n")[0], "classes": classes, "functions": functions}
        except Exception:
            return None

    print("Discovering files...")
    files = []
    for root, dirs, filenames in os.walk(ROOT_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in filenames:
            fp = os.path.normpath(os.path.join(root, f))
            if should_process(fp):
                files.append(fp)
    files.sort()
    print(f"Found {len(files)} files to analyze.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write("# Project Map (Agent-Friendly Context)\n\n")
        out.write("> Semantic summaries and structural metadata for all core project files.\n\n")

        backend_files = [f for f in files if f.startswith("backend/app")]
        test_files = [f for f in files if f.startswith("backend/tests")]
        other_files = [f for f in files if f not in backend_files and f not in test_files]

        for title, group in [
            ("## 1. Core Application (backend/app)", backend_files),
            ("## 2. Tests (backend/tests)", test_files),
            ("## 3. Configuration & Root", other_files),
        ]:
            if not group:
                continue
            out.write(f"{title}\n\n")
            for fp in group:
                out.write(f"### `{fp}`\n")
                if fp.endswith(".py"):
                    meta = extract_py_meta(fp)
                    if meta:
                        out.write(f"- **Purpose:** {meta['docstring'] or 'No docstring.'}\n")
                        if meta["classes"]:
                            out.write(f"- **Classes:** {', '.join(meta['classes'])}\n")
                        if meta["functions"]:
                            out.write(f"- **Functions:** {', '.join(meta['functions'])}\n")
                else:
                    out.write("- **Type:** Non-Python resource/config file.\n")
                out.write("\n")

    print(f"Successfully wrote {OUTPUT_FILE}!")


# ════════════════════════════════════════════════════════════
#  scaffold — Generate prompt skeleton files
# ════════════════════════════════════════════════════════════

def cmd_scaffold(args):
    """Generate prompt skeleton files for languages/domains that don't have them yet."""
    from app.languages import SUPPORTED_LANGUAGES
    from app.domains import SUPPORTED_DOMAINS

    base_dir = os.path.join(os.path.dirname(__file__), "backend/app/prompts")
    src_dir = os.path.join(base_dir, "skills/languages/source")
    tgt_dir = os.path.join(base_dir, "skills/languages/target")
    dom_dir = os.path.join(base_dir, "skills/domains")

    os.makedirs(src_dir, exist_ok=True)
    os.makedirs(tgt_dir, exist_ok=True)
    os.makedirs(dom_dir, exist_ok=True)

    created = 0

    for code, domain in SUPPORTED_DOMAINS.items():
        path = os.path.join(dom_dir, f"{code}.md")
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# Domain: {domain.name}\n\n")
                f.write(f"- {domain.persona_prompt.strip()}\n")
                f.write(f"- {domain.style_rules.strip()}\n")
            print(f"  Created: {path}")
            created += 1

    for lang in SUPPORTED_LANGUAGES.values():
        for dir_path, template in [
            (src_dir, f"# Source Language Profile: {lang.name} ({lang.code.upper()})\n\n"
                      f"- Auto-generated profile for {lang.name}.\n"),
            (tgt_dir, f"# Target Language Style Guide: {lang.name} ({lang.code.upper()})\n\n"
                      f"- Translate into natural, professional {lang.name}.\n"
                      f"- Maintain technical consistency according to the domain.\n"),
        ]:
            path = os.path.join(dir_path, f"{lang.code}.md")
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(template)
                print(f"  Created: {path}")
                created += 1

    if created == 0:
        print("All prompt files already exist. Nothing to create.")
    else:
        print(f"\nCreated {created} new prompt files.")


# ════════════════════════════════════════════════════════════
#  Main parser
# ════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        prog="cli",
        description="🌐 Multilingual Translation System — Unified CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── translate ──
    p_translate = subparsers.add_parser("translate", aliases=["t"], help="Translate document(s)")
    p_translate.add_argument("--file", "-f", action="append", help="File(s) to translate (repeatable)")
    p_translate.add_argument("--dir", "-d", help="Directory of files to translate")
    p_translate.add_argument("--source", "-s", default=None, help="Source language code (default: from .env)")
    p_translate.add_argument("--target", "-t", default=None, help="Target language code (default: from .env)")
    p_translate.add_argument("--domain", default=None, help="Translation domain (general, it, legal, medical, finance, marketing)")
    p_translate.add_argument("--export-xliff", action="store_true", help="Export bilingual XLIFF alongside output")
    p_translate.add_argument("--xliff-version", default="1.2", choices=["1.2", "2.1"], help="XLIFF version")
    p_translate.add_argument("--import-xliff", type=str, help="Import reviewed XLIFF (skip LLM)")
    p_translate.add_argument("--no-translate", action="store_true", help="Export blank XLIFF without translation")
    p_translate.add_argument("--glossary", type=str, help="CSV glossary file (source, target, context)")

    # ── review ──
    p_review = subparsers.add_parser("review", aliases=["r"], help="Interactive XLIFF review in terminal")
    p_review.add_argument("xliff", help="Path to .xlf file")
    p_review.add_argument("--show-all", action="store_true", help="Show all segments (not just LOW/MEDIUM)")
    p_review.add_argument("--threshold", type=float, default=0.85, help="Confidence threshold (default: 0.85)")

    # ── setup ──
    p_setup = subparsers.add_parser("setup", help="Setup Ollama model")
    p_setup.add_argument("--model", type=str, default=None, help="Model name to pull (default: from .env)")

    # ── project-map ──
    subparsers.add_parser("project-map", aliases=["pm"], help="Regenerate PROJECT_MAP.md")

    # ── scaffold ──
    subparsers.add_parser("scaffold", help="Generate missing prompt skeleton files")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    cmd = args.command

    if cmd in ("translate", "t"):
        if not args.file and not args.dir:
            print("Error: --file or --dir is required")
            sys.exit(1)
        asyncio.run(cmd_translate(args))
    elif cmd in ("review", "r"):
        cmd_review(args)
    elif cmd == "setup":
        cmd_setup(args)
    elif cmd in ("project-map", "pm"):
        cmd_project_map(args)
    elif cmd == "scaffold":
        cmd_scaffold(args)


if __name__ == "__main__":
    main()
