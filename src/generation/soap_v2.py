"""
soap_note_v2.py
================
Drop-in replacement for soap_generator.py + multilingual_soap_generator.py

Key changes:
  1. SOAPNote is now PARAMETRIC — each subsection is its own field.
  2. SOAP is generated directly in Marathi (no post-hoc translation step).
  3. The Marathi `text` field from your JSON is used as primary input.
  4. Parser extracts subsections from the LLM output by heading name.
"""

from __future__ import annotations

import json
import re
import requests
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


# ─────────────────────────────────────────────────────────────────
# 1.  PARAMETRIC SOAP NOTE  (structured subsections)
# ─────────────────────────────────────────────────────────────────

@dataclass
class SubjectiveSection:
    chief_complaint:      str = ""   # मुख्य तक्रार
    hpi:                  str = ""   # सध्याच्या आजाराचा इतिहास
    trauma_history:       str = ""   # आघाताचा इतिहास
    psychosocial_history: str = ""   # मनोसामाजिक इतिहास
    functional_status:    str = ""   # कार्यक्षम स्थिती

@dataclass
class ObjectiveSection:
    medical_history:      str = ""   # वैद्यकीय इतिहास
    past_psych_history:   str = ""   # पूर्व मनोरुग्ण इतिहास
    biological_obs:       str = ""   # जैविक निरीक्षणे (झोप, भूक, ऊर्जा)
    mental_status_exam:   str = ""   # मानसिक स्थिती तपासणी (MSE)
    phq8_score:           str = ""   # PHQ-8 गुण

@dataclass
class AssessmentSection:
    diagnostic_formulation: str = ""  # निदान
    risk_formulation:       str = ""  # जोखीम मूल्यांकन
    contributing_factors:   str = ""  # योगदान देणारे घटक

@dataclass
class PlanSection:
    treatment_safety_plan: str = ""   # उपचार आणि सुरक्षा योजना
    therapy_plan:          str = ""   # मानसोपचार योजना
    medication:            str = ""   # औषधोपचार
    followup:              str = ""   # पाठपुरावा

@dataclass
class ParametricSOAPNote:
    subjective:  SubjectiveSection  = field(default_factory=SubjectiveSection)
    objective:   ObjectiveSection   = field(default_factory=ObjectiveSection)
    assessment:  AssessmentSection  = field(default_factory=AssessmentSection)
    plan:        PlanSection        = field(default_factory=PlanSection)
    language:    str                = "marathi"
    raw_output:  str                = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_flat_dict(self) -> Dict[str, str]:
        """Flat representation compatible with the old SOAPNote.to_dict()."""
        s, o, a, p = self.subjective, self.objective, self.assessment, self.plan
        return {
            "subjective": "\n".join(filter(None, [
                _fmt("मुख्य तक्रार", s.chief_complaint),
                _fmt("सध्याच्या आजाराचा इतिहास", s.hpi),
                _fmt("आघाताचा इतिहास", s.trauma_history),
                _fmt("मनोसामाजिक इतिहास", s.psychosocial_history),
                _fmt("कार्यक्षम स्थिती", s.functional_status),
            ])),
            "objective": "\n".join(filter(None, [
                _fmt("वैद्यकीय इतिहास", o.medical_history),
                _fmt("पूर्व मनोरुग्ण इतिहास", o.past_psych_history),
                _fmt("जैविक निरीक्षणे", o.biological_obs),
                _fmt("मानसिक स्थिती तपासणी", o.mental_status_exam),
                _fmt("PHQ-8", o.phq8_score),
            ])),
            "assessment": "\n".join(filter(None, [
                _fmt("निदान", a.diagnostic_formulation),
                _fmt("जोखीम मूल्यांकन", a.risk_formulation),
                _fmt("योगदान देणारे घटक", a.contributing_factors),
            ])),
            "plan": "\n".join(filter(None, [
                _fmt("उपचार आणि सुरक्षा योजना", p.treatment_safety_plan),
                _fmt("मानसोपचार योजना", p.therapy_plan),
                _fmt("औषधोपचार", p.medication),
                _fmt("पाठपुरावा", p.followup),
            ])),
        }


def _fmt(heading: str, body: str) -> str:
    return f"{heading}:\n{body}" if body.strip() else ""


