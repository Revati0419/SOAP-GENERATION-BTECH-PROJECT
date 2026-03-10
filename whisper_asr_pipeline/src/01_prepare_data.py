"""
01_prepare_data.py
──────────────────
Step 1 of the Whisper Medical ASR pipeline.

What this script does:
  1. Validates your raw audio files and metadata.csv
  2. Resamples all audio to 16kHz mono (Whisper's required format)
  3. Trims silence from start/end of clips
  4. Normalises audio loudness
  5. Splits dataset into train/validation/test (80/10/10)
  6. Saves HuggingFace Dataset to data/processed/

Usage:
    python src/01_prepare_data.py
    python src/01_prepare_data.py --data_dir data/raw --min_duration 1.0
"""

import os
import sys
import csv
import json
import argparse
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from tqdm import tqdm

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────
RAW_DIR       = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
TARGET_SR     = 16000          # Whisper required sample rate
MIN_DURATION  = 1.0            # seconds — drop clips shorter than this
MAX_DURATION  = 30.0           # seconds — drop clips longer than this
TRAIN_SPLIT   = 0.80
VAL_SPLIT     = 0.10
# TEST_SPLIT  = 0.10           # remainder

# ─────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────

def load_audio(path: str, target_sr: int = TARGET_SR):
    """Load audio file, resample to target_sr, return (samples, sr)."""
    import librosa
    audio, sr = librosa.load(path, sr=target_sr, mono=True)
    return audio, sr


def trim_silence(audio: np.ndarray, sr: int, top_db: int = 30):
    """Trim leading/trailing silence."""
    import librosa
    trimmed, _ = librosa.effects.trim(audio, top_db=top_db)
    return trimmed


def normalize_audio(audio: np.ndarray) -> np.ndarray:
    """Peak normalize audio to -1.0 to 1.0."""
    peak = np.abs(audio).max()
    if peak > 0:
        audio = audio / peak * 0.95
    return audio


def duration_seconds(audio: np.ndarray, sr: int) -> float:
    return len(audio) / sr


def validate_transcript(text: str) -> bool:
    """Basic transcript validation."""
    if not text or not isinstance(text, str):
        return False
    text = text.strip()
    if len(text) < 3:
        return False
    if len(text) > 500:
        return False
    return True


def clean_transcript(text: str) -> str:
    """Clean and normalise transcript text."""
    import re
    text = text.strip()
    # Normalise whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing punctuation that isn't meaningful
    return text

# ─────────────────────────────────────────────────────
# MAIN PROCESSING
# ─────────────────────────────────────────────────────

