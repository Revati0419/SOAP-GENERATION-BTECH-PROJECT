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
from .soap_generator import SOAPGenerator, SOAPNote


# ── Data class ─────────────────────────────────────────────────────────────────

@dataclass
class MultilingualSOAPNote:
    """SOAP Note in multiple languages"""
    english: SOAPNote
    target_language: SOAPNote
    input_language: str
    target_language_code: str

    def to_dict(self) -> Dict:
        """Return SINGLE-LANGUAGE output (input/session language only)."""
        return {
            f'soap_{self.target_language_code}': self.target_language.to_dict(),
            'metadata': {
                'input_language':  self.input_language,
                'target_language': self.target_language_code,
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
            return 'marathi' if ('ळ' in text or 'ऱ' in text) else 'hindi'
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
        self.soap_generator = SOAPGenerator(
            model=self.config.get('llm_model', 'gemma2:2b')
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
            return MultilingualSOAPNote(empty, empty, 'unknown', target_lang or 'marathi')

        # ── Detect the TRUE session language from the `text` field ───────────
        # This is always the patient's native language (Marathi/Hindi etc.)
        # regardless of whether text_en is also present.
        true_session_lang = LanguageDetector.detect_from_turns(turns)

        # ── Auto-detect phase ──────────────────────────────────────────────
        has_english = any(t.get('text_en', '').strip() for t in turns[:5])

        if has_english:
            # PHASE 1: bilingual — feed text_en to Gemma (better quality),
            # but record true_session_lang as input_language in metadata.
            conversation       = self._format_turns_english(turns)
            gemma_input_lang   = 'english'          # what Gemma actually receives
        else:
            # PHASE 2: Marathi-only — text field is the only source
            conversation       = self._format_turns_marathi(turns)
            gemma_input_lang   = true_session_lang  # Marathi goes through NLLB first

        return self.generate_from_transcript(
            conversation=conversation,
            phq8_score=session_data.get('phq8_score', 0),
            severity=session_data.get('severity', 'unknown'),
            gender=session_data.get('gender', 'unknown'),
            # Default target = same as input language (caller can still override)
            target_lang=target_lang or true_session_lang,
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
        # Enforce output in the same language the patient/session used.
        target_lang = session_lang

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
                    translated.append(
                        self.translator.translate(text, 'english', target_lang)
                    )
                else:
                    translated.append("")

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


# ── Factory ─────────────────────────────────────────────────────────────────────

def get_multilingual_soap_generator(config: Optional[Dict] = None) -> MultilingualSOAPGenerator:
    return MultilingualSOAPGenerator(config=config)
