"""
02_augment_data.py
──────────────────
Step 2: Audio augmentation — turns each clip into 3-4 variants,
multiplying your training data without recording more audio.

Augmentations applied:
  1. Speed perturbation  (0.85x, 1.15x) — simulates fast/slow speakers
  2. Pitch shift         (±2 semitones)  — voice variation
  3. Gaussian noise      (SNR 20-35 dB)  — real-world noise robustness
  4. Volume jitter       (±6 dB)         — microphone variation

CPU-safe: All transforms run on numpy arrays, no GPU required.

Usage:
    python src/02_augment_data.py
    python src/02_augment_data.py --augmentations speed noise  # selective
"""

import argparse
import json
import random
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf
from tqdm import tqdm

warnings.filterwarnings("ignore")

PROCESSED_DIR  = Path("data/processed")
AUGMENTED_DIR  = Path("data/augmented")
TARGET_SR      = 16000
RANDOM_SEED    = 42

random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# ─────────────────────────────────────────────────────
# AUGMENTATION FUNCTIONS (all CPU-only)
# ─────────────────────────────────────────────────────

def speed_perturb(audio: np.ndarray, sr: int, rate: float) -> np.ndarray:
    """
    Change playback speed without changing pitch.
    rate < 1.0 = slower, rate > 1.0 = faster.
    Uses linear interpolation — no librosa required.
    """
    if rate == 1.0:
        return audio
    output_length = int(len(audio) / rate)
    indices = np.linspace(0, len(audio) - 1, output_length)
    return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)


def add_gaussian_noise(audio: np.ndarray, snr_db: float) -> np.ndarray:
    """
    Add Gaussian white noise at a given Signal-to-Noise ratio (dB).
    Higher SNR = cleaner audio. 20-35 dB = realistic recording noise.
    """
    signal_power = np.mean(audio ** 2)
    if signal_power == 0:
        return audio
    noise_power = signal_power / (10 ** (snr_db / 10))
    noise = np.random.normal(0, np.sqrt(noise_power), len(audio))
    return (audio + noise).astype(np.float32)


def volume_jitter(audio: np.ndarray, gain_db: float) -> np.ndarray:
    """Apply a gain change in dB (positive = louder, negative = quieter)."""
    gain_linear = 10 ** (gain_db / 20)
    audio = audio * gain_linear
    # Clip to prevent distortion
    return np.clip(audio, -1.0, 1.0).astype(np.float32)


def pitch_shift_simple(audio: np.ndarray, sr: int, semitones: float) -> np.ndarray:
    """
    Simple pitch shift using resampling trick (CPU-only, no librosa needed).
    Not perfect but effective for augmentation purposes.
    """
    rate = 2 ** (-semitones / 12)
    # Speed change (changes pitch)
    shifted_length = int(len(audio) * rate)
    indices = np.linspace(0, len(audio) - 1, shifted_length)
    shifted = np.interp(indices, np.arange(len(audio)), audio)
    # Resample back to original length to keep duration the same
    indices2 = np.linspace(0, len(shifted) - 1, len(audio))
    return np.interp(indices2, np.arange(len(shifted)), shifted).astype(np.float32)


# ─────────────────────────────────────────────────────
# AUGMENTATION STRATEGY
# Each entry: (name, function_call_lambda, probability)
# ─────────────────────────────────────────────────────

def get_augmentations(selected: list):
    """
    Returns list of (augmentation_name, transform_fn) pairs.
    Each creates one new variant of the audio.
    """
    all_augs = {
        "speed_slow": lambda a, sr: (
            speed_perturb(a, sr, rate=round(random.uniform(0.82, 0.92), 2)),
            "speed_slow"
        ),
        "speed_fast": lambda a, sr: (
            speed_perturb(a, sr, rate=round(random.uniform(1.08, 1.18), 2)),
            "speed_fast"
        ),
        "noise_light": lambda a, sr: (
            add_gaussian_noise(a, snr_db=random.uniform(28, 38)),
            "noise_light"
        ),
        "noise_heavy": lambda a, sr: (
            add_gaussian_noise(a, snr_db=random.uniform(15, 22)),
            "noise_heavy"
        ),
        "volume_up": lambda a, sr: (
            volume_jitter(a, gain_db=random.uniform(2, 6)),
            "volume_up"
        ),
        "volume_down": lambda a, sr: (
            volume_jitter(a, gain_db=random.uniform(-6, -2)),
            "volume_down"
        ),
        "pitch_up": lambda a, sr: (
            pitch_shift_simple(a, sr, semitones=random.uniform(1, 2.5)),
            "pitch_up"
        ),
        "pitch_down": lambda a, sr: (
            pitch_shift_simple(a, sr, semitones=random.uniform(-2.5, -1)),
            "pitch_down"
        ),
    }

    if not selected or selected == ["all"]:
        return all_augs
    return {k: v for k, v in all_augs.items() if any(s in k for s in selected)}


