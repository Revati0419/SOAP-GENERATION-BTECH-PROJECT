"""
pipeline/02_parse_transcripts.py
=================================
Reads all _TRANSCRIPT.csv files from data/raw/ and the label CSVs
from data/labels/, then produces a clean parsed dataset:

  data/parsed/
    <id>_parsed.json   ← one file per session
    sessions_index.csv ← master index of all sessions with labels

Parsed JSON structure (mirrors DAIC-WOZ fields, adapted for doctor-patient):
{
  "session_id": 301,
  "phq8_score": 5,
  "phq8_binary": 0,         ← 0=non-depressed, 1=depressed
  "severity": "minimal",
  "gender": 1,              ← from label CSV (1=male, 2=female)
  "turns": [
    {
      "turn_id": 0,
      "start_time": 29.428,
      "stop_time": 35.888,
      "speaker": "Ellie",           ← original DAIC speaker
      "role": "Doctor",             ← mapped role for our dataset
      "text_en": "hi i'm ellie ...",
      "word_count": 18,
      "duration_sec": 6.46
    },
    ...
  ],
  "patient_turns": [...],   ← convenience: Participant turns only
  "n_turns": 42,
  "n_patient_turns": 21,
  "session_duration_sec": 803.8
}
"""

import csv
import json
from pathlib import Path

# ─── Configuration ────────────────────────────────────────────────────────────
RAW_DIR    = Path("data/raw")
LABEL_DIR  = Path("data/labels")
PARSED_DIR = Path("data/parsed")

LABEL_FILES = [
    "train_split_Depression_AVEC2017.csv",
    "dev_split_Depression_AVEC2017.csv",
    "full_test_split.csv",
]

# Severity bands based on PHQ-8 score
def phq8_severity(score: int) -> str:
    if score is None:
        return "unknown"
    if score <= 4:
        return "minimal"
    if score <= 9:
        return "mild"
    if score <= 14:
        return "moderate"
    if score <= 19:
        return "moderately_severe"
    return "severe"


# ─── Step 1: Load labels ──────────────────────────────────────────────────────

