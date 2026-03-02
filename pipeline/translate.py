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
import time
from pathlib import Path

# ─── Optional: deep-translator ────────────────────────────────────────────────
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False
    print("[WARN] deep-translator not installed. "
          "Only vocab-map and code-mixed styles will be generated.\n"
          "       Run: pip install deep-translator")

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
                      retries: int = 3, delay: float = 0.5) -> str:
    """Translate text using Google Translate via deep-translator."""
    if not TRANSLATOR_AVAILABLE or not text.strip():
        return text
    for attempt in range(1, retries + 1):
        try:
            translated = GoogleTranslator(
                source="auto", target=target_lang_code
            ).translate(text)
            time.sleep(delay)           # be polite to the free API
            return translated or text
        except Exception as exc:
            if attempt == retries:
                print(f"  [WARN] translation failed: {exc[:80]}")
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
    Build a code-mixed utterance:
    - Keep high-frequency English clinical/casual words as-is
    - For everything else, use the translated version
    Strategy: word-level mixing.
    """
    words_en = text_en.split()
    words_tr = text_translated.split() if text_translated else words_en

    mixed = []
    for i, word_en in enumerate(words_en):
        clean = re.sub(r"[^a-zA-Z]", "", word_en).lower()
        if clean in CODE_MIXED_KEEP:
            mixed.append(word_en)           # keep English
        elif i < len(words_tr):
            mixed.append(words_tr[i])       # use translated word
        else:
            mixed.append(word_en)

    return " ".join(mixed)


# ─── Role label ───────────────────────────────────────────────────────────────

def _role_label(role: str, lang: str) -> str:
    if role == "Doctor":
        return LANGUAGES[lang]["doctor_label"]
    return LANGUAGES[lang]["patient_label"]


# ─── Per-session translation ──────────────────────────────────────────────────

def translate_session(session: dict, lang: str, vocab: dict) -> dict:
    """
    Translate all turns of a session into `lang` using three styles.
    Returns a dict with the three style variants.
    """
    lang_code     = LANGUAGES[lang]["code"]
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

def translate_all(parsed_dir: Path  = PARSED_DIR,
                  out_dir:    Path  = TRANSLATED_DIR,
                  languages:  list  = None,
                  session_ids: list = None) -> int:
    """
    Translate all parsed sessions into all target languages.
    Returns number of files written.
    """
    if languages is None:
        languages = list(LANGUAGES.keys())   # ["hindi", "marathi"]

    out_dir.mkdir(parents=True, exist_ok=True)

    # Load vocab maps
    vocab_maps = {lang: load_vocab(lang) for lang in languages}

    # Find parsed JSONs
    parsed_files = sorted(parsed_dir.glob("*_parsed.json"))
    if not parsed_files:
        print(f"[ERROR] No parsed JSONs in {parsed_dir}. Run 02_parse_transcripts.py first.")
        return 0

    if session_ids:
        parsed_files = [p for p in parsed_files
                        if int(p.stem.split("_")[0]) in session_ids]

    print(f"  Sessions to translate: {len(parsed_files)}")
    print(f"  Target languages: {languages}")
    if not TRANSLATOR_AVAILABLE:
        print("  [INFO] Translation skipped (deep-translator not installed).")
        print("         Only vocab-map post-processing will be applied.")

    written = 0
    for pf in parsed_files:
        with open(pf, encoding="utf-8") as f:
            session = json.load(f)

        sid = session["session_id"]
        for lang in languages:
            out_path = out_dir / f"{sid}_{lang}.json"
            if out_path.exists():
                print(f"  [SKIP] {out_path.name} already exists")
                continue

            print(f"  Translating session {sid} → {lang} …", end=" ", flush=True)
            result = translate_session(session, lang, vocab_maps[lang])

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print("✓")
            written += 1

    print(f"\n✓ {written} translated file(s) → {out_dir}")
    return written


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids",  nargs="+", type=int, default=None,
                        help="Specific session IDs to translate")
    parser.add_argument("--lang", nargs="+", default=None,
                        choices=["hindi", "marathi"],
                        help="Languages (default: both)")
    args = parser.parse_args()
    translate_all(session_ids=args.ids, languages=args.lang)
