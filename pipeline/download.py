"""
pipeline/01_download.py
=======================
Downloads DAIC-WOZ ZIPs from https://dcapswoz.ict.usc.edu/wwwdaicwoz/
and extracts ONLY the _TRANSCRIPT.csv files (the heavy files like
COVAREP, CLNF, FORMANT are skipped — not needed for Phase 1).

Also downloads:
  - train_split_Depression_AVEC2017.csv
  - dev_split_Depression_AVEC2017.csv
  - full_test_split.csv
which contain the PHQ-8 / depression labels per session.

Usage
-----
  python pipeline/01_download.py                  # download all sessions
  python pipeline/01_download.py --ids 301 302    # download specific sessions
  python pipeline/01_download.py --sample         # use local References/ sample only
"""

import argparse
import os
import sys
import time
import zipfile
from pathlib import Path

import requests
from tqdm import tqdm

# ─── Configuration ────────────────────────────────────────────────────────────
BASE_URL      = "https://dcapswoz.ict.usc.edu/wwwdaicwoz"
RAW_DIR       = Path("data/raw")          # extracted transcripts land here
ZIP_CACHE_DIR = Path("data/zip_cache")    # ZIPs stored here temporarily
LABEL_DIR     = Path("data/labels")       # split / label CSVs

# All session IDs available on the server (300–492, with gaps)
ALL_SESSION_IDS = [
    300,301,302,303,304,305,306,307,308,309,310,
    311,312,313,314,315,316,317,318,319,320,321,
    322,323,324,325,326,327,328,329,330,331,332,
    333,334,335,336,337,338,339,340,341,343,344,
    345,346,347,348,349,350,351,352,353,354,355,
    356,357,358,359,360,361,362,363,364,365,366,
    367,368,369,370,371,372,373,374,375,376,377,
    378,379,380,381,382,383,384,385,386,387,388,
    389,390,391,392,393,395,396,397,399,400,401,
    402,403,404,405,406,407,408,409,410,411,412,
    413,414,415,416,417,418,419,420,421,422,423,
    424,425,426,427,428,429,430,431,432,433,434,
    435,436,437,438,439,440,441,442,443,444,445,
    446,447,448,449,450,451,452,453,454,455,456,
    457,458,459,461,462,463,464,465,466,467,468,
    469,470,471,472,473,474,475,476,477,478,479,
    480,481,482,483,484,485,486,487,488,489,490,
    491,492,
]

LABEL_FILES = [
    "train_split_Depression_AVEC2017.csv",
    "dev_split_Depression_AVEC2017.csv",
    "full_test_split.csv",
]