# ─────────────────────────────────────────────────────────────────
# 2.  MARATHI SOAP PROMPT
# ─────────────────────────────────────────────────────────────────

MARATHI_SOAP_PROMPT = """\
तुम्ही एक अनुभवी मनोचिकित्सक आहात. खालील रुग्ण-डॉक्टर संवादावर आधारित क्लिनिकल SOAP नोट मराठीत तयार करा.

PHQ-8 गुण: {phq8_score}/24 | तीव्रता: {severity} | लिंग: {gender}

संवाद:
{conversation}

नियम:
1) फक्त संवादातून मिळालेली माहिती वापरा. स्वतःहून काहीही जोडू नका.
2) माहिती उपलब्ध नसल्यास लिहा: "- संवादातून स्पष्ट झाले नाही."
3) प्रत्येक मुद्दा नवीन ओळीवर "- " ने सुरू करा.
4) खाली दिलेले शीर्षक (headings) जसेच्या तसे ठेवा. heading नंतर ":" लावा.
5) Markdown (###, **, ``` इ.) वापरू नका.
6) फक्त खालील structure output करा.
7) खाली दिलेल्या मार्गदर्शक वर्णन-ओळी (उदा. "रुग्णाच्या शब्दात...") आउटपुटमध्ये कॉपी करू नका.
8) प्रत्येक उपविभागात 1-2 ठोस, संवाद-आधारित मुद्दे द्या; माहिती नसेल तर फक्त "- संवादातून स्पष्ट झाले नाही." द्या.
9) सर्वसाधारण/template मजकूर देऊ नका (उदा. "तात्काळ पुढील पावले", "उपचार पद्धती" असे generic शब्दशः लिहू नका जोपर्यंत संवादातून पुरावा नाही).

SUBJECTIVE:
मुख्य तक्रार:
- रुग्णाच्या शब्दात भेटीचे प्राथमिक कारण.
सध्याच्या आजाराचा इतिहास:
- लक्षणांचा कालावधी, बदल, कारणे, आराम देणारे घटक.
आघाताचा इतिहास:
- भूतकाळातील आघात, दुःख, खेद (उल्लेख असल्यास).
मनोसामाजिक इतिहास:
- कुटुंब, नाती, सामाजिक आधार, बालपण.
कार्यक्षम स्थिती:
- दैनंदिन कामे, छंद, काम/शिक्षणावर परिणाम.

OBJECTIVE:
वैद्यकीय इतिहास:
- संबंधित शारीरिक आजार, सहविकार, औषधे.
पूर्व मनोरुग्ण इतिहास:
- पूर्वीचे निदान, उपचार, रुग्णालय प्रवेश.
जैविक निरीक्षणे:
- झोप, भूक, ऊर्जा, शारीरिक/सायकोमोटर निरीक्षणे.
मानसिक स्थिती तपासणी:
- देखावा, वर्तन, बोलणे, मनस्थिती/affect, विचारप्रक्रिया, अंतर्दृष्टी.
PHQ-8 गुण:
- {phq8_score} ({severity})

ASSESSMENT:
निदान:
- संवाद पुराव्यावर आधारित संभाव्य निदान आणि कारणमीमांसा.
जोखीम मूल्यांकन:
- आत्महत्या/स्वतःला इजा/हिंसेचा धोका, संरक्षणात्मक घटक.
योगदान देणारे घटक:
- जैविक, मानसिक, सामाजिक घटक.

PLAN:
उपचार आणि सुरक्षा योजना:
- तात्काळ पुढील पावले आणि संकट/सुरक्षा मार्गदर्शन.
मानसोपचार योजना:
- उपचार पद्धती (CBT, आधारभूत थेरपी इ.), अल्पकालीन उद्दिष्टे.
औषधोपचार:
- सूचित असल्यास, मूल्यमापन/रेफरल आणि adherence समुपदेशन.
पाठपुरावा:
- वेळापत्रक, चेतावणी चिन्हे, मोजता येण्याजोगे review checkpoints.
"""


# ─────────────────────────────────────────────────────────────────
# 3.  SOAP GENERATOR  (Marathi-first)
# ─────────────────────────────────────────────────────────────────

