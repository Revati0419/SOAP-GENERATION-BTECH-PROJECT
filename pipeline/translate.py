"""
pipeline/03_translate.py
========================
Translates English DAIC-WOZ conversations into Hindi and Marathi
using three style layers per session:

  1. formal_translated  – machine translation via deep-translator
                          (Google Translate, free, no API key)
  2. colloquial         – vocab-map substitution: replaces clinical
                          English keywords with colloquial Indic terms
                          BEFORE translating, giving more natural output
  3. code_mixed         – Hinglish / Marathi-English: keeps some English
                          words (clinical terms, common nouns) and wraps
                          the rest in the target language — mirrors how
                          educated Indian patients actually speak

All three are stored so the final dataset has linguistic variety.

Also performs role conversion:
  Ellie (virtual interviewer) → "डॉक्टर" / "डॉक्टर" in the conversation

Output: data/translated/<session_id>_<lang>_<style>.json
"""

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from tqdm import tqdm

# ─── Configuration ────────────────────────────────────────────────────────────
PARSED_DIR     = Path("data/parsed")
TRANSLATED_DIR = Path("data/translated")
VOCAB_DIR      = Path("vocab")

LANGUAGES = {
    "hindi":   {"code": "hi", "vocab_file": "hindi_clinical_vocab.json",
                "doctor_label": "डॉक्टर", "patient_label": "मरीज़"},
    "marathi": {"code": "mr", "vocab_file": "marathi_clinical_vocab.json",
                "doctor_label": "डॉक्टर", "patient_label": "रुग्ण"},
}

# English words we keep AS-IS in code-mixed style (not translated)
CODE_MIXED_KEEP = {
    "depression", "anxiety", "ptsd", "stress", "mood", "sleep", "memory",
    "focus", "panic", "trauma", "therapy", "doctor", "medication", "hospital",
    "ok", "okay", "yes", "no", "hi", "bye", "hello", "thanks", "sorry",
    "feeling", "feel", "mind", "brain", "energy", "tired", "sad",
}

# English → English substitution that nudges translation toward colloquial
# (applied before translating for the "colloquial" style)
COLLOQUIAL_SUBSTITUTION_EN = {
    r"\bdepression\b":        "sadness and hopelessness",
    r"\banxiety\b":           "worry and fear",
    r"\bptsd\b":              "trauma from a past event",
    r"\bsuicidal\b":          "not wanting to live",
    r"\bself.harm\b":         "hurting myself",
    r"\binsomnia\b":          "not being able to sleep",
    r"\banhedonia\b":         "not enjoying anything",
    r"\bfatigue\b":           "extreme tiredness",
    r"\birritab\w+\b":        "getting angry easily",
    r"\bconcentrat\w+\b":     "unable to focus",
    r"\bhopeless\w*\b":       "feeling that nothing will get better",
    r"\bworthless\w*\b":      "feeling useless",
    r"\bdiagnos\w+\b":        "identified as having",
    r"\btherapy\b":           "treatment and counseling",
    r"\bmedication\b":        "medicine",
    r"\bsymptom\w*\b":        "problem",
    r"\bpsychiatri\w+\b":     "mental health doctor",
    r"\bpsychologi\w+\b":     "mental health counselor",
}


# ─── Load vocab maps ──────────────────────────────────────────────────────────

def load_vocab(lang: str) -> dict:
    fname = LANGUAGES[lang]["vocab_file"]
    path  = VOCAB_DIR / fname
    if not path.exists():
        print(f"  [WARN] vocab file not found: {path}")
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ─── Translation helpers ──────────────────────────────────────────────────────

