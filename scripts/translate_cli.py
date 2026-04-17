"""CLI runner for the JP→VI translation pipeline.

Fully deterministic extraction and reconstruction.
LLM used only for translation (gemma4:e4b).

Usage:
    python scripts/translate_cli.py [--file FILE] [--dir DIR]

Environment variables:
    OLLAMA_URL (default: http://localhost:11434)
    MODEL (default: gemma4:e4b)
"""

import asyncio
import logging
import os
import sys
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.ollama.client import OllamaClient
from app.ollama.model_manager import ModelManager
from app.agent.translator import Translator
from app.agent.orchestrator import Orchestrator
from app.utils.file_detect import detect_file_type

# ── Config ──

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("MODEL", "gemma4:e4b")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(
    os.path.dirname(__file__), "..", "data", "output"
))

# ── Logging ──

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("translate_cli")

# Progress bar
_BAR_WIDTH = 30


def _progress_bar(phase: str, progress: float, message: str):
    filled = int(_BAR_WIDTH * progress)
    bar = "█" * filled + "░" * (_BAR_WIDTH - filled)
    print(f"\r  [{bar}] {progress*100:5.1f}% | {phase:<15} | {message}", end="", flush=True)
    if progress >= 1.0:
        print()


async def translate_one(file_path: str, output_dir: str) -> dict:
    """Translate a single file."""
    abs_path = os.path.abspath(file_path)
    filename = os.path.basename(abs_path)
    file_type = detect_file_type(filename)
    if not file_type:
        logger.error(f"Unsupported file type: {filename}")
        return {"file": filename, "status": "skipped", "error": "unsupported type"}

    base, ext = os.path.splitext(filename)
    output_path = os.path.join(os.path.abspath(output_dir), f"{base}_vi{ext}")

    logger.info("=" * 60)
    logger.info(f"Translating: {filename} (type={file_type})")
    logger.info(f"  Input:  {file_path}")
    logger.info(f"  Output: {output_path}")
    logger.info("=" * 60)

    # Build pipeline
    client = OllamaClient(OLLAMA_URL, timeout=600.0)  # 600s to allow slow local Gemma 4b batch translation
    model_manager = ModelManager(client)
    translator = Translator(client, MODEL)
    orchestrator = Orchestrator(
        model_manager=model_manager,
        translator=translator,
        model=MODEL,
        on_progress=_progress_bar,
    )

    job_id = f"{base}_{file_type}"
    result = await orchestrator.translate_file(
        file_path=abs_path,
        file_type=file_type,
        job_id=job_id,
        output_path=output_path,
    )

    return {"file": filename, **result}


async def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Translate JP→VI documents")
    parser.add_argument("--file", "-f", action="append", help="File(s) to translate. Can be specified multiple times.")
    parser.add_argument("--dir", "-d", help="Directory of files to translate")
    args = parser.parse_args()

    if not args.file and not args.dir:
        parser.print_help()
        sys.exit(1)

    # Verify Ollama connection
    client = OllamaClient(OLLAMA_URL, timeout=90.0)
    try:
        await client.list_models()
        logger.info(f"Ollama connected at {OLLAMA_URL}")
    except Exception as e:
        logger.error(f"Cannot connect to Ollama at {OLLAMA_URL}: {e}")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    files = []
    if args.file:
        files.extend(args.file)
    elif args.dir:
        for f in sorted(os.listdir(args.dir)):
            if detect_file_type(f):
                files.append(os.path.join(args.dir, f))

    results = []
    for f in files:
        r = await translate_one(f, OUTPUT_DIR)
        status_emoji = "✅" if r.get("status") == "completed" else "❌"
        segs = r.get("segments_count", 0)
        dur = r.get("duration_seconds", 0)
        logger.info(f"{status_emoji} {r['file']} → {segs} segments in {dur:.1f}s")
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
    print(f"  Output directory: {os.path.abspath(OUTPUT_DIR)}")


if __name__ == "__main__":
    asyncio.run(main())
