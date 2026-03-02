"""
pipeline/04_assemble_dataset.py
================================
Takes the translated JSONs from data/translated/ and assembles the
final dataset in data/final/.

Output structure per session × language × style:
  data/final/
    <id>_<lang>_<style>/
      <id>_TRANSCRIPT_<lang>_<style>.csv   ← DAIC-WOZ format transcript
      <id>_metadata.json                   ← session metadata + labels

  data/final/
    master_dataset.json     ← all sessions in one file (for model training)
    master_dataset.csv      ← flat CSV: one row per turn

TRANSCRIPT CSV columns (DAIC-WOZ compatible + extras):
  start_time | stop_time | speaker | role_label | text_en | text | style | language
"""

import csv
import json
from pathlib import Path

# ─── Configuration ────────────────────────────────────────────────────────────
TRANSLATED_DIR = Path("data/translated")
FINAL_DIR      = Path("data/final")

STYLES = ["formal_translated", "colloquial", "code_mixed"]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def save_transcript_csv(turns: list[dict], out_path: Path,
                        lang: str, style: str):
    """Save turns as a DAIC-WOZ-style tab-separated CSV."""
    fieldnames = [
        "start_time", "stop_time", "speaker",
        "role_label", "text_en", "text",
        "style", "language",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t",
                                extrasaction="ignore")
        writer.writeheader()
        for t in turns:
            writer.writerow({
                "start_time": t["start_time"],
                "stop_time":  t["stop_time"],
                "speaker":    t.get("role", ""),
                "role_label": t.get("role_label", ""),
                "text_en":    t.get("text_en", ""),
                "text":       t.get("text", ""),
                "style":      style,
                "language":   lang,
            })


def save_metadata_json(session: dict, style: str, out_path: Path):
    meta = {
        "session_id":  session["session_id"],
        "language":    session["language"],
        "style":       style,
        "phq8_score":  session.get("phq8_score"),
        "phq8_binary": session.get("phq8_binary"),
        "severity":    session.get("severity"),
        "gender":      session.get("gender"),
        "split":       session.get("split"),
        "n_turns":     len(session["styles"][style]),
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


# ─── Per-session assembly ─────────────────────────────────────────────────────

def assemble_session(translated_path: Path, out_base: Path) -> list[dict]:
    """
    Read one translated JSON, write one folder per style,
    return list of flat rows for master CSV.
    """
    with open(translated_path, encoding="utf-8") as f:
        session = json.load(f)

    sid  = session["session_id"]
    lang = session["language"]
    flat_rows = []

    for style in STYLES:
        turns = session["styles"].get(style, [])
        if not turns:
            continue

        # Folder: data/final/301_hindi_formal_translated/
        folder_name = f"{sid}_{lang}_{style}"
        folder = out_base / folder_name
        folder.mkdir(parents=True, exist_ok=True)

        # TRANSCRIPT CSV
        csv_path = folder / f"{sid}_TRANSCRIPT_{lang}_{style}.csv"
        save_transcript_csv(turns, csv_path, lang, style)

        # Metadata JSON
        meta_path = folder / f"{sid}_metadata.json"
        save_metadata_json(session, style, meta_path)

        # Collect flat rows for master CSV
        for t in turns:
            flat_rows.append({
                "session_id":  sid,
                "language":    lang,
                "style":       style,
                "turn_id":     t["turn_id"],
                "start_time":  t["start_time"],
                "stop_time":   t["stop_time"],
                "role":        t.get("role", ""),
                "role_label":  t.get("role_label", ""),
                "text_en":     t.get("text_en", ""),
                "text":        t.get("text", ""),
                "phq8_score":  session.get("phq8_score"),
                "phq8_binary": session.get("phq8_binary"),
                "severity":    session.get("severity"),
                "gender":      session.get("gender"),
                "split":       session.get("split"),
            })

    return flat_rows


# ─── Master dataset ───────────────────────────────────────────────────────────

def build_master_dataset(all_flat_rows: list[dict], out_dir: Path):
    """Save master CSV and master JSON."""
    if not all_flat_rows:
        return

    # Master CSV
    master_csv = out_dir / "master_dataset.csv"
    fields = [
        "session_id","language","style","turn_id",
        "start_time","stop_time","role","role_label",
        "text_en","text",
        "phq8_score","phq8_binary","severity","gender","split",
    ]
    with open(master_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_flat_rows)
    print(f"  ✓ master_dataset.csv  ({len(all_flat_rows):,} rows) → {master_csv}")

    # Master JSON — grouped by session
    sessions_grouped: dict[str, list] = {}
    for row in all_flat_rows:
        key = f"{row['session_id']}_{row['language']}_{row['style']}"
        sessions_grouped.setdefault(key, []).append(row)

    master_json = out_dir / "master_dataset.json"
    with open(master_json, "w", encoding="utf-8") as f:
        json.dump(sessions_grouped, f, ensure_ascii=False, indent=2)
    print(f"  ✓ master_dataset.json ({len(sessions_grouped)} session-lang-styles) → {master_json}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def assemble_all(translated_dir: Path = TRANSLATED_DIR,
                 final_dir:      Path = FINAL_DIR) -> int:
    """
    Process all translated JSONs → final dataset.
    Returns number of sessions processed.
    """
    final_dir.mkdir(parents=True, exist_ok=True)

    translated_files = sorted(translated_dir.glob("*_*.json"))
    if not translated_files:
        print(f"[ERROR] No translated JSONs in {translated_dir}. "
              "Run 03_translate.py first.")
        return 0

    print(f"  Found {len(translated_files)} translated file(s)")

    all_flat_rows = []
    for tf in translated_files:
        print(f"  Assembling {tf.name} …", end=" ", flush=True)
        rows = assemble_session(tf, final_dir)
        all_flat_rows.extend(rows)
        print(f"✓  ({len(rows)} turns across {len(STYLES)} styles)")

    build_master_dataset(all_flat_rows, final_dir)

    # Print dataset stats
    print("\n── Dataset Summary ───────────────────────────────────")
    sessions = set((r["session_id"], r["language"]) for r in all_flat_rows)
    for lang in ["hindi", "marathi"]:
        lang_sessions = [s for s in sessions if s[1] == lang]
        lang_rows     = [r for r in all_flat_rows if r["language"] == lang]
        patient_rows  = [r for r in lang_rows if r["role"] == "Patient"]
        print(f"  {lang:8s}  sessions={len(lang_sessions):>3}  "
              f"total_turns={len(lang_rows):>5}  "
              f"patient_turns={len(patient_rows):>5}")
    print("──────────────────────────────────────────────────────")
    print(f"\n✓ Final dataset → {final_dir}")
    return len(translated_files)


if __name__ == "__main__":
    assemble_all()
