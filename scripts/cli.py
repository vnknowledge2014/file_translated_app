#!/usr/bin/env python3
"""Unified CLI tool for the Multilingual Translation System.

Subcommands:
    config      Configure API key and server URL
    status      Check server connection and auth status
    translate   Translate document(s) via HTTP API
    jobs        Manage translation jobs
    download    Download translated output or XLIFF
    glossary    Manage glossary terms
    review      Interactive XLIFF review in terminal
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import sys
import time

try:
    import httpx
except ImportError:
    print("Error: 'httpx' package is required. Please install it with 'pip install httpx'.")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cli")

# ════════════════════════════════════════════════════════════
#  Configuration & HTTP Client
# ════════════════════════════════════════════════════════════

CONFIG_FILE = os.path.expanduser("~/.infitrans.json")

def _load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"api_key": None, "server": "http://localhost:8000"}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def _save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def _api_call(method, path, **kwargs):
    config = _load_config()
    if not config.get("api_key"):
        print("❌ API key not configured. Run: python cli.py config --api-key <KEY>")
        sys.exit(1)
        
    headers = kwargs.pop("headers", {})
    headers["X-API-Key"] = config["api_key"]
    url = f"{config['server'].rstrip('/')}/api{path}"
    
    timeout = kwargs.pop("timeout", 60.0)
    
    try:
        response = httpx.request(method, url, headers=headers, timeout=timeout, **kwargs)
        if response.status_code == 401:
            print("❌ Authentication failed. Invalid or revoked API key.")
            sys.exit(1)
        response.raise_for_status()
        return response
    except httpx.ConnectError:
        print(f"❌ Could not connect to server at {config['server']}")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        err_msg = ""
        try:
            err_msg = e.response.json().get("detail", "")
        except:
            err_msg = e.response.text
        print(f"❌ Server returned {e.response.status_code}: {err_msg}")
        sys.exit(1)

# ════════════════════════════════════════════════════════════
#  config
# ════════════════════════════════════════════════════════════

def cmd_config(args):
    config = _load_config()
    
    if args.show:
        print("Current Configuration:")
        print(f"  Server: {config.get('server')}")
        key = config.get('api_key')
        if key:
            masked = key[:18] + "..." + key[-4:] if len(key) > 22 else "..."
            print(f"  API Key: {masked}")
        else:
            print("  API Key: Not set")
        return

    updated = False
    if args.api_key:
        config["api_key"] = args.api_key
        updated = True
    if args.server:
        config["server"] = args.server
        updated = True
        
    if updated:
        _save_config(config)
        print("✅ Configuration updated successfully.")
    else:
        print("No changes provided. Use --help for usage.")

# ════════════════════════════════════════════════════════════
#  status
# ════════════════════════════════════════════════════════════

def cmd_status(args):
    config = _load_config()
    print(f"Connecting to {config.get('server')} ...")
    
    res = _api_call("GET", "/keys")
    keys = res.json()
    
    current_key_prefix = config.get("api_key", "")[:20]
    matched_key = next((k for k in keys if k["key_prefix"] == current_key_prefix), None)
    
    print("✅ Connection successful.")
    if matched_key:
        print(f"  API Key: {matched_key['name']} ({matched_key['key_prefix']})")
        print(f"  Scope:   {matched_key['scope']}")
        print(f"  Usage:   {matched_key['requests_count']} requests, {matched_key['pages_used']} pages")
    else:
        print("  Key is valid but not found in user's key list.")

# ════════════════════════════════════════════════════════════
#  translate
# ════════════════════════════════════════════════════════════

def _progress_bar(phase: str, progress: float, message: str):
    _BAR_WIDTH = 30
    filled = int(_BAR_WIDTH * progress)
    bar = "█" * filled + "░" * (_BAR_WIDTH - filled)
    print(f"\r  [{bar}] {progress*100:5.1f}% | {phase:<15} | {message}", end="", flush=True)

def cmd_translate(args):
    files = []
    if args.file:
        files.extend(args.file)
    elif args.dir:
        resolved_dir = os.path.realpath(args.dir)
        for f in sorted(os.listdir(resolved_dir)):
            if os.path.isfile(os.path.join(resolved_dir, f)):
                files.append(os.path.join(resolved_dir, f))
                
    if not files:
        print("Error: No files specified.")
        sys.exit(1)

    jobs_created = []

    for filepath in files:
        if not os.path.isfile(filepath):
            print(f"Skipping {filepath} (not found)")
            continue
            
        print(f"Uploading {os.path.basename(filepath)}...")
        
        data = {
            "export_xliff": str(args.export_xliff).lower(),
            "xliff_version": args.xliff_version,
            "no_translate": str(args.no_translate).lower(),
        }
        if args.source:
            data["source_lang"] = args.source
        if args.target:
            data["target_lang"] = args.target
        if args.domain:
            data["domain"] = args.domain

        with open(filepath, "rb") as f:
            files_payload = {"file": (os.path.basename(filepath), f)}
            res = _api_call("POST", "/upload", data=data, files=files_payload, timeout=300.0)
            
        job = res.json()
        if "error" in job:
            print(f"❌ Error uploading {os.path.basename(filepath)}: {job['error']}")
        else:
            print(f"✅ Job created: {job['job_id']}")
            jobs_created.append(job['job_id'])

    if args.wait and jobs_created:
        print("\nWaiting for jobs to complete...")
        completed = set()
        
        while len(completed) < len(jobs_created):
            for jid in jobs_created:
                if jid in completed:
                    continue
                    
                res = _api_call("GET", f"/jobs/{jid}")
                job = res.json()
                
                status = job.get("status")
                if status in ("completed", "failed"):
                    print(f"\n{jid} -> {status.upper()}")
                    if status == "failed":
                        print(f"  Error: {job.get('error_message')}")
                    else:
                        print(f"  Done in {job.get('duration_seconds', 0):.1f}s, {job.get('segments_count', 0)} segments.")
                        if getattr(args, 'auto_download', True):
                            cmd_download(argparse.Namespace(job_id=jid, xliff=args.export_xliff, output=None))
                    completed.add(jid)
                else:
                    progress = job.get("progress", 0.0)
                    msg = job.get("progress_message", "")
                    _progress_bar(status, progress, msg)
            
            if len(completed) < len(jobs_created):
                time.sleep(3)

# ════════════════════════════════════════════════════════════
#  jobs
# ════════════════════════════════════════════════════════════

def cmd_jobs(args):
    if args.job_id:
        if args.retry:
            print(f"Retrying job {args.job_id}...")
            res = _api_call("POST", f"/jobs/{args.job_id}/retry")
            print("✅ " + str(res.json()))
        elif args.delete:
            print(f"Deleting job {args.job_id}...")
            res = _api_call("DELETE", f"/jobs/{args.job_id}")
            print("✅ " + str(res.json()))
        else:
            res = _api_call("GET", f"/jobs/{args.job_id}")
            print(json.dumps(res.json(), indent=2))
        return

    params = {}
    if args.status:
        params["status"] = args.status
        
    res = _api_call("GET", "/jobs", params=params)
    jobs = res.json()
    
    if not jobs:
        print("No jobs found.")
        return
        
    print(f"{'ID':<25} | {'Status':<10} | {'Filename':<30} | {'Date'}")
    print("-" * 80)
    for j in jobs:
        print(f"{j['id']:<25} | {j['status']:<10} | {j['filename']:<30} | {j.get('created_at', '')}")

# ════════════════════════════════════════════════════════════
#  download
# ════════════════════════════════════════════════════════════

def cmd_download(args):
    params = {}
    if args.xliff:
        params["xliff"] = "true"
        
    print(f"Downloading {'XLIFF for ' if args.xliff else ''}job {args.job_id}...")
    res = _api_call("GET", f"/download/{args.job_id}", params=params)
    
    cd = res.headers.get("content-disposition", "")
    filename = f"download_{args.job_id}"
    if 'filename="' in cd:
        filename = cd.split('filename="')[1].split('"')[0]
        
    out_dir = args.output or "."
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)
    
    with open(out_path, "wb") as f:
        f.write(res.content)
        
    print(f"✅ Saved to {out_path}")

# ════════════════════════════════════════════════════════════
#  glossary
# ════════════════════════════════════════════════════════════

def cmd_glossary(args):
    if args.action == "list" or not args.action:
        res = _api_call("GET", "/glossary")
        data = res.json()
        terms = data.get("terms", [])
        print(f"Glossary ({data.get('source_lang')} -> {data.get('target_lang')}): {len(terms)} terms")
        for t in terms[:20]:
            print(f"  {t['id'][:8]}... | {t['source_text']} -> {t['target_text']} ({t.get('context', '')})")
        if len(terms) > 20:
            print(f"  ... and {len(terms)-20} more.")
            
    elif args.action == "upload":
        if not args.file:
            print("Error: --file is required for upload")
            sys.exit(1)
        with open(args.file, "rb") as f:
            res = _api_call("POST", "/glossary/upload", files={"file": f})
            print("✅ " + str(res.json()))
            
    elif args.action == "delete":
        if not args.term_id:
            print("Error: term ID required")
            sys.exit(1)
        res = _api_call("DELETE", f"/glossary/{args.term_id}")
        print("✅ " + str(res.json()))

# ════════════════════════════════════════════════════════════
#  review (local XLIFF)
# ════════════════════════════════════════════════════════════

def cmd_review(args):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
    from app.agent.xliff import import_xliff, export_xliff, detect_xliff_version
    from app.agent.confidence import score_segment

    if not os.path.exists(args.xliff):
        print(f"Error: File not found: {args.xliff}")
        sys.exit(1)

    print(f"\n📝 Loading: {args.xliff}")
    segments = import_xliff(args.xliff)
    version = detect_xliff_version(args.xliff)

    for seg in segments:
        seg["confidence"] = score_segment(seg)

    total = len(segments)
    needs_review = [s for s in segments if s["confidence"] < args.threshold]
    high = total - len(needs_review)

    if not args.show_all and not needs_review:
        print(f"\n✅ All {total} segments are HIGH confidence. No review needed!")
        sys.exit(0)

    review_list = segments if args.show_all else needs_review

    print(f"\n╔{'═' * 60}╗")
    print(f"║ 📝 Review: {os.path.basename(args.xliff)}  ({len(review_list)} / {total}){' ' * 10}║")
    print(f"╠{'═' * 60}╣")
    print(f"║  ● HIGH: {high}   ● MEDIUM/LOW: {len(needs_review)}   (XLIFF {version})")
    print(f"║  Enter: keep  |  Type text: replace  |  q: quit")
    print(f"╚{'═' * 60}╝")

    edited_count = 0
    skipped_count = 0

    for i, seg in enumerate(review_list):
        source = seg.get("text", "")
        target = seg.get("translated_text", "")
        conf = seg.get("confidence", 0.0)

        print(f"\n{'─' * 60}")
        print(f"  #{i + 1}/{len(review_list)}  [Conf: {conf:.0%}]")
        print(f"  SRC: {source}")
        print(f"  TGT: {target}\n")

        try:
            user_input = input(f"  Edit (Enter to keep, 'q' to quit): ")
        except (EOFError, KeyboardInterrupt):
            print(f"\nInterrupted.")
            break

        if user_input.strip().lower() == "q":
            break
        elif user_input.strip():
            seg["translated_text"] = user_input.strip()
            edited_count += 1
            print(f"  ✓ Updated")
        else:
            skipped_count += 1

    if edited_count > 0:
        print(f"\n💾 Saving XLIFF...")
        original_filename = os.path.basename(args.xliff).replace("_vi.xlf", "").replace(".xlf", "")
        export_xliff(segments, original_filename, "docx", args.xliff, version=version)
        print(f"✅ Saved: {args.xliff}")

    print(f"\n{'═' * 60}")
    print(f"  REVIEW SUMMARY")
    print(f"{'═' * 60}")
    print(f"  Reviewed:  {len(review_list)}")
    print(f"  Edited:    {edited_count}")
    print(f"  Unchanged: {skipped_count}\n")

# ════════════════════════════════════════════════════════════
#  Main parser
# ════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        prog="cli",
        description="🌐 Multilingual Translation System — HTTP CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    p_config = subparsers.add_parser("config", help="Configure CLI")
    p_config.add_argument("--api-key", help="Set API key")
    p_config.add_argument("--server", help="Set Server URL (e.g., http://localhost:8000)")
    p_config.add_argument("--show", action="store_true", help="Show current config")

    subparsers.add_parser("status", help="Check connection and auth status")

    p_translate = subparsers.add_parser("translate", aliases=["t"], help="Translate document(s)")
    p_translate.add_argument("--file", "-f", action="append", help="File(s) to upload")
    p_translate.add_argument("--dir", "-d", help="Directory of files to upload")
    p_translate.add_argument("--source", "-s", help="Source language")
    p_translate.add_argument("--target", "-t", help="Target language")
    p_translate.add_argument("--domain", help="Domain")
    p_translate.add_argument("--export-xliff", action="store_true", help="Export XLIFF")
    p_translate.add_argument("--xliff-version", default="1.2", choices=["1.2", "2.1"])
    p_translate.add_argument("--no-translate", action="store_true", help="Export blank XLIFF")
    p_translate.add_argument("--wait", action="store_true", help="Wait for completion and auto-download")

    p_jobs = subparsers.add_parser("jobs", aliases=["j"], help="Manage jobs")
    p_jobs.add_argument("job_id", nargs="?", help="Job ID")
    p_jobs.add_argument("--status", help="Filter by status (for list)")
    p_jobs.add_argument("--retry", action="store_true", help="Retry failed job")
    p_jobs.add_argument("--delete", action="store_true", help="Delete job")

    p_dl = subparsers.add_parser("download", aliases=["dl"], help="Download output")
    p_dl.add_argument("job_id", help="Job ID")
    p_dl.add_argument("--xliff", action="store_true", help="Download XLIFF instead of target doc")
    p_dl.add_argument("-o", "--output", help="Output directory")

    p_glos = subparsers.add_parser("glossary", aliases=["g"], help="Manage glossary")
    p_glos.add_argument("action", nargs="?", choices=["list", "upload", "delete"])
    p_glos.add_argument("--file", help="CSV file for upload")
    p_glos.add_argument("--term-id", help="Term ID to delete")

    p_review = subparsers.add_parser("review", aliases=["r"], help="Interactive XLIFF review")
    p_review.add_argument("xliff", help="Path to .xlf file")
    p_review.add_argument("--show-all", action="store_true", help="Show all segments")
    p_review.add_argument("--threshold", type=float, default=0.85, help="Confidence threshold")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    cmd = args.command
    if cmd == "config":
        cmd_config(args)
    elif cmd == "status":
        cmd_status(args)
    elif cmd in ("translate", "t"):
        cmd_translate(args)
    elif cmd in ("jobs", "j"):
        cmd_jobs(args)
    elif cmd in ("download", "dl"):
        cmd_download(args)
    elif cmd in ("glossary", "g"):
        cmd_glossary(args)
    elif cmd in ("review", "r"):
        cmd_review(args)
    else:
        print(f"Command '{cmd}' is deprecated in the HTTP client or not implemented yet.")

if __name__ == "__main__":
    main()
