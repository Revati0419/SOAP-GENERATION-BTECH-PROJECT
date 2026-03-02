"""
run_pipeline.py
===============
Single entry point for the SOAP-Generation dataset pipeline.

Stages
------
  1. download     – fetch DAIC-WOZ ZIPs, extract _TRANSCRIPT.csv + labels
  2. parse        – parse transcripts + attach PHQ-8 labels
  3. translate    – translate to Hindi & Marathi (3 style variants each)
  4. assemble     – combine into final dataset (CSV + JSON)

Usage examples
--------------
  # Full pipeline (download everything, both languages)
  python run_pipeline.py

  # Use the local sample only (no download needed)
  python run_pipeline.py --sample

  # Download + process only specific sessions
  python run_pipeline.py --ids 301 302 303

  # Only Hindi
  python run_pipeline.py --sample --lang hindi

  # Only translate + assemble (skip download/parse)
  python run_pipeline.py --skip download parse

  # Download only first 10 sessions (for testing)
  python run_pipeline.py --limit 10
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to path so pipeline imports work when called from any cwd
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.download         import main as download_main, use_local_sample
from pipeline.parse_transcripts import parse_all
from pipeline.translate         import translate_all
from pipeline.assemble_dataset  import assemble_all


def banner(stage: str):
    print(f"\n{'─'*60}")
    print(f"  STAGE: {stage}")
    print(f"{'─'*60}\n")


def run_pipeline(args):
    skip = set(args.skip or [])
    t0   = time.time()

    # ── Stage 1: Download ──────────────────────────────────────────────────────
    if "download" not in skip:
        banner("1 / 4  –  Download DAIC-WOZ Transcripts")
        if args.sample:
            use_local_sample()
        else:
            # Patch sys.argv so download_main() sees the right flags
            download_argv = []
            if args.ids:
                download_argv += ["--ids"] + [str(i) for i in args.ids]
            if args.limit:
                download_argv += ["--limit", str(args.limit)]
            original_argv = sys.argv
            sys.argv = ["01_download.py"] + download_argv
            download_main()
            sys.argv = original_argv
    else:
        print("[SKIP] Stage 1 – download")

    # ── Stage 2: Parse ────────────────────────────────────────────────────────
    if "parse" not in skip:
        banner("2 / 4  –  Parse Transcripts & Attach Labels")
        summaries = parse_all()
        if not summaries:
            print("[ERROR] No sessions parsed. Exiting.")
            sys.exit(1)
    else:
        print("[SKIP] Stage 2 – parse")

    # ── Stage 3: Translate ────────────────────────────────────────────────────
    if "translate" not in skip:
        banner("3 / 4  –  Translate to Hindi & Marathi")
        languages = args.lang or ["hindi", "marathi"]
        written = translate_all(
            session_ids=args.ids,
            languages=languages,
        )
        if written == 0:
            print("[WARN] No new translations produced (files may already exist).")
    else:
        print("[SKIP] Stage 3 – translate")

    # ── Stage 4: Assemble ─────────────────────────────────────────────────────
    if "assemble" not in skip:
        banner("4 / 4  –  Assemble Final Dataset")
        assemble_all()
    else:
        print("[SKIP] Stage 4 – assemble")

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"  ✓ Pipeline complete in {elapsed:.1f}s")
    print(f"  Final dataset → data/final/")
    print(f"  Master CSV    → data/final/master_dataset.csv")
    print(f"  Master JSON   → data/final/master_dataset.json")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SOAP-Generation dataset pipeline",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--sample", action="store_true",
        help="Use local References/301_P/ sample instead of downloading",
    )
    parser.add_argument(
        "--ids", nargs="+", type=int, default=None,
        help="Specific DAIC-WOZ session IDs to process",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Max number of sessions to download (for quick testing)",
    )
    parser.add_argument(
        "--lang", nargs="+", default=None,
        choices=["hindi", "marathi"],
        help="Target languages (default: both)",
    )
    parser.add_argument(
        "--skip", nargs="+", default=None,
        choices=["download", "parse", "translate", "assemble"],
        help="Stages to skip",
    )
    args = parser.parse_args()
    run_pipeline(args)