def process_dataset(data_dir: Path, min_duration: float, max_duration: float):
    """
    Main processing function.
    Expects data_dir to contain:
      - metadata.csv  (columns: file_name, transcript, language)
      - *.wav files
    """
    print("\n" + "="*60)
    print("  STEP 1: Data Preparation")
    print("="*60)

    # ── Load metadata ──────────────────────────────────
    meta_path = data_dir / "metadata.csv"
    if not meta_path.exists():
        print(f"\n❌  metadata.csv not found at {meta_path}")
        print("\nExpected format:")
        print("  file_name,transcript,language")
        print("  audio_001.wav,रुग्णाला डोकेदुखी आहे,marathi")
        print("\nRun this first to generate synthetic data:")
        print("  python scripts/generate_synthetic.py")
        sys.exit(1)

    df = pd.read_csv(meta_path)
    print(f"\n📄  Loaded metadata: {len(df)} rows")
    print(f"    Columns: {list(df.columns)}")

    # Validate required columns
    required_cols = {"file_name", "transcript", "language"}
    missing = required_cols - set(df.columns)
    if missing:
        print(f"\n❌  Missing columns in metadata.csv: {missing}")
        sys.exit(1)

    # ── Language distribution ──────────────────────────
    lang_counts = df["language"].value_counts()
    print(f"\n📊  Language distribution:")
    for lang, count in lang_counts.items():
        bar = "█" * (count // max(1, len(df) // 30))
        print(f"    {lang:12s} {count:4d}  {bar}")

    # ── Process each audio file ────────────────────────
    processed_rows = []
    skipped = {"not_found": 0, "too_short": 0, "too_long": 0,
               "bad_transcript": 0, "load_error": 0}

    print(f"\n🔊  Processing audio files...")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    audio_out_dir = PROCESSED_DIR / "audio"
    audio_out_dir.mkdir(exist_ok=True)

    for _, row in tqdm(df.iterrows(), total=len(df), desc="  Processing"):
        file_name  = str(row["file_name"]).strip()
        transcript = str(row["transcript"]).strip()
        language   = str(row.get("language", "unknown")).strip().lower()
        audio_path = data_dir / file_name

        # Validate transcript
        if not validate_transcript(transcript):
            skipped["bad_transcript"] += 1
            continue

        # Check file exists
        if not audio_path.exists():
            skipped["not_found"] += 1
            continue

        # Load + process audio
        try:
            audio, sr = load_audio(str(audio_path), target_sr=TARGET_SR)
            audio = trim_silence(audio, sr)
            audio = normalize_audio(audio)
            dur   = duration_seconds(audio, sr)
        except Exception as e:
            skipped["load_error"] += 1
            continue

        # Duration filter
        if dur < min_duration:
            skipped["too_short"] += 1
            continue
        if dur > max_duration:
            skipped["too_long"] += 1
            continue

        # Save processed audio
        out_name = f"proc_{file_name}"
        out_path = audio_out_dir / out_name
        try:
            import soundfile as sf
            sf.write(str(out_path), audio, TARGET_SR)
        except Exception:
            skipped["load_error"] += 1
            continue

        processed_rows.append({
            "file_name":   out_name,
            "audio_path":  str(out_path),
            "transcript":  clean_transcript(transcript),
            "language":    language,
            "duration_s":  round(dur, 2),
            "sample_rate": TARGET_SR,
        })

    print(f"\n✅  Processed: {len(processed_rows)} clips")
    print(f"⚠️   Skipped:")
    for reason, count in skipped.items():
        if count > 0:
            print(f"    {reason:20s}: {count}")

    if len(processed_rows) == 0:
        print("\n❌  No valid clips found. Check your data_dir and metadata.csv")
        sys.exit(1)

    # ── Train/Val/Test split ───────────────────────────
    # Stratified by language for balanced splits
    proc_df = pd.DataFrame(processed_rows)
    proc_df = proc_df.sample(frac=1, random_state=42).reset_index(drop=True)

    n = len(proc_df)
    n_train = int(n * TRAIN_SPLIT)
    n_val   = int(n * VAL_SPLIT)

    train_df = proc_df.iloc[:n_train]
    val_df   = proc_df.iloc[n_train : n_train + n_val]
    test_df  = proc_df.iloc[n_train + n_val:]

    print(f"\n📁  Dataset split:")
    print(f"    Train: {len(train_df)} clips")
    print(f"    Val:   {len(val_df)} clips")
    print(f"    Test:  {len(test_df)} clips")

    # ── Save splits as CSV ─────────────────────────────
    train_df.to_csv(PROCESSED_DIR / "train.csv", index=False)
    val_df.to_csv(PROCESSED_DIR / "val.csv",   index=False)
    test_df.to_csv(PROCESSED_DIR / "test.csv", index=False)

    # ── Save dataset stats ─────────────────────────────
    stats = {
        "total_clips":    len(proc_df),
        "train_clips":    len(train_df),
        "val_clips":      len(val_df),
        "test_clips":     len(test_df),
        "total_duration_minutes": round(proc_df["duration_s"].sum() / 60, 1),
        "avg_duration_s": round(proc_df["duration_s"].mean(), 2),
        "language_counts": proc_df["language"].value_counts().to_dict(),
        "skipped":        skipped,
    }
    with open(PROCESSED_DIR / "dataset_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    # ── Summary ────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Dataset statistics:")
    print(f"  Total duration: {stats['total_duration_minutes']} minutes")
    print(f"  Avg clip length: {stats['avg_duration_s']}s")
    print(f"\n  Files saved to: {PROCESSED_DIR}/")
    print(f"    train.csv  ({len(train_df)} rows)")
    print(f"    val.csv    ({len(val_df)} rows)")
    print(f"    test.csv   ({len(test_df)} rows)")
    print(f"    dataset_stats.json")
    print(f"\n  ✅  Step 1 complete!")
    print(f"  Next step: python src/02_augment_data.py")
    print(f"{'='*60}\n")

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare Whisper ASR training data")
    parser.add_argument("--data_dir",     type=str,   default="data/raw")
    parser.add_argument("--min_duration", type=float, default=MIN_DURATION)
    parser.add_argument("--max_duration", type=float, default=MAX_DURATION)
    args = parser.parse_args()

    process_dataset(
        data_dir     = Path(args.data_dir),
        min_duration = args.min_duration,
        max_duration = args.max_duration,
    )
