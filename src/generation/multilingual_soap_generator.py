import os
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from .soap_generator import SOAPGenerator, SOAPNote

# ── Data class ─────────────────────────────────────────────────────────────────

@dataclass
class MultilingualSOAPNote:
    """Bilingual note containing 10 sections in English and Target Language"""
    english: SOAPNote
    target_language: SOAPNote
    input_language: str
    target_language_code: str

    def to_dict(self) -> Dict:
        """Returns the dictionary format expected by the API and Frontend"""
        return {
            'soap_english': self.english.to_dict(),
            f'soap_{self.target_language_code}': self.target_language.to_dict(),
            'metadata': {
                'input_language':  self.input_language,
                'target_language': self.target_language_code,
            }
        }

# ── Language detection ──────────────────────────────────────────────────────────

class LanguageDetector:
    """Detect primary language from script composition (Devanagari vs Latin)"""
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
        # If more than 30% is Devanagari, it's an Indian language
        if dev / total > 0.3:
            # Marathi specific characters check
            if 'ळ' in text or 'ऱ' in text or 'चे' in text:
                return 'marathi'
            return 'hindi'
        if lat / total > 0.5:
            return 'english'
        return 'mixed'

    @staticmethod
    def detect_from_turns(turns: List[Dict]) -> str:
        """Detect language by inspecting the first 10 turns."""
        sample = ' '.join([str(t.get('text', '')) for t in turns[:10]])
        return LanguageDetector.detect_language(sample)

# ── Main generator ──────────────────────────────────────────────────────────────

class MultilingualSOAPGenerator:
    """
    Handles Phase 1 (Bilingual) and Phase 2 (Marathi-only) pipelines.
    Now supports 10 clinical subsections.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.soap_generator = SOAPGenerator(
            model=self.config.get('llm_model', 'gemma2:2b')
        )
        self._translator        = None
        self._translator_loaded = False
        self._ner               = None
        self._ner_loaded        = False

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

    def generate_from_session(self, session_data: Dict, dialect: Optional[str] = None, target_lang: Optional[str] = None) -> MultilingualSOAPNote:
        """Full pipeline: handles complex JSON files with multiple turn formats"""
        turns = self._extract_turns(session_data, dialect)
        if not turns:
            empty = SOAPNote({}, "Error: No conversation found")
            return MultilingualSOAPNote(empty, empty, 'unknown', target_lang or 'marathi')

        true_session_lang = LanguageDetector.detect_from_turns(turns)
        has_english = any(str(t.get('text_en', '')).strip() for t in turns[:5])

        if has_english:
            print("📋 Phase 1 pipeline (English source present)")
            conversation = self._format_turns_english(turns)
            gemma_input_lang = 'english'
        else:
            print("📋 Phase 2 pipeline (Marathi-only source)")
            conversation = self._format_turns_marathi(turns)
            gemma_input_lang = true_session_lang

        return self.generate_from_transcript(
            conversation=conversation,
            phq8_score=session_data.get('phq8_score', 0),
            severity=session_data.get('severity', 'unknown'),
            gender=session_data.get('gender', 'unknown'),
            target_lang=target_lang or 'marathi',
            _detected_lang_override=gemma_input_lang,
            _session_lang_override=true_session_lang,
        )

    def generate_from_transcript(self, conversation: str, phq8_score: int = 0, severity: str = "unknown", 
                                  gender: str = "unknown", target_lang: str = "marathi", 
                                  _detected_lang_override: Optional[str] = None, 
                                  _session_lang_override: Optional[str] = None) -> MultilingualSOAPNote:
        
        detected_lang = _detected_lang_override or LanguageDetector.detect_language(conversation)
        session_lang  = _session_lang_override or detected_lang
        
        ner_context = ""
        # Phase 2 logic: If input is Marathi, extract entities and translate to English for Gemma
        if detected_lang in ('marathi', 'hindi', 'mixed'):
            if self.ner:
                try:
                    entities = self.ner.extract_entities(conversation)
                    if entities:
                        ner_context = "\n\nDetected Clinical Entities:\n" + ", ".join([f"{e.label}: {e.text}" for e in entities])
                except: pass
            
            if self.translator:
                try:
                    conversation = self.translator.translate(conversation, source_lang=detected_lang, target_lang='english')
                except: pass

        # 1. Generate the 10-section note in English
        english_soap = self.soap_generator.generate(
            conversation=conversation + ner_context,
            phq8_score=phq8_score,
            severity=severity,
            gender=gender,
        )

        # 2. Translate those 10 sections back to Marathi
        marathi_soap = self._translate_soap(english_soap, target_lang)

        return MultilingualSOAPNote(
            english=english_soap,
            target_language=marathi_soap,
            input_language=session_lang,
            target_language_code=target_lang,
        )

    def _translate_soap(self, english_soap: SOAPNote, target_lang: str) -> SOAPNote:
        """Translates each of the 10 subsections from English to target language"""
        if not self.translator or target_lang == 'english':
            return english_soap

        translated_sections = {}
        for key, content in english_soap.sections.items():
            if content.strip() and "None" not in content and "नाही" not in content:
                try:
                    marathi_text = self.translator.translate(content, 'english', target_lang)
                    translated_sections[key] = marathi_text
                except:
                    translated_sections[key] = content
            else:
                translated_sections[key] = "माहिती उपलब्ध नाही."

        return SOAPNote(sections=translated_sections, raw_output=english_soap.raw_output)

    # ── Helpers for JSON extraction ──────────────────────────────────────────

    def _extract_turns(self, session_data: Dict, dialect: Optional[str]) -> List[Dict]:
        """Supports various JSON schemas: dialects, styles, or flat lists"""
        if dialect and session_data.get('dialects', {}).get(dialect):
            return session_data['dialects'][dialect]
        
        for key in ('dialects', 'styles', 'turns', 'conversation'):
            val = session_data.get(key)
            if isinstance(val, list): return val
            if isinstance(val, dict):
                for sub_val in val.values():
                    if isinstance(sub_val, list): return sub_val
        return []

    def _format_turns_english(self, turns: List[Dict], max_turns: int = 40) -> str:
        sel = turns[:20] + turns[-20:] if len(turns) > max_turns else turns
        return "\n".join([f"{t.get('role', 'Unknown')}: {t.get('text_en', t.get('text', ''))}" for t in sel])

    def _format_turns_marathi(self, turns: List[Dict], max_turns: int = 40) -> str:
        sel = turns[:20] + turns[-20:] if len(turns) > max_turns else turns
        return "\n".join([f"{t.get('role', 'Unknown')}: {t.get('text', t.get('text_en', ''))}" for t in sel])

# ── Factory ─────────────────────────────────────────────────────────────────────

def get_multilingual_soap_generator(config: Optional[Dict] = None) -> MultilingualSOAPGenerator:
    return MultilingualSOAPGenerator(config=config)