# Maps prompt heading → dataclass field path  (section, field_name)
_SUBSECTION_MAP: List[tuple] = [
    # SUBJECTIVE
    ("मुख्य तक्रार",                ("subjective", "chief_complaint")),
    ("सध्याच्या आजाराचा इतिहास",    ("subjective", "hpi")),
    ("आघाताचा इतिहास",              ("subjective", "trauma_history")),
    ("मनोसामाजिक इतिहास",           ("subjective", "psychosocial_history")),
    ("कार्यक्षम स्थिती",             ("subjective", "functional_status")),
    # OBJECTIVE
    ("वैद्यकीय इतिहास",              ("objective", "medical_history")),
    ("पूर्व मनोरुग्ण इतिहास",        ("objective", "past_psych_history")),
    ("जैविक निरीक्षणे",             ("objective", "biological_obs")),
    ("मानसिक स्थिती तपासणी",         ("objective", "mental_status_exam")),
    ("PHQ-8 गुण",                    ("objective", "phq8_score")),
    # ASSESSMENT
    ("निदान",                        ("assessment", "diagnostic_formulation")),
    ("जोखीम मूल्यांकन",              ("assessment", "risk_formulation")),
    ("योगदान देणारे घटक",            ("assessment", "contributing_factors")),
    # PLAN
    ("उपचार आणि सुरक्षा योजना",      ("plan", "treatment_safety_plan")),
    ("मानसोपचार योजना",              ("plan", "therapy_plan")),
    ("औषधोपचार",                    ("plan", "medication")),
    ("पाठपुरावा",                    ("plan", "followup")),
]

# Top-level section markers
_TOP_SECTION_RE = re.compile(
    r"^\s*(SUBJECTIVE|OBJECTIVE|ASSESSMENT|PLAN)\s*:?\s*$",
    re.IGNORECASE
)


def _normalize_heading_text(value: str) -> str:
    """Normalize heading text for fuzzy matching across markdown/noisy outputs."""
    cleaned = value.replace("**", "").strip()
    cleaned = re.sub(r"^#+\s*", "", cleaned)
    cleaned = cleaned.rstrip(":").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _clean_content_line(value: str) -> str:
    """Normalize content line and drop trivial noise markers."""
    line = value.replace("**", "").strip()
    line = re.sub(r"^#+\s*", "", line).strip()
    line = line.lstrip("-").strip()

    # Drop empty/trivial placeholders that degrade UI quality.
    if line in {"", "-", ":", "::"}:
        return ""

    # Drop guide/template phrases that LLM sometimes copies from prompt instructions.
    guidance_phrases = [
        "रुग्णाच्या शब्दात भेटीचे प्राथमिक कारण",
        "लक्षणांचा कालावधी, बदल, कारणे",
        "भूतकाळातील आघात, दुःख, खेद",
        "कुटुंब, नाती, सामाजिक आधार",
        "दैनंदिन कामे, छंद, काम/शिक्षणावर परिणाम",
        "संबंधित शारीरिक आजार, सहविकार, औषधे",
        "पूर्वीचे निदान, उपचार, रुग्णालय प्रवेश",
        "झोप, भूक, ऊर्जा",
        "देखावा, वर्तन, बोलणे",
        "संवाद पुराव्यावर आधारित संभाव्य निदान",
        "आत्महत्या/स्वतःला इजा/हिंसेचा धोका",
        "जैविक, मानसिक, सामाजिक घटक",
        "तात्काळ पुढील पावले आणि संकट/सुरक्षा मार्गदर्शन",
        "उपचार पद्धती",
        "सूचित असल्यास, मूल्यमापन/रेफरल",
        "वेळापत्रक, चेतावणी चिन्हे",
    ]
    low = line.lower()
    if any(phrase in line for phrase in guidance_phrases):
        return ""
    if low in {"उपचार", "मानसोपचार", "योजना", "आणि सुरक्षा योजना"}:
        return ""

    return f"- {line}"


