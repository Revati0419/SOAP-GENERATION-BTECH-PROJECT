"""
test_soap_v2.py
================
Quick demo: load session 300 and generate a Marathi SOAP note.
Run from your project root:
    python test_soap_v2.py
"""

import json
from soap_v2 import get_marathi_soap_generator

# ── Load session data ──────────────────────────────────────────────────────────
with open("data/dialect_marathi/300_marathi.json", encoding="utf-8") as f:
    session = json.load(f)

# ── Generate ───────────────────────────────────────────────────────────────────
gen  = get_marathi_soap_generator(model="gemma2:2b")
note = gen.generate_from_session(session, dialect="standard_pune")

# ── Print structured output ────────────────────────────────────────────────────
print("=" * 60)
print("  मराठी SOAP नोट (संरचित / Parametric)")
print("=" * 60)

S = note.subjective
O = note.objective
A = note.assessment
P = note.plan

print("\n── SUBJECTIVE ──────────────────────────────────────────────")
print(f"मुख्य तक्रार:\n{S.chief_complaint}")
print(f"\nसध्याच्या आजाराचा इतिहास:\n{S.hpi}")
print(f"\nआघाताचा इतिहास:\n{S.trauma_history}")
print(f"\nमनोसामाजिक इतिहास:\n{S.psychosocial_history}")
print(f"\nकार्यक्षम स्थिती:\n{S.functional_status}")

print("\n── OBJECTIVE ───────────────────────────────────────────────")
print(f"वैद्यकीय इतिहास:\n{O.medical_history}")
print(f"\nपूर्व मनोरुग्ण इतिहास:\n{O.past_psych_history}")
print(f"\nजैविक निरीक्षणे:\n{O.biological_obs}")
print(f"\nमानसिक स्थिती तपासणी:\n{O.mental_status_exam}")
print(f"\nPHQ-8 गुण:\n{O.phq8_score}")

print("\n── ASSESSMENT ──────────────────────────────────────────────")
print(f"निदान:\n{A.diagnostic_formulation}")
print(f"\nजोखीम मूल्यांकन:\n{A.risk_formulation}")
print(f"\nयोगदान देणारे घटक:\n{A.contributing_factors}")

print("\n── PLAN ────────────────────────────────────────────────────")
print(f"उपचार आणि सुरक्षा योजना:\n{P.treatment_safety_plan}")
print(f"\nमानसोपचार योजना:\n{P.therapy_plan}")
print(f"\nऔषधोपचार:\n{P.medication}")
print(f"\nपाठपुरावा:\n{P.followup}")

# ── Also show as dict (for API / frontend use) ─────────────────────────────────
print("\n── JSON (flat, API-compatible) ─────────────────────────────")
import pprint
pprint.pprint(note.to_flat_dict())

print("\n── JSON (full parametric, for structured UI) ───────────────")
print(json.dumps(note.to_dict(), ensure_ascii=False, indent=2)[:2000], "...")