def load_labels() -> dict[int, dict]:
    """
    Read all three split CSVs and return a dict:
      session_id (int) → {phq8_score, phq8_binary, gender, split}
    """
    labels: dict[int, dict] = {}

    split_name_map = {
        "train_split_Depression_AVEC2017.csv": "train",
        "dev_split_Depression_AVEC2017.csv":   "dev",
        "full_test_split.csv":                 "test",
    }

    for fname in LABEL_FILES:
        fpath = LABEL_DIR / fname
        if not fpath.exists():
            print(f"  [WARN] label file not found: {fpath}")
            continue

        split = split_name_map.get(fname, "unknown")
        with open(fpath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    sid = int(row.get("Participant_ID", 0))
                except ValueError:
                    continue

                # PHQ8_Score is the continuous score; PHQ8_Binary is 0/1
                phq_score = row.get("PHQ8_Score") or row.get("PHQ_Score") or ""
                try:
                    phq_int = int(float(phq_score))
                except (ValueError, TypeError):
                    phq_int = None

                binary_raw = row.get("PHQ8_Binary", "")
                try:
                    binary = int(binary_raw)
                except (ValueError, TypeError):
                    binary = None

                gender_raw = row.get("Gender", "")
                try:
                    gender = int(gender_raw)
                except (ValueError, TypeError):
                    gender = None

                labels[sid] = {
                    "phq8_score":  phq_int,
                    "phq8_binary": binary,
                    "severity":    phq8_severity(phq_int),
                    "gender":      gender,
                    "split":       split,
                }

    print(f"  Labels loaded: {len(labels)} sessions")
    return labels


# ─── Step 2: Parse one transcript ─────────────────────────────────────────────

def parse_transcript(csv_path: Path) -> list[dict]:
    """
    Read a _TRANSCRIPT.csv (tab-separated) and return list of turn dicts.
    Handles both tab-separated (DAIC-WOZ style) and comma-separated.
    """
    turns = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        # Detect delimiter
        sample = f.read(512)
        f.seek(0)
        delim = "\t" if "\t" in sample else ","
        reader = csv.DictReader(f, delimiter=delim)

        for i, row in enumerate(reader):
            try:
                start = float(row.get("start_time", 0))
                stop  = float(row.get("stop_time",  0))
            except (ValueError, TypeError):
                start, stop = 0.0, 0.0

            speaker_raw = (row.get("speaker") or "").strip()
            text        = (row.get("value")   or "").strip()

            # Map DAIC-WOZ speaker names to our roles
            if speaker_raw.lower() in ("ellie", "doctor", "interviewer"):
                role = "Doctor"
            else:
                role = "Patient"

            turns.append({
                "turn_id":      i,
                "start_time":   round(start, 3),
                "stop_time":    round(stop,  3),
                "speaker":      speaker_raw,
                "role":         role,
                "text_en":      text,
                "word_count":   len(text.split()),
                "duration_sec": round(max(0.0, stop - start), 3),
            })

    return turns


# ─── Step 3: Build session dict ───────────────────────────────────────────────

def build_session(session_id: int, turns: list[dict], label: dict | None) -> dict:
    patient_turns = [t for t in turns if t["role"] == "Patient"]

    # Session duration = last stop_time
    duration = turns[-1]["stop_time"] if turns else 0.0

    return {
        "session_id":         session_id,
        "phq8_score":         label["phq8_score"]  if label else None,
        "phq8_binary":        label["phq8_binary"] if label else None,
        "severity":           label["severity"]    if label else "unknown",
        "gender":             label["gender"]      if label else None,
        "split":              label["split"]       if label else "unknown",
        "n_turns":            len(turns),
        "n_patient_turns":    len(patient_turns),
        "session_duration_sec": round(duration, 3),
        "turns":              turns,
        "patient_turns":      patient_turns,
    }


# ─── Step 4: Process all sessions ─────────────────────────────────────────────

def parse_all(raw_dir: Path = RAW_DIR,
              label_dir: Path = LABEL_DIR,
              parsed_dir: Path = PARSED_DIR) -> list[dict]:
    """
    Walk raw_dir for all *_TRANSCRIPT.csv files, parse them,
    attach labels, save JSON + summary CSV.
    Returns list of session summaries (without turns — for index CSV).
    """
    parsed_dir.mkdir(parents=True, exist_ok=True)

    labels = load_labels()

    # Collect all transcript files
    transcript_files = sorted(raw_dir.glob("**/*_TRANSCRIPT.csv"))
    if not transcript_files:
        print(f"[ERROR] No *_TRANSCRIPT.csv found in {raw_dir}")
        print("        Run pipeline/01_download.py first.")
        return []

    print(f"  Found {len(transcript_files)} transcript(s)")

    summaries = []
    for csv_path in transcript_files:
        # Extract session ID from filename like "301_TRANSCRIPT.csv"
        stem = csv_path.stem                   # e.g. "301_TRANSCRIPT"
        parts = stem.split("_")
        try:
            sid = int(parts[0])
        except ValueError:
            print(f"  [SKIP] Cannot parse session ID from {csv_path.name}")
            continue

        label = labels.get(sid)
        turns = parse_transcript(csv_path)
        session = build_session(sid, turns, label)

        # Save per-session JSON
        out_path = parsed_dir / f"{sid}_parsed.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)

        # Collect summary row (no turns)
        summaries.append({
            "session_id":           session["session_id"],
            "phq8_score":           session["phq8_score"],
            "phq8_binary":          session["phq8_binary"],
            "severity":             session["severity"],
            "gender":               session["gender"],
            "split":                session["split"],
            "n_turns":              session["n_turns"],
            "n_patient_turns":      session["n_patient_turns"],
            "session_duration_sec": session["session_duration_sec"],
        })

        score_str = str(session["phq8_score"]) if session["phq8_score"] is not None else "?"
        print(f"  [{sid}] turns={session['n_turns']:>3}  patient_turns={session['n_patient_turns']:>3}"
              f"  PHQ-8={score_str:>2}  severity={session['severity']}")

    # Save summary CSV
    if summaries:
        index_path = parsed_dir.parent / "sessions_index.csv"
        fields = ["session_id","phq8_score","phq8_binary","severity",
                  "gender","split","n_turns","n_patient_turns","session_duration_sec"]
        with open(index_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(summaries)
        print(f"\n  ✓ sessions_index.csv → {index_path}")

    print(f"\n✓ {len(summaries)} session(s) parsed → {parsed_dir}")
    return summaries


if __name__ == "__main__":
    parse_all()