class MarathiSOAPGenerator:
    """
    Generates a fully Marathi, parametric SOAP note directly from
    Marathi conversation text using Gemma via Ollama.
    """

    def __init__(self, model: str = "gemma2:2b",
                 ollama_url: str = "http://localhost:11434"):
        self.model        = model
        self.ollama_url   = ollama_url
        self.api_endpoint = f"{ollama_url}/api/generate"

    # ── public ──────────────────────────────────────────────────

    def generate_from_session(self, session_data: Dict,
                               dialect: str = "standard_pune") -> ParametricSOAPNote:
        """Entry point: pass a session dict loaded from your JSON files."""
        turns = self._extract_turns(session_data, dialect)
        if not turns:
            return ParametricSOAPNote(raw_output="Error: No conversation found")

        conversation = self._format_marathi_turns(turns)

        return self.generate(
            conversation=conversation,
            phq8_score=session_data.get("phq8_score", 0),
            severity=session_data.get("severity", "अज्ञात"),
            gender=session_data.get("gender", "अज्ञात"),
        )

    def generate(self, conversation: str,
                 phq8_score: int = 0,
                 severity: str = "अज्ञात",
                 gender: str = "अज्ञात",
                 temperature: float = 0.2,
                 timeout: int = 300) -> ParametricSOAPNote:
        """Core generation: conversation (Marathi) → ParametricSOAPNote."""
        prompt = MARATHI_SOAP_PROMPT.format(
            conversation=self._trim_conversation(conversation),
            phq8_score=phq8_score,
            severity=severity,
            gender=gender,
        )

        raw = self._call_ollama(prompt, temperature, timeout)
        note = self._parse(raw, phq8_score, severity)
        note.raw_output = raw
        return note

    # ── Ollama call ──────────────────────────────────────────────

    def _call_ollama(self, prompt: str, temperature: float, timeout: int) -> str:
        raw = ""
        try:
            resp = requests.post(
                self.api_endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        "top_p": 0.9,
                        "repeat_penalty": 1.08,
                        "num_ctx": 3072,
                        "num_thread": 4,
                    },
                },
                timeout=timeout,
                stream=True,
            )
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        raw += chunk.get("response", "")
                        if chunk.get("done"):
                            break
                    except Exception:
                        pass
        except requests.exceptions.Timeout:
            print(f"⚠️  Timeout — parsing partial output")
        except Exception as e:
            print(f"❌  Ollama error: {e}")
        return raw.strip()

    # ── Parser ───────────────────────────────────────────────────

    def _parse(self, text: str, phq8_score: int, severity: str) -> ParametricSOAPNote:
        """
        Parse LLM output into ParametricSOAPNote.
        Strategy:
          1. Walk lines looking for top-level headers (SUBJECTIVE / OBJECTIVE …)
             and subsection headings (मुख्य तक्रार: etc.)
          2. Accumulate bullet lines under each subsection heading.
          3. Assign to the matching dataclass field via _SUBSECTION_MAP.
        """
        note = ParametricSOAPNote(language="marathi")

        # Build lookups for exact and normalized heading matching.
        heading_lookup: Dict[str, tuple] = {h: path for h, path in _SUBSECTION_MAP}
        normalized_heading_lookup: Dict[str, tuple] = {
            _normalize_heading_text(h): path for h, path in _SUBSECTION_MAP
        }
        known_heading_names = set(normalized_heading_lookup.keys())

        current_field: Optional[tuple] = None   # ("subjective", "chief_complaint")
        buffers: Dict[tuple, List[str]] = {}

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # Normalize noisy markdown wrappers generated by LLM.
            line = re.sub(r"^#+\s*", "", line)
            line = line.replace("**", "").strip()

            # Skip top-level SOAP markers
            if _TOP_SECTION_RE.match(line):
                current_field = None
                continue

            # Subsection heading can be either:
            # 1) heading only: "मुख्य तक्रार:"
            # 2) inline content: "मुख्य तक्रार: रुग्णाला झोप येत नाही"
            matched_heading = False

            # Exact heading match fast path.
            for heading, path in heading_lookup.items():
                if line == heading or line == f"{heading}:":
                    current_field = path
                    buffers.setdefault(current_field, [])
                    matched_heading = True
                    break

            # Fuzzy heading or inline content heading match.
            if not matched_heading:
                normalized_line = _normalize_heading_text(line)

                if normalized_line in normalized_heading_lookup:
                    current_field = normalized_heading_lookup[normalized_line]
                    buffers.setdefault(current_field, [])
                    matched_heading = True
                else:
                    for norm_heading, path in normalized_heading_lookup.items():
                        prefix = norm_heading + ":"
                        low_line = _normalize_heading_text(line.lower())
                        low_heading = norm_heading.lower()

                        # Supports: "मुख्य तक्रार: ..." and close variants.
                        if low_line.startswith(low_heading + ":"):
                            current_field = path
                            buffers.setdefault(current_field, [])
                            inline_value = line.split(":", 1)[1].strip() if ":" in line else ""
                            cleaned_inline = _clean_content_line(inline_value)
                            if cleaned_inline:
                                buffers[current_field].append(cleaned_inline)
                            matched_heading = True
                            break

            if matched_heading:
                continue

            # Prevent heading fragments from being stored as content.
            normalized_line = _normalize_heading_text(line)
            if normalized_line in known_heading_names:
                continue

            # Content line — add to current buffer
            if current_field is not None:
                cleaned_line = _clean_content_line(line)
                if cleaned_line:
                    buffers[current_field].append(cleaned_line)

        # Write buffers → dataclass fields
        default = "- संवादातून स्पष्ट झाले नाही."
        for (sec_attr, fld_attr), lines in buffers.items():
            section_obj = getattr(note, sec_attr)
            value = "\n".join(lines).strip() or default
            setattr(section_obj, fld_attr, value)

        # Ensure PHQ-8 is always filled
        if not note.objective.phq8_score.strip():
            note.objective.phq8_score = f"- {phq8_score} ({severity})"

        # If model leaks PHQ line into MSE field, move it to structured score.
        mse_text = note.objective.mental_status_exam or ""
        if mse_text and ("phq-8" in mse_text.lower() or "phq8" in mse_text.lower() or "phq" in mse_text.lower()):
            extracted = []
            kept = []
            for ln in mse_text.splitlines():
                clean_ln = ln.strip()
                if not clean_ln:
                    continue
                if "phq" in clean_ln.lower():
                    normalized = clean_ln if clean_ln.startswith("-") else f"- {clean_ln}"
                    extracted.append(normalized)
                else:
                    kept.append(clean_ln if clean_ln.startswith("-") else f"- {clean_ln}")

            if extracted:
                existing_score = (note.objective.phq8_score or "").strip()
                if existing_score == "" or "संवादातून स्पष्ट झाले नाही" in existing_score:
                    note.objective.phq8_score = "\n".join(extracted)
                note.objective.mental_status_exam = "\n".join(kept).strip() or default

        # Fill any empty fields with default
        for _, (sec_attr, fld_attr) in _SUBSECTION_MAP:
            section_obj = getattr(note, sec_attr)
            if not getattr(section_obj, fld_attr, "").strip():
                setattr(section_obj, fld_attr, default)

        return note

    # ── Helpers ──────────────────────────────────────────────────

    def _extract_turns(self, session_data: Dict, dialect: str) -> List[Dict]:
        """Support both dialects-schema and flat turns-schema."""
        # Try requested dialect first
        turns = session_data.get("dialects", {}).get(dialect, [])
        if turns:
            return turns
        # Any available dialect
        for v in session_data.get("dialects", {}).values():
            if isinstance(v, list) and v:
                return v
        # Flat schema fallbacks
        for key in ("turns", "conversation", "dialogue", "messages"):
            v = session_data.get(key)
            if isinstance(v, list) and v:
                return v
        return []

    def _format_marathi_turns(self, turns: List[Dict],
                               max_turns: int = 50) -> str:
        """
        Use Marathi `text` field.  Falls back to `text_en` only if `text`
        is absent (should not happen with your current data).
        """
        if len(turns) > max_turns:
            turns = turns[: max_turns // 2] + turns[-(max_turns // 2):]

        lines = []
        for t in turns:
            role = t.get("role", "अज्ञात")
            text = t.get("text", "") or t.get("text_en", "")
            if text:
                lines.append(f"{role}: {text}")
        return "\n".join(lines)

    def _trim_conversation(self, conv: str, max_chars: int = 6000) -> str:
        if len(conv) <= max_chars:
            return conv
        half = max_chars // 2
        return conv[:half] + "\n...\n" + conv[-half:]


# ─────────────────────────────────────────────────────────────────
# 4.  FACTORY
# ─────────────────────────────────────────────────────────────────

def get_marathi_soap_generator(model: str = "gemma2:2b",
                                ollama_url: str = "http://localhost:11434"
                                ) -> MarathiSOAPGenerator:
    return MarathiSOAPGenerator(model=model, ollama_url=ollama_url)