def _google_translate(text: str, target_lang_code: str,
                      retries: int = 3, delay: float = 0.2) -> str:
    """Translate text using the public translate.googleapis.com HTTP endpoint.
    
    No API key required. Direct HTTP calls — simple and reliable.
    """
    if not text.strip():
        return text

    for attempt in range(1, retries + 1):
        try:
            params = {
                'client': 'gtx',
                'sl': 'auto',
                'tl': target_lang_code,
                'dt': 't',
                'q': text,
            }
            resp = requests.get(
                'https://translate.googleapis.com/translate_a/single',
                params=params,
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                # data[0] is list of segments [ [translated, original, ...], ... ]
                translated = ''.join(seg[0] for seg in data[0] if seg and seg[0])
                time.sleep(delay)
                return translated or text
            else:
                if attempt == retries:
                    print(f"  [WARN] HTTP API returned status {resp.status_code}")
                    return text
                time.sleep(2 ** attempt)
        except Exception as exc:
            if attempt == retries:
                print(f"  [WARN] HTTP translate failed: {str(exc)[:100]}")
                return text
            time.sleep(2 ** attempt)
    return text


def _apply_colloquial_substitution(text: str) -> str:
    """Replace clinical English words with plain English before translating."""
    t = text.lower()
    for pattern, replacement in COLLOQUIAL_SUBSTITUTION_EN.items():
        t = re.sub(pattern, replacement, t, flags=re.IGNORECASE)
    return t


def _apply_vocab_map(text: str, vocab: dict) -> str:
    """
    After translation, scan the translated text for any remaining
    English clinical terms and replace with colloquial Indic terms.
    Also appends slang phrase hints where relevant.
    """
    text_lower = text.lower()
    result = text

    for key, variants in vocab.items():
        if key.startswith("_"):
            continue
        # If English key still appears in translated text, swap it
        if re.search(r'\b' + re.escape(key) + r'\b', text_lower):
            colloquial = variants.get("colloquial") or variants.get("formal", "")
            if colloquial:
                result = re.sub(
                    r'\b' + re.escape(key) + r'\b',
                    colloquial, result, flags=re.IGNORECASE
                )

    return result


def _make_code_mixed(text_en: str, text_translated: str, lang: str) -> str:
    """
    Build a code-mixed utterance that mirrors how educated Indian patients speak:
    - Clinical / common English words stay in English
    - The rest of the sentence uses the translated Indic version
    Strategy: sentence-level mixing — keep English anchor words,
    use the full translated sentence as the base, then re-insert
    the English anchor words at their natural positions.
    This avoids the word-count mismatch problem of word-level mixing.
    """
    words_en = text_en.split()

    # Identify which English words to keep
    keep_words = []
    for word_en in words_en:
        clean = re.sub(r"[^a-zA-Z]", "", word_en).lower()
        if clean in CODE_MIXED_KEEP:
            keep_words.append(word_en)

    # If no anchor words, just return translation
    if not keep_words:
        return text_translated if text_translated else text_en

    # If ALL words are anchor words (very short utterance), keep English
    if len(keep_words) == len(words_en):
        return text_en

    # Use the translated sentence as the base, but append English terms
    # that were present in the original — natural code-mixed pattern
    base = text_translated if text_translated else text_en
    appended = " ".join(keep_words)

    # Pattern: translated base + English clinical terms appended naturally
    # e.g.  "मुझे बहुत उदास और थका हुआ feel होता है"
    if appended:
        return f"{base} ({appended})" if len(keep_words) <= 2 else base

    return base


# ─── Role label ───────────────────────────────────────────────────────────────

def _role_label(role: str, lang: str) -> str:
    if role == "Doctor":
        return LANGUAGES[lang]["doctor_label"]
    return LANGUAGES[lang]["patient_label"]


# ─── Per-session translation ──────────────────────────────────────────────────

def translate_session(session: dict, lang: str, vocab: dict) -> dict:
    """
    Translate all turns of a session into `lang` using three styles.
    Thread-safe: uses a per-thread Translator instance.
    Returns a dict with the three style variants.
    """
    lang_code                   = LANGUAGES[lang]["code"]
    translated_turns_formal     = []
    translated_turns_colloquial = []
    translated_turns_code_mixed = []

    for turn in session["turns"]:
        text_en = turn["text_en"]

        # ── Style 1: Formal translated ──────────────────────────────────────
        text_formal = _google_translate(text_en, lang_code)
        text_formal = _apply_vocab_map(text_formal, vocab)

        # ── Style 2: Colloquial translated ──────────────────────────────────
        text_en_simplified = _apply_colloquial_substitution(text_en)
        text_colloquial    = _google_translate(text_en_simplified, lang_code)
        text_colloquial    = _apply_vocab_map(text_colloquial, vocab)

        # ── Style 3: Code-mixed ─────────────────────────────────────────────
        text_code_mixed = _make_code_mixed(text_en, text_formal, lang)

        base = {
            "turn_id":      turn["turn_id"],
            "start_time":   turn["start_time"],
            "stop_time":    turn["stop_time"],
            "role":         turn["role"],
            "role_label":   _role_label(turn["role"], lang),
            "text_en":      text_en,
        }

        translated_turns_formal.append(    {**base, "text": text_formal})
        translated_turns_colloquial.append({**base, "text": text_colloquial})
        translated_turns_code_mixed.append({**base, "text": text_code_mixed})

    return {
        "session_id":    session["session_id"],
        "language":      lang,
        "phq8_score":    session.get("phq8_score"),
        "phq8_binary":   session.get("phq8_binary"),
        "severity":      session.get("severity"),
        "gender":        session.get("gender"),
        "split":         session.get("split"),
        "styles": {
            "formal_translated": translated_turns_formal,
            "colloquial":        translated_turns_colloquial,
            "code_mixed":        translated_turns_code_mixed,
        },
    }


# ─── Process all sessions ─────────────────────────────────────────────────────

def _translate_one(args: tuple) -> tuple[int, str, str]:
    """
    Worker function for one (session_file, lang) job.
    Returns (session_id, lang, "ok" | "skip" | "error:<msg>").
    """
    pf, lang, vocab, out_dir = args
    with open(pf, encoding="utf-8") as f:
        session = json.load(f)
    sid = session["session_id"]
    out_path = out_dir / f"{sid}_{lang}.json"

    if out_path.exists():
        return sid, lang, "skip"

    try:
        result = translate_session(session, lang, vocab)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return sid, lang, "ok"
    except Exception as exc:
        return sid, lang, f"error:{str(exc)[:120]}"


def translate_all(parsed_dir:  Path = PARSED_DIR,
                  out_dir:     Path = TRANSLATED_DIR,
                  languages:   list = None,
                  session_ids: list = None,
                  n_workers:   int  = 8) -> int:
    """
    Translate all parsed sessions into all target languages in parallel.
    Uses ThreadPoolExecutor — each thread gets its own Translator instance.
    Returns number of new files written.
    """
    if languages is None:
        languages = list(LANGUAGES.keys())

    out_dir.mkdir(parents=True, exist_ok=True)
    vocab_maps = {lang: load_vocab(lang) for lang in languages}

    parsed_files = sorted(parsed_dir.glob("*_parsed.json"))
    if not parsed_files:
        print(f"[ERROR] No parsed JSONs in {parsed_dir}.")
        return 0

    if session_ids:
        parsed_files = [p for p in parsed_files
                        if int(p.stem.split("_")[0]) in session_ids]

    # Build full job list
    jobs = [
        (pf, lang, vocab_maps[lang], out_dir)
        for pf in parsed_files
        for lang in languages
    ]
    total     = len(jobs)
    done_pre  = sum(1 for (pf, lang, _, od) in jobs
                    if (od / f"{int(pf.stem.split('_')[0])}_{lang}.json").exists())
    remaining = total - done_pre

    print(f"\n{'─'*60}")
    print(f"  Sessions  : {len(parsed_files)}")
    print(f"  Languages : {', '.join(languages)}")
    print(f"  Workers   : {n_workers}  (parallel sessions)")
    print(f"  Jobs      : {total}  |  Already done: {done_pre}  |  Left: {remaining}")
    print(f"{'─'*60}\n")

    if remaining == 0:
        print("  ✅ All sessions already translated. Nothing to do.")
        return 0

    written = 0
    skipped = 0
    errors  = 0

    bar = tqdm(total=remaining, unit="file", desc="Translating",
               dynamic_ncols=True, file=sys.stderr,
               bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} "
                          "[{elapsed}<{remaining}, {rate_fmt}]")

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futures = {pool.submit(_translate_one, job): job for job in jobs}
        for fut in as_completed(futures):
            sid, lang, status = fut.result()
            if status == "skip":
                skipped += 1
            elif status == "ok":
                written += 1
                bar.update(1)
                bar.set_postfix(done=written, err=errors, refresh=True)
            else:
                errors += 1
                bar.update(1)
                tqdm.write(f"  [ERR] {sid}/{lang}: {status[6:]}", file=sys.stderr)

    bar.close()
    print(f"\n{'─'*60}")
    print(f"  ✅ Done.  Written: {written}  |  Skipped: {skipped}  |  Errors: {errors}")
    print(f"  📁 Output: {out_dir}")
    print(f"{'─'*60}\n")
    return written


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids",     nargs="+", type=int, default=None,
                        help="Specific session IDs to translate")
    parser.add_argument("--lang",    nargs="+", default=None,
                        choices=["hindi", "marathi"],
                        help="Languages (default: both)")
    parser.add_argument("--workers", type=int, default=8,
                        help="Parallel worker threads (default: 8)")
    args = parser.parse_args()
    translate_all(session_ids=args.ids, languages=args.lang, n_workers=args.workers)
