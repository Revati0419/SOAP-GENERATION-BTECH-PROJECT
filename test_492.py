#!/usr/bin/env python3
"""
Test SOAP generation for two variants of session 492:

  492_marathi.json       → Phase 1  (bilingual: text_en + text)
  492_marathi_only.json  → Phase 2  (Marathi-only: text field only)

Both results are printed + saved to outputs/soap_notes/.
"""

import sys, json, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# ── Load models ONCE, share across both tests ─────────────────────────────────
print("📦 Loading models...\n")
from src.translation import get_translator
from src.ner         import get_ner_model
from src.generation  import MultilingualSOAPGenerator

translator = get_translator(model_type="nllb", device="cpu")
translator.load_model()
print("   ✅ NLLB-200 loaded")

ner = get_ner_model(model_type="rule_based", device="cpu")
print("   ✅ NER (rule-based) loaded\n")

config = {"llm_model": "gemma2:2b", "use_ner": True, "use_rag": False, "device": "cpu"}
gen = MultilingualSOAPGenerator(config=config)
gen._translator        = translator
gen._translator_loaded = True
gen._ner               = ner
gen._ner_loaded        = True

# ── Helpers ───────────────────────────────────────────────────────────────────
SEP  = "═" * 65
SEP2 = "─" * 65

def print_soap(label, soap, lang_label, lang_hint=""):
    print(f"\n  {'🇬🇧' if 'ENGLISH' in lang_label else '🇮🇳'}  {lang_label}  {lang_hint}")
    print(f"  {SEP2}")
    for title, text in [
        ("SUBJECTIVE", soap.subjective),
        ("OBJECTIVE",  soap.objective),
        ("ASSESSMENT", soap.assessment),
        ("PLAN",       soap.plan),
    ]:
        print(f"\n  ┌─ {title}")
        for line in (text or "— (empty)").strip().splitlines():
            print(f"  │  {line}")
        print(f"  └{'─'*50}")

def run_test(json_file, label):
    path    = ROOT / "data" / "dialect_marathi" / json_file
    print(f"\n{SEP}")
    print(f"  TEST: {label}")
    print(f"  File: {json_file}")
    print(SEP)

    session = json.load(open(path, encoding="utf-8"))
    turns   = list(session["dialects"].values())[0]
    has_en  = any(t.get("text_en", "").strip() for t in turns[:5])

    print(f"  session_id : {session['session_id']}")
    print(f"  phq8_score : {session['phq8_score']}")
    print(f"  severity   : {session['severity']}")
    print(f"  gender     : {session['gender']}")
    print(f"  turns      : {len(turns)}")
    print(f"  text_en    : {'✅ present (Phase 1)' if has_en else '❌ absent  (Phase 2 — Marathi-only)'}\n")

    t0      = time.time()
    result  = gen.generate_from_session(session, target_lang="marathi")
    elapsed = time.time() - t0

    print(f"\n{SEP}")
    print(f"  SOAP NOTE — Session {session['session_id']}")
    print(f"  Pipeline  : Phase {'1 (text_en → Gemma)' if has_en else '2 (Marathi → NLLB → Gemma)'}")
    print(f"  Time      : {elapsed:.1f}s")
    print(SEP)

    print_soap(label, result.english,         "ENGLISH SOAP NOTE")
    print_soap(label, result.target_language, "MARATHI SOAP NOTE",
               "(व्यक्तिनिष्ठ / वस्तुनिष्ठ / मूल्यांकन / योजना)")

    # Save to outputs/soap_notes/
    out_dir  = ROOT / "outputs" / "soap_notes"
    out_dir.mkdir(parents=True, exist_ok=True)
    sid      = str(session["session_id"]).replace(".", "_")
    out_file = out_dir / f"{sid}_soap_note.json"

    raw = result.to_dict()
    raw.update({
        "session_id":        session["session_id"],
        "phq8_score":        session["phq8_score"],
        "severity":          session["severity"],
        "gender":            session["gender"],
        "processing_time_s": round(elapsed, 2),
        "phase":             "1_bilingual" if has_en else "2_marathi_only",
    })
    json.dump(raw, open(out_file, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n  💾 Saved → {out_file.relative_to(ROOT)}")
    print(f"  ✅ {label} done in {elapsed:.1f}s\n")

# ── Run both tests ─────────────────────────────────────────────────────────────
run_test("492_marathi.json",      "492   — PHASE 1  (bilingual  text_en + text)")
run_test("492_marathi_only.json", "492.1 — PHASE 2  (Marathi-only  text only)")

print(f"\n{SEP}")
print("  ALL TESTS DONE")
print(f"{SEP}\n")