# Files inside each ZIP we want to keep (everything else is discarded)
KEEP_SUFFIXES = ("_TRANSCRIPT.csv",)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _download_file(url: str, dest: Path, retries: int = 3, chunk: int = 1 << 20) -> bool:
    """Stream-download url → dest, showing a progress bar. Returns True on success."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, stream=True, timeout=60)
            if resp.status_code == 404:
                print(f"  [SKIP] 404 – {url}")
                return False
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            with open(dest, "wb") as f, tqdm(
                total=total, unit="B", unit_scale=True,
                desc=dest.name, leave=False
            ) as bar:
                for data in resp.iter_content(chunk_size=chunk):
                    f.write(data)
                    bar.update(len(data))
            return True
        except Exception as exc:
            print(f"  [WARN] attempt {attempt}/{retries} failed: {exc}")
            time.sleep(2 ** attempt)
    return False


def download_labels():
    """Download the three label / split CSVs."""
    LABEL_DIR.mkdir(parents=True, exist_ok=True)
    for fname in LABEL_FILES:
        dest = LABEL_DIR / fname
        if dest.exists():
            print(f"  [OK]   {fname} already downloaded")
            continue
        url = f"{BASE_URL}/{fname}"
        print(f"  Downloading label file: {fname}")
        _download_file(url, dest)


def extract_transcripts(zip_path: Path, session_id: int) -> list[Path]:
    """
    Open zip_path, extract only files ending with KEEP_SUFFIXES,
    placing them in RAW_DIR/<session_id>_P/.
    Returns list of extracted file paths.
    """
    out_dir = RAW_DIR / f"{session_id}_P"
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            if any(member.endswith(s) for s in KEEP_SUFFIXES):
                # Flatten: just put the file in out_dir regardless of path inside zip
                fname   = Path(member).name
                dest    = out_dir / fname
                data    = zf.read(member)
                dest.write_bytes(data)
                extracted.append(dest)

    return extracted


def process_session(session_id: int, keep_zip: bool = False) -> bool:
    """Download, extract, optionally delete zip. Returns True if new data."""
    zip_name = f"{session_id}_P.zip"
    zip_path = ZIP_CACHE_DIR / zip_name
    out_dir  = RAW_DIR / f"{session_id}_P"

    # Check if transcript already extracted
    transcript = out_dir / f"{session_id}_TRANSCRIPT.csv"
    if transcript.exists():
        return False   # already done

    # Download
    url = f"{BASE_URL}/{zip_name}"
    ZIP_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  ↓ {zip_name}  …")
    ok = _download_file(url, zip_path)
    if not ok:
        return False

    # Extract
    extracted = extract_transcripts(zip_path, session_id)
    print(f"    ✓ extracted {len(extracted)} file(s) → {out_dir}")

    # Remove zip to save disk space (unless --keep-zip)
    if not keep_zip and zip_path.exists():
        zip_path.unlink()

    return True


def use_local_sample():
    """
    Copy the References/301_P/ sample into data/raw/301_P/ so the rest of
    the pipeline can run without any download.
    """
    import shutil
    src = Path("References/301_P")
    dst = RAW_DIR / "301_P"
    if not src.exists():
        print("[ERROR] References/301_P/ not found — cannot use sample mode.")
        sys.exit(1)
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.glob("*_TRANSCRIPT.csv"):
        shutil.copy(f, dst / f.name)
        print(f"  [SAMPLE] copied {f.name} → {dst}")

    # Also create a dummy label CSV so parse step doesn't break
    LABEL_DIR.mkdir(parents=True, exist_ok=True)
    label_csv = LABEL_DIR / "train_split_Depression_AVEC2017.csv"
    if not label_csv.exists():
        label_csv.write_text(
            "Participant_ID,PHQ8_Binary,PHQ8_Score,PHQ_Score,Gender\n"
            "301,0,5,5,1\n"
        )
        print(f"  [SAMPLE] created dummy label CSV → {label_csv}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Download DAIC-WOZ transcripts from dcapswoz.ict.usc.edu"
    )
    parser.add_argument(
        "--ids", nargs="+", type=int, default=None,
        help="Specific session IDs to download (e.g. --ids 301 302 303)"
    )
    parser.add_argument(
        "--sample", action="store_true",
        help="Skip download; use local References/301_P/ sample"
    )
    parser.add_argument(
        "--keep-zip", action="store_true",
        help="Keep downloaded ZIP files after extraction"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Max number of sessions to download (useful for testing)"
    )
    args = parser.parse_args()

    if args.sample:
        print("\n[MODE] Local sample — skipping download\n")
        use_local_sample()
        print("\n✓ Sample data ready in data/raw/")
        return

    print("\n[MODE] Download from dcapswoz.ict.usc.edu\n")

    # Step 1: label CSVs
    print("── Downloading label files ──")
    download_labels()

    # Step 2: session ZIPs
    ids = args.ids if args.ids else ALL_SESSION_IDS
    if args.limit:
        ids = ids[: args.limit]

    print(f"\n── Downloading {len(ids)} session(s) ──")
    new_count = 0
    for sid in ids:
        ok = process_session(sid, keep_zip=args.keep_zip)
        if ok:
            new_count += 1

    print(f"\n✓ Done. {new_count} new session(s) extracted → {RAW_DIR}")
    print(f"  Label files → {LABEL_DIR}")


if __name__ == "__main__":
    main()