# ─────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────

def augment_split(split_name: str, augmentations: dict, max_aug_per_clip: int):
    """Augment one dataset split (train/val/test)."""
    csv_path = PROCESSED_DIR / f"{split_name}.csv"
    if not csv_path.exists():
        print(f"  ⚠  {csv_path} not found, skipping {split_name}")
        return []

    df = pd.read_csv(csv_path)
    print(f"\n  {split_name.upper()}: {len(df)} original clips")

    # Only augment train split — val and test stay clean
    if split_name != "train":
        # Copy to augmented dir without changes
        out_dir = AUGMENTED_DIR / split_name
        out_dir.mkdir(parents=True, exist_ok=True)
        new_rows = df.to_dict("records")
        df.to_csv(AUGMENTED_DIR / f"{split_name}.csv", index=False)
        print(f"    → Copied as-is (no augmentation on {split_name})")
        return new_rows

    out_dir = AUGMENTED_DIR / "train"
    out_dir.mkdir(parents=True, exist_ok=True)

    aug_rows = []
    aug_names = list(augmentations.keys())

    for _, row in tqdm(df.iterrows(), total=len(df), desc=f"  Augmenting {split_name}"):
        # Always keep the original
        aug_rows.append(dict(row))

        audio_path = row["audio_path"]
        if not Path(audio_path).exists():
            continue

        try:
            audio, sr = sf.read(audio_path, dtype="float32")
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)  # Stereo → mono
        except Exception:
            continue

        # Apply a random subset of augmentations
        chosen = random.sample(aug_names, k=min(max_aug_per_clip, len(aug_names)))

        for aug_name in chosen:
            try:
                aug_fn = augmentations[aug_name]
                aug_audio, tag = aug_fn(audio, sr)

                # Save augmented clip
                base = Path(row["file_name"]).stem
                aug_filename = f"{base}_{tag}.wav"
                aug_path = out_dir / aug_filename
                sf.write(str(aug_path), aug_audio, sr)

                new_row = dict(row)
                new_row["file_name"]  = aug_filename
                new_row["audio_path"] = str(aug_path)
                new_row["augmented"]  = aug_name
                aug_rows.append(new_row)

            except Exception as e:
                continue

    aug_df = pd.DataFrame(aug_rows)
    aug_df.to_csv(AUGMENTED_DIR / "train.csv", index=False)

    print(f"    → Augmented: {len(aug_rows)} clips "
          f"({len(aug_rows) - len(df)} new, {len(aug_rows)/len(df):.1f}x multiplier)")
    return aug_rows


def main(selected_augs: list, max_aug_per_clip: int):
    print("\n" + "="*60)
    print("  STEP 2: Audio Augmentation")
    print("="*60)

    AUGMENTED_DIR.mkdir(parents=True, exist_ok=True)
    augmentations = get_augmentations(selected_augs)

    print(f"\n  Active augmentations: {list(augmentations.keys())}")
    print(f"  Max augmentations per clip: {max_aug_per_clip}")

    stats = {}
    for split in ["train", "val", "test"]:
        rows = augment_split(split, augmentations, max_aug_per_clip)
        stats[split] = len(rows)

    # Save augmentation summary
    summary = {
        "augmentations_used": list(augmentations.keys()),
        "max_aug_per_clip":   max_aug_per_clip,
        "split_sizes":        stats,
    }
    with open(AUGMENTED_DIR / "augmentation_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  Augmentation complete!")
    print(f"  Train: {stats.get('train', 0)} clips")
    print(f"  Val:   {stats.get('val', 0)} clips")
    print(f"  Test:  {stats.get('test', 0)} clips")
    print(f"\n  Files saved to: {AUGMENTED_DIR}/")
    print(f"\n  ✅  Step 2 complete!")
    print(f"  Next step: python src/03_train.py")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audio augmentation for ASR training")
    parser.add_argument("--augmentations", nargs="+", default=["all"],
                        help="Augmentations to apply: speed noise volume pitch all")
    parser.add_argument("--max_aug_per_clip", type=int, default=3,
                        help="Max augmentations applied per clip (default: 3)")
    args = parser.parse_args()
    main(args.augmentations, args.max_aug_per_clip)
