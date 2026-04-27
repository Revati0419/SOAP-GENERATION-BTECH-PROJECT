"""
Multilingual SOAP Generator
============================

PHASE 1 (current data):
  Each session turn has BOTH text_en (English) + text (Marathi).
  Pipeline: text_en → Gemma → English SOAP → NLLB → Marathi SOAP

PHASE 2 (future Marathi-only data):
  Session turns will have ONLY text (Marathi), no text_en.
  Pipeline: text (Marathi)
              → IndicNER  (extract medical entities from Marathi)
              → RAG       (retrieve clinical term context)
              → NLLB      (Marathi → English)
              → Gemma     (entity+RAG enriched English → English SOAP)
              → NLLB      (English SOAP → Marathi SOAP)

The generator auto-detects which phase applies per-session.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import re
from .soap_generator import SOAPGenerator, SOAPNote
from .soap_v2 import get_marathi_soap_generator


# ── Data class ─────────────────────────────────────────────────────────────────

@dataclass
class MultilingualSOAPNote:
    """SOAP Note in multiple languages"""
    english: SOAPNote
    target_language: SOAPNote
    input_language: str
    target_language_code: str
    target_parametric: Optional[Dict[str, Dict[str, str]]] = None

    def to_dict(self) -> Dict:
        """Return Marathi-only SOAP payload for API consumers."""
        target_parametric = self.target_parametric or self.target_language.to_parametric_dict()
        return {
            'soap_marathi': self.target_language.to_dict(),
            'soap_marathi_parametric': target_parametric,
            'metadata': {
                'input_language':  self.input_language,
                'target_language': 'marathi',
                'structure_mode': 'enhanced_parametric',
                'display_mode': 'marathi_only',
            }
        }


# ── Language detection ──────────────────────────────────────────────────────────

class LanguageDetector:
    """Detect primary language from script composition."""

    DEVANAGARI = (0x0900, 0x097F)
    LATIN      = (0x0041, 0x007A)

    @staticmethod
    def detect_language(text: str) -> str:
        """Returns 'marathi', 'hindi', 'english', or 'mixed'."""
        if not text:
            return 'english'
        dev = lat = 0
        for ch in text:
            c = ord(ch)
            if LanguageDetector.DEVANAGARI[0] <= c <= LanguageDetector.DEVANAGARI[1]:
                dev += 1
            elif LanguageDetector.LATIN[0] <= c <= LanguageDetector.LATIN[1]:
                lat += 1
        total = max(len(text), 1)
        if dev / total > 0.3:
            low = text.lower()
            marathi_cues = [
                'आहे', 'नाही', 'आणि', 'मला', 'तुम्हाला', 'कसे', 'काय', 'वाटते',
                'झोप', 'रुग्ण', 'डॉक्टर', 'चे', 'मध्ये', 'साठी',
            ]
            if ('ळ' in text or 'ऱ' in text) or any(cue in low for cue in marathi_cues):
                return 'marathi'
            return 'hindi'
        if lat / total > 0.5:
            return 'english'
        return 'mixed'

    @staticmethod
    def detect_from_turns(turns: List[Dict]) -> str:
        """Detect language by inspecting the `text` field of the first 10 turns."""
        sample = ' '.join(t.get('text', '') for t in turns[:10])
        return LanguageDetector.detect_language(sample)


# ── Main generator ──────────────────────────────────────────────────────────────

class MultilingualSOAPGenerator:
    """
    SOAP generator that handles both current (bilingual) and
    future (Marathi-only) data automatically.

    Phase 1 — bilingual data (text_en present):
        text_en → Gemma → English SOAP → NLLB → Marathi SOAP

    Phase 2 — Marathi-only data (text_en absent):
        text (Marathi)
          → IndicNER  (extract entities from Marathi)
          → RAG       (retrieve clinical term context)
          → NLLB      (Marathi → English)
          → Gemma     (entity+RAG enriched English → English SOAP)
          → NLLB      (English SOAP → Marathi SOAP)
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.active_model = self.config.get('llm_model', 'gemma2:2b')
        self.soap_generator = SOAPGenerator(
            model=self.active_model
        )
        self.marathi_soap_generator = get_marathi_soap_generator(
            model=self.active_model,
            ollama_url=self.config.get('ollama_url', 'http://localhost:11434'),
        )
        # Pre-injected at startup by api_server_complete.py (no re-download)
        self._translator        = None
        self._translator_loaded = False
        self._ner               = None
        self._ner_loaded        = False

    # ── lazy-load fallbacks (used only when not pre-injected) ──────────────

    @property
    def translator(self):
        if not self._translator_loaded:
            try:
                from src.translation import get_translator
                self._translator = get_translator(
                    model_type=self.config.get('translator_type', 'nllb'),
                    device=self.config.get('device', 'cpu'),
                )
            except Exception as e:
                print(f"⚠️ Translator unavailable: {e}")
                self._translator = None
            self._translator_loaded = True
        return self._translator

    @property
    def ner(self):
        if not self._ner_loaded:
            try:
                from src.ner import get_ner_model
                self._ner = get_ner_model(
                    model_type=self.config.get('ner_type', 'rule_based'),
                    device=self.config.get('device', 'cpu'),
                )
            except Exception as e:
                print(f"⚠️ NER unavailable: {e}")
                self._ner = None
            self._ner_loaded = True
        return self._ner

    def set_model(self, model_name: str) -> None:
        """Switch active LLM model at runtime for both English and Marathi generators."""
        model = (model_name or "").strip()
        if not model:
            return
        if model == self.active_model:
            return

        self.active_model = model
        self.config['llm_model'] = model
        self.soap_generator.model = model
        self.marathi_soap_generator.model = model
        print(f"🔁 LLM model switched to: {model}")

    # ── public API ──────────────────────────────────────────────────────────

    def generate_from_session(self,
                               session_data: Dict,
                               dialect: Optional[str] = None,
                               target_lang: Optional[str] = None,
                               ) -> MultilingualSOAPNote:
        """Entry point when you have a full session dict."""
        turns = self._extract_turns(session_data, dialect)
        if not turns:
            empty = SOAPNote("", "", "", "", "Error: No conversation found")
            return MultilingualSOAPNote(empty, empty, 'unknown', 'marathi')

        # ── Detect the TRUE session language from the `text` field ───────────
        # This is always the patient's native language (Marathi/Hindi etc.)
        # regardless of whether text_en is also present.
        true_session_lang = LanguageDetector.detect_from_turns(turns)

        # Marathi-first policy: always use native Devanagari turn text when available.
        # This preserves clinical phrasing and enables direct Marathi SOAP generation.
        conversation = self._format_turns_marathi(turns)
        gemma_input_lang = true_session_lang

        if not conversation.strip():
            # Safety fallback if session lacks text field but has text_en.
            conversation = self._format_turns_english(turns)
            gemma_input_lang = 'english'

        return self.generate_from_transcript(
            conversation=conversation,
            phq8_score=session_data.get('phq8_score', 0),
            severity=session_data.get('severity', 'unknown'),
            gender=session_data.get('gender', 'unknown'),
            # Marathi-only output for deployment/demo.
            target_lang='marathi',
            _detected_lang_override=gemma_input_lang,
            _session_lang_override=true_session_lang,
        )

    def generate_from_transcript(self,
                                  conversation: str,
                                  phq8_score: int = 0,
                                  severity: str = "unknown",
                                  gender: str = "unknown",
                                  target_lang: Optional[str] = None,
                                  _detected_lang_override: Optional[str] = None,
                                  _session_lang_override: Optional[str] = None,
                                  ) -> MultilingualSOAPNote:
        """
        Core pipeline — works for both Phase 1 and Phase 2 data.

        _detected_lang_override : language of the text actually fed to Gemma
                                   (always 'english' in Phase 1)
        _session_lang_override  : TRUE language of the session (e.g. 'marathi')
                                   used only for input_language in metadata
        """
        detected_lang = _detected_lang_override or LanguageDetector.detect_language(conversation)
        # True session lang — what the patient actually spoke
        session_lang  = _session_lang_override or detected_lang
        # Enforce Marathi-only output.
        target_lang = 'marathi'

        # Primary path: direct Marathi SOAP generation without back-translation.
        if session_lang in ('marathi', 'hindi', 'mixed') or detected_lang in ('marathi', 'hindi', 'mixed'):
            try:
                marathi_note = self.marathi_soap_generator.generate(
                    conversation=conversation,
                    phq8_score=phq8_score,
                    severity=severity,
                    gender=gender,
                )
                marathi_flat = marathi_note.to_flat_dict()
                parametric = self._normalize_v2_parametric(marathi_note.to_dict())
                parametric = self._recover_non_marathi_parametric(parametric)
                marathi_soap = self._build_soap_from_parametric(parametric, marathi_note.raw_output)

                return MultilingualSOAPNote(
                    english=SOAPNote('', '', '', '', ''),
                    target_language=marathi_soap,
                    input_language=session_lang,
                    target_language_code=target_lang,
                    target_parametric=parametric,
                )
            except Exception as e:
                print(f"⚠️ Direct Marathi generation failed, using fallback pipeline: {e}")

        ner_context = ""
        rag_context = ""

        # ── PHASE 2 only: IndicNER + RAG + translation ─────────────────────
        if detected_lang in ('marathi', 'hindi', 'mixed'):

            # Step 1 — IndicNER: extract medical entities from Marathi text
            if self.ner:
                try:
                    entities = self.ner.extract_entities(conversation)
                    if entities:
                        by_type: Dict[str, List[str]] = {}
                        for e in entities:
                            by_type.setdefault(e.label, []).append(e.text)
                        ner_context = "\n\nExtracted Medical Entities (from Marathi):\n"
                        for label, items in by_type.items():
                            ner_context += f"  {label}: {', '.join(dict.fromkeys(items))}\n"
                except Exception as e:
                    print(f"⚠️ NER failed: {e}")

            # Step 2 — RAG: retrieve clinical terminology context
            # (activate via config: use_rag=True and _rag_store=<ClinicalVectorStore>)
            rag_store = self.config.get('_rag_store') if self.config.get('use_rag') else None
            if rag_store:
                try:
                    results = rag_store.search(conversation[:400], n_results=5)
                    if results:
                        rag_context = "\n\nRelevant Clinical Terms:\n"
                        for r in results:
                            rag_context += (
                                f"  EN: {r['english']}  "
                                f"MR: {r.get('marathi', '')}  "
                                f"HI: {r.get('hindi', '')}\n"
                            )
                except Exception as e:
                    print(f"⚠️ RAG failed: {e}")

            # Step 3 — NLLB: Marathi → English conversation
            if self.translator:
                try:
                    conversation = self.translator.translate(
                        conversation,
                        source_lang=detected_lang,
                        target_lang='english',
                    )
                except Exception as e:
                    print(f"⚠️ Translation failed: {e}")

        # ── BOTH PHASES: Gemma generates English SOAP ──────────────────────
        enriched_conversation = conversation + ner_context + rag_context

        # print("📝 Gemma: generating English SOAP note...")
        english_soap = self.soap_generator.generate(
            conversation=enriched_conversation,
            phq8_score=phq8_score,
            severity=severity,
            gender=gender,
        )

        # ── Translate English SOAP → target language ───────────────────────
        target_soap = english_soap
        if target_lang != 'english' and self.translator:
            # print(f"🔄 NLLB: translating SOAP → {target_lang}...")
            target_soap = self._translate_soap(english_soap, target_lang)

        return MultilingualSOAPNote(
            english=english_soap,
            target_language=target_soap,
            input_language=session_lang,        # true patient language, not Gemma feed lang
            target_language_code=target_lang,
            target_parametric=target_soap.to_parametric_dict(),
        )

    # ── private helpers ─────────────────────────────────────────────────────

    def _extract_turns(self, session_data: Dict, dialect: Optional[str]) -> List[Dict]:
        # 1) Explicit dialect selection from legacy schema
        if dialect:
            turns = session_data.get('dialects', {}).get(dialect, [])
            if turns:
                return turns

        # 2) Legacy schema: dialects
        dialects = session_data.get('dialects', {})
        if isinstance(dialects, dict) and dialects:
            first = dialects[next(iter(dialects))]
            if isinstance(first, list) and first:
                return first

        # 3) Newer synthetic schema: styles (e.g., formal_translated)
        # synthetic_data/* files often store turn lists under styles.*
        styles = session_data.get('styles', {})
        if isinstance(styles, dict) and styles:
            preferred_style_order = [
                'formal_translated',
                'translated',
                'formal',
                'colloquial',
                'neutral',
            ]

            for key in preferred_style_order:
                candidate = styles.get(key)
                if isinstance(candidate, list) and candidate:
                    return candidate

            for value in styles.values():
                if isinstance(value, list) and value:
                    return value

        # 4) Flat schema fallback
        turns = session_data.get('turns', [])
        if isinstance(turns, list) and turns:
            return turns

        # 5) Last-resort alternatives seen in some exports
        for key in ('conversation', 'dialogue', 'messages'):
            value = session_data.get(key)
            if isinstance(value, list) and value:
                return value

        return []

    def _format_turns_english(self, turns: List[Dict], max_turns: int = 40) -> str:
        """
        PHASE 1: both text_en and text present → always use text_en.
        Capped at 40 turns (first 20 + last 20).
        """
        sel = (
            turns[: max_turns // 2] + turns[-(max_turns // 2):]
            if len(turns) > max_turns else turns
        )
        lines = []
        for t in sel:
            role = t.get('role', 'Unknown')
            text = t.get('text_en', '') or t.get('text', '')
            if text:
                lines.append(f"{role}: {text}")
        return "\n".join(lines)

    def _format_turns_marathi(self, turns: List[Dict], max_turns: int = 40) -> str:
        """
        PHASE 2: Marathi-only data → use text field.
        Capped at 40 turns (first 20 + last 20).
        """
        sel = (
            turns[: max_turns // 2] + turns[-(max_turns // 2):]
            if len(turns) > max_turns else turns
        )
        lines = []
        for t in sel:
            role = t.get('role', 'Unknown')
            text = t.get('text', '') or t.get('text_en', '')
            if text:
                lines.append(f"{role}: {text}")
        return "\n".join(lines)

    def _translate_soap(self, soap_note: SOAPNote, target_lang: str) -> SOAPNote:
        """Translate each English SOAP section to target language via NLLB."""
        if not self.translator:
            return soap_note

        sections = [
            soap_note.subjective or "",
            soap_note.objective  or "",
            soap_note.assessment or "",
            soap_note.plan       or "",
        ]
        if not any(s.strip() for s in sections):
            print("   ⚠️ Skipping translation — SOAP is empty (LLM failed)")
            return soap_note

        try:
            names      = ["Subjective", "Objective", "Assessment", "Plan"]
            translated = []
            for name, text in zip(names, sections):
                if text.strip():
                    print(f"      → {name}...")
                    translated_text = self.translator.translate(text, 'english', target_lang)
                    if not isinstance(translated_text, str) or not translated_text.strip():
                        translated_text = text
                    translated.append(translated_text)
                else:
                    translated.append("- Not clearly elicited from interview.")

            return SOAPNote(
                subjective=translated[0],
                objective=translated[1],
                assessment=translated[2],
                plan=translated[3],
                raw_output=soap_note.raw_output,
            )
        except Exception as e:
            print(f"⚠️ Translation error: {e}")
            return soap_note

    def _normalize_v2_parametric(self, raw_v2: Dict) -> Dict[str, Dict[str, str]]:
        """Map soap_v2 parametric field names to API/UI contract keys."""
        subjective = raw_v2.get('subjective', {}) or {}
        objective = raw_v2.get('objective', {}) or {}
        assessment = raw_v2.get('assessment', {}) or {}
        plan = raw_v2.get('plan', {}) or {}

        return {
            'subjective': {
                'chief_complaint': subjective.get('chief_complaint', ''),
                'hpi': subjective.get('hpi', ''),
                'trauma_history': subjective.get('trauma_history', ''),
                'psychosocial_history': subjective.get('psychosocial_history', ''),
                'functional_status': subjective.get('functional_status', ''),
            },
            'objective': {
                'medical_history': objective.get('medical_history', ''),
                'past_psych_history': objective.get('past_psych_history', ''),
                'biological_observations': objective.get('biological_obs', ''),
                'mental_status_exam': objective.get('mental_status_exam', ''),
                'structured_scores': objective.get('phq8_score', ''),
            },
            'assessment': {
                'diagnostic_formulation': assessment.get('diagnostic_formulation', ''),
                'risk_formulation': assessment.get('risk_formulation', ''),
                'contributing_factors': assessment.get('contributing_factors', ''),
            },
            'plan': {
                'treatment_safety_plan': plan.get('treatment_safety_plan', ''),
                'therapy_plan': plan.get('therapy_plan', ''),
                'medication_considerations': plan.get('medication', ''),
                'followup_monitoring': plan.get('followup', ''),
            },
        }

    def _devanagari_ratio(self, text: str) -> float:
        if not text:
            return 0.0
        total = max(len(text), 1)
        dev = sum(1 for ch in text if 0x0900 <= ord(ch) <= 0x097F)
        return dev / total

    def _latin_ratio(self, text: str) -> float:
        if not text:
            return 0.0
        total = max(len(text), 1)
        lat = sum(1 for ch in text if ('a' <= ch.lower() <= 'z'))
        return lat / total

    def _looks_non_marathi(self, text: str) -> bool:
        stripped = (text or "").strip()
        if not stripped:
            return False
        if "संवादातून स्पष्ट झाले नाही" in stripped:
            return False
        dev = self._devanagari_ratio(stripped)
        lat = self._latin_ratio(stripped)
        return lat > 0.20 and dev < 0.10

    def _translate_field_to_marathi(self, text: str) -> str:
        if not text.strip() or not self.translator:
            return text
        try:
            translated = self.translator.translate(text, 'english', 'marathi')
            if isinstance(translated, str) and translated.strip():
                return translated
        except Exception as e:
            print(f"⚠️ Marathi recovery translation failed: {e}")
        return text

    def _recover_non_marathi_parametric(self, parametric: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
        """If direct Marathi generation leaks English, translate only affected fields to Marathi."""
        recovered: Dict[str, Dict[str, str]] = {}
        english_like_fields = 0
        total_fields = 0

        for section, fields in (parametric or {}).items():
            recovered[section] = {}
            for key, value in (fields or {}).items():
                text = str(value or "").strip()
                if not text:
                    recovered[section][key] = "- संवादातून स्पष्ट झाले नाही."
                    continue
                total_fields += 1
                if self._looks_non_marathi(text):
                    english_like_fields += 1
                recovered[section][key] = text

        # Recovery gate: translate only when significant English leakage exists.
        if total_fields > 0 and english_like_fields >= max(2, total_fields // 3):
            print("⚠️ Detected English-heavy direct output; applying Marathi recovery translation...")
            for section, fields in recovered.items():
                candidates = [(k, v) for k, v in fields.items() if self._looks_non_marathi(v)]
                if not candidates:
                    continue

                # Batch translate by section to reduce repeated model invocation overhead.
                translated = self._translate_section_fields_to_marathi(candidates)
                for key, value in translated.items():
                    fields[key] = value

        return recovered

    def _translate_section_fields_to_marathi(self, fields: List[tuple]) -> Dict[str, str]:
        """Translate multiple fields in one shot and map them back safely by markers."""
        if not fields or not self.translator:
            return {k: v for k, v in fields}

        markers = []
        payload_parts = []
        for idx, (_, text) in enumerate(fields, start=1):
            marker = f"[[F{idx}]]"
            markers.append(marker)
            payload_parts.append(f"{marker}\n{text}")

        payload = "\n".join(payload_parts)

        try:
            translated_payload = self.translator.translate(payload, 'english', 'marathi')
            if not isinstance(translated_payload, str) or not translated_payload.strip():
                return {k: self._translate_field_to_marathi(v) for k, v in fields}

            # Parse marker-delimited chunks back to fields.
            chunks = re.split(r"(\[\[F\d+\]\])", translated_payload)
            parsed: Dict[str, str] = {}
            current_marker = None
            marker_to_text: Dict[str, str] = {}
            for chunk in chunks:
                if not chunk:
                    continue
                if re.fullmatch(r"\[\[F\d+\]\]", chunk):
                    current_marker = chunk
                    marker_to_text[current_marker] = ""
                elif current_marker:
                    marker_to_text[current_marker] += chunk

            for idx, (key, original) in enumerate(fields, start=1):
                marker = f"[[F{idx}]]"
                translated_text = (marker_to_text.get(marker) or "").strip()
                parsed[key] = translated_text if translated_text else self._translate_field_to_marathi(original)

            return parsed
        except Exception as e:
            print(f"⚠️ Section-level Marathi recovery failed: {e}")
            return {k: self._translate_field_to_marathi(v) for k, v in fields}

    def _build_soap_from_parametric(self, parametric: Dict[str, Dict[str, str]], raw_output: str) -> SOAPNote:
        def join_fields(title_value_pairs: List[tuple]) -> str:
            lines: List[str] = []
            for heading, value in title_value_pairs:
                v = str(value or "").strip() or "- संवादातून स्पष्ट झाले नाही."
                lines.append(f"{heading}:\n{v}")
            return "\n".join(lines)

        s = (parametric or {}).get('subjective', {})
        o = (parametric or {}).get('objective', {})
        a = (parametric or {}).get('assessment', {})
        p = (parametric or {}).get('plan', {})

        return SOAPNote(
            subjective=join_fields([
                ("मुख्य तक्रार", s.get('chief_complaint')),
                ("सध्याच्या आजाराचा इतिहास", s.get('hpi')),
                ("आघाताचा इतिहास", s.get('trauma_history')),
                ("मनोसामाजिक इतिहास", s.get('psychosocial_history')),
                ("कार्यक्षम स्थिती", s.get('functional_status')),
            ]),
            objective=join_fields([
                ("वैद्यकीय इतिहास", o.get('medical_history')),
                ("पूर्व मनोरुग्ण इतिहास", o.get('past_psych_history')),
                ("जैविक निरीक्षणे", o.get('biological_observations')),
                ("मानसिक स्थिती तपासणी", o.get('mental_status_exam')),
                ("PHQ-8 गुण", o.get('structured_scores')),
            ]),
            assessment=join_fields([
                ("निदान", a.get('diagnostic_formulation')),
                ("जोखीम मूल्यांकन", a.get('risk_formulation')),
                ("योगदान देणारे घटक", a.get('contributing_factors')),
            ]),
            plan=join_fields([
                ("उपचार आणि सुरक्षा योजना", p.get('treatment_safety_plan')),
                ("मानसोपचार योजना", p.get('therapy_plan')),
                ("औषधोपचार", p.get('medication_considerations')),
                ("पाठपुरावा", p.get('followup_monitoring')),
            ]),
            raw_output=raw_output,
        )


# ── Factory ─────────────────────────────────────────────────────────────────────

def get_multilingual_soap_generator(config: Optional[Dict] = None) -> MultilingualSOAPGenerator:
    return MultilingualSOAPGenerator(config=config)
