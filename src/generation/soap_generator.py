"""
SOAP Note Generation using Open-Source LLMs

Uses Ollama for local inference with models like:
- Gemma 2 (Google)
- Llama 3.1 (Meta)
- Mistral (Mistral AI)
- OpenHathi (Sarvam AI - Hindi-focused)
"""

import json
import re
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class SOAPNote:
    """Structured SOAP Note"""
    subjective: str
    objective: str
    assessment: str
    plan: str
    raw_output: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'subjective': self.subjective,
            'objective': self.objective,
            'assessment': self.assessment,
            'plan': self.plan,
            'raw': self.raw_output
        }

    def to_parametric_dict(self) -> Dict[str, Dict[str, str]]:
        """Return a subsection-wise structured view of SOAP content."""
        parametric = {
            "subjective": self._extract_subjective_params(self.subjective),
            "objective": self._extract_objective_params(self.objective),
            "assessment": self._extract_assessment_params(self.assessment),
            "plan": self._extract_plan_params(self.plan),
        }
        return self._ensure_parametric_defaults(parametric)

    @staticmethod
    def _ensure_parametric_defaults(parametric: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
        """Guarantee all subsection fields are non-empty for stable API/UI usage."""
        default = "- Not clearly elicited from interview."
        for section in ("subjective", "objective", "assessment", "plan"):
            values = parametric.get(section, {})
            for field, value in values.items():
                if not isinstance(value, str) or not value.strip():
                    values[field] = default
            parametric[section] = values
        return parametric

    @staticmethod
    def _extract_subjective_params(text: str) -> Dict[str, str]:
        return {
            "chief_complaint": SOAPNote._extract_by_aliases(text, ["chief complaint", "mukhya takrar", "मुख्य तक्रार"]),
            "hpi": SOAPNote._extract_by_aliases(text, ["history of present illness", "hpi", "सध्याच्या आजाराचा इतिहास"]),
            "trauma_history": SOAPNote._extract_by_aliases(text, ["trauma history", "आघाताचा इतिहास"]),
            "psychosocial_history": SOAPNote._extract_by_aliases(text, ["psychosocial history", "मनोसामाजिक इतिहास"]),
            "functional_status": SOAPNote._extract_by_aliases(text, ["functional status", "कार्यक्षम स्थिती"]),
        }

    @staticmethod
    def _extract_objective_params(text: str) -> Dict[str, str]:
        return {
            "medical_history": SOAPNote._extract_by_aliases(text, ["medical history", "वैद्यकीय इतिहास"]),
            "past_psych_history": SOAPNote._extract_by_aliases(text, ["past psychiatric history", "पूर्व मनोरुग्ण इतिहास"]),
            "biological_observations": SOAPNote._extract_by_aliases(text, ["biological observations", "जैविक निरीक्षणे"]),
            "mental_status_exam": SOAPNote._extract_by_aliases(text, ["mental status exam", "मानसिक स्थिती तपासणी"]),
            "structured_scores": SOAPNote._extract_by_aliases(text, ["structured scores", "phq-8", "phq8"]),
        }

    @staticmethod
    def _extract_assessment_params(text: str) -> Dict[str, str]:
        return {
            "diagnostic_formulation": SOAPNote._extract_by_aliases(text, ["diagnostic formulation", "निदान"]),
            "risk_formulation": SOAPNote._extract_by_aliases(text, ["risk formulation", "जोखीम मूल्यांकन"]),
            "contributing_factors": SOAPNote._extract_by_aliases(text, ["key contributing factors", "contributing factors", "योगदान देणारे घटक"]),
        }

    @staticmethod
    def _extract_plan_params(text: str) -> Dict[str, str]:
        return {
            "treatment_safety_plan": SOAPNote._extract_by_aliases(text, ["treatment & safety plan", "treatment and safety plan", "उपचार आणि सुरक्षा योजना"]),
            "therapy_plan": SOAPNote._extract_by_aliases(text, ["therapy plan", "मानसोपचार योजना"]),
            "medication_considerations": SOAPNote._extract_by_aliases(text, ["medication considerations", "औषधोपचार"]),
            "followup_monitoring": SOAPNote._extract_by_aliases(text, ["follow-up & monitoring", "follow up & monitoring", "follow-up", "पाठपुरावा"]),
        }

    @staticmethod
    def _normalize_heading(line: str) -> str:
        cleaned = line.strip().strip("*")
        cleaned = cleaned.rstrip(":").strip().lower()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    @staticmethod
    def _parse_section_pairs(text: str) -> List[Tuple[str, List[str]]]:
        """Parse section text into (heading, bullet-lines) pairs."""
        pairs: List[Tuple[str, List[str]]] = []
        current_heading: Optional[str] = None
        current_lines: List[str] = []

        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.endswith(":") and not line.startswith("-"):
                if current_heading is not None:
                    pairs.append((current_heading, current_lines))
                current_heading = SOAPNote._normalize_heading(line)
                current_lines = []
                continue
            if current_heading is None:
                continue
            cleaned_line = line
            if cleaned_line.startswith("-"):
                cleaned_line = "- " + cleaned_line.lstrip("-").strip()
            current_lines.append(cleaned_line)

        if current_heading is not None:
            pairs.append((current_heading, current_lines))

        return pairs

    @staticmethod
    def _extract_by_aliases(text: str, aliases: List[str]) -> str:
        """Extract subsection content by matching heading aliases."""
        default = "- Not clearly elicited from interview."
        if not text or not text.strip():
            return default

        normalized_aliases = [re.sub(r"\s+", " ", a.strip().lower()) for a in aliases]
        for heading, lines in SOAPNote._parse_section_pairs(text):
            if any(alias in heading for alias in normalized_aliases):
                value = "\n".join(lines).strip()
                return value or default

        return default


class SOAPGenerator:
    """
    Generate SOAP notes using open-source LLMs via Ollama
    """
    
    # Strongly constrained clinical prompt for better factuality and structure.
    PROMPT_TEMPLATE = """You are a psychiatrist writing a professional, detailed SOAP note.

PHQ-8: {phq8_score}/24 | Severity: {severity} | Gender: {gender}

TRANSCRIPT:
{conversation}

Rules:
1) Use ONLY evidence from transcript. Do NOT invent symptoms, diagnosis details, or risk factors.
2) If information is missing, write "Not clearly elicited from interview.".
3) Keep bullets clinically neutral, specific, non-repetitive, and slightly descriptive.
4) Output ONLY the four SOAP sections below. No markdown fences, no preface.
5) Under each SOAP section, cover the requested subsection points.
6) Do NOT use markdown headings like ###.
7) Keep each clinical point on a new line and prefix each point with "- ".

**SUBJECTIVE:**
मुख्य तक्रार (Chief Complaint):
- Primary reason for visit in patient's own words.
सध्याच्या आजाराचा इतिहास (HPI):
- Symptom timeline, progression, triggers, relieving factors.
आघाताचा इतिहास (Trauma History):
- Past trauma, grief, deep regrets (if mentioned).
मनोसामाजिक इतिहास (Psychosocial History):
- Family, upbringing, relationships, social support.
कार्यक्षम स्थिती (Functional Status):
- Daily activities, hobbies, work/study impact.

**OBJECTIVE:**
वैद्यकीय इतिहास (Medical History):
- Relevant physical illnesses, comorbidities, medications.
पूर्व मनोरुग्ण इतिहास (Past Psychiatric History):
- Previous diagnoses, treatments, admissions, adherence.
जैविक निरीक्षणे (Biological Observations):
- Sleep, appetite, energy, somatic/psychomotor observations.
मानसिक स्थिती तपासणी (Mental Status Exam):
- Appearance, behavior, speech, mood/affect, thought process/content, insight/judgment.
Structured Scores:
- PHQ-8: {phq8_score} ({severity})

**ASSESSMENT:**
Diagnostic Formulation:
- Most likely diagnosis and clinical reasoning from transcript evidence.
Risk Formulation:
- Suicide/self-harm/violence risk level, risk factors, protective factors.
Key Contributing Factors:
- Biological, psychological, social maintaining factors.

**PLAN:**
उपचार आणि सुरक्षा योजना (Treatment & Safety Plan):
- Immediate next steps and crisis/safety guidance.
Therapy Plan:
- Modality/focus (e.g., CBT, supportive therapy), short-term goals.
Medication Considerations:
- If indicated, evaluation/referral and adherence counseling.
Follow-up & Monitoring:
- Timeframe, warning signs, measurable review checkpoints."""

    SECTION_HEADERS = {
        'subjective': re.compile(r'(?:\*\*)?\s*subjective\s*:?\s*(?:\*\*)?', re.IGNORECASE),
        'objective': re.compile(r'(?:\*\*)?\s*objective\s*:?\s*(?:\*\*)?', re.IGNORECASE),
        'assessment': re.compile(r'(?:\*\*)?\s*assessment\s*:?\s*(?:\*\*)?', re.IGNORECASE),
        'plan': re.compile(r'(?:\*\*)?\s*plan\s*:?\s*(?:\*\*)?', re.IGNORECASE),
    }

    SHORT_SECTION_HEADERS = {
        'subjective': re.compile(r'^\s*(?:s|subj)\s*[:\-]\s*$', re.IGNORECASE),
        'objective': re.compile(r'^\s*(?:o|obj)\s*[:\-]\s*$', re.IGNORECASE),
        'assessment': re.compile(r'^\s*(?:a|assess?)\s*[:\-]\s*$', re.IGNORECASE),
        'plan': re.compile(r'^\s*(?:p|pln)\s*[:\-]\s*$', re.IGNORECASE),
    }

    CLINICAL_HEADING_MAP = {
        'subjective': [
            'chief complaint',
            'history of present illness',
            'hpi',
            'review of systems',
        ],
        'objective': [
            'physical examination',
            'physical exam',
            'examination',
            'results',
            'investigations',
            'labs',
            'imaging',
            'vitals',
        ],
        'assessment': [
            'assessment',
            'impression',
            'diagnosis',
            'diagnostic impression',
            'assessment and plan',
        ],
        'plan': [
            'plan',
            'treatment plan',
            'recommendations',
            'follow-up',
            'follow up',
        ],
    }

    def __init__(self, model: str = "gemma2:2b", 
                 ollama_url: str = "http://localhost:11434"):
        """
        Initialize SOAP generator
        
        Args:
            model: Ollama model name
            ollama_url: Ollama API URL
        """
        self.model = model
        self.ollama_url = ollama_url
        self.api_endpoint = f"{ollama_url}/api/generate"
    
    def check_ollama(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def generate(self, conversation: str, phq8_score: int = 0,
                 severity: str = "unknown", gender: str = "unknown",
                 temperature: float = 0.3,
                 timeout: int = 300) -> SOAPNote:
        """Generate SOAP note from conversation via Ollama (streaming)."""
        conversation = self._prepare_conversation(conversation)
        prompt = self.PROMPT_TEMPLATE.format(
            conversation=conversation,
            phq8_score=phq8_score,
            severity=severity,
            gender=gender
        )

        raw_output = ""
        try:
            # stream=True: tokens arrive as generated, no buffering wait
            # NO num_predict: Gemma stops when it naturally finishes the note
            # (forcing num_predict caused padding to the limit → timeout)
            response = requests.post(
                self.api_endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": min(temperature, 0.2),
                        "top_p": 0.9,
                        "repeat_penalty": 1.08,
                        "num_ctx": 2048,   # cap context window → faster attention
                        "num_thread": 4,   # use 4 CPU cores
                    }
                },
                timeout=timeout,
                stream=True,
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        raw_output += chunk.get("response", "")
                        if chunk.get("done"):
                            break
                    except Exception:
                        pass
            raw_output = raw_output.strip()

        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout after {timeout}s — parsing partial output")
        except Exception as e:
            print(f"❌ Generation error: {e}")

        return self._parse_soap(raw_output)

    def _prepare_conversation(self, conversation: str, max_chars: int = 7000) -> str:
        """Normalize transcript to reduce ASR noise and repeated lines before prompting."""
        if not conversation:
            return ""

        cleaned_lines: List[str] = []
        prev_norm = ""

        for raw_line in conversation.splitlines():
            line = re.sub(r'\s+', ' ', raw_line).strip()
            if not line:
                continue

            # Keep role-labeled dialogue and useful context lines only.
            if ':' in line:
                role, text = line.split(':', 1)
                text = text.strip()
                if len(text) < 2:
                    continue
                line = f"{role.strip()}: {text}"

            norm = re.sub(r'[^a-z0-9\u0900-\u097F ]+', '', line.lower())
            if norm == prev_norm:
                continue
            prev_norm = norm
            cleaned_lines.append(line)

        merged = '\n'.join(cleaned_lines)
        if len(merged) > max_chars:
            head = merged[: max_chars // 2]
            tail = merged[-(max_chars // 2):]
            merged = head + "\n...[trimmed for length]...\n" + tail

        return merged
    
    def _parse_soap(self, text: str) -> SOAPNote:
        """Parse SOAP note text into structured sections with robust fallbacks."""
        sections = {'subjective': '', 'objective': '', 'assessment': '', 'plan': ''}

        if not text:
            return SOAPNote('', '', '', '', '')

        # Attempt JSON parse if model returned JSON-like output.
        parsed_json = self._try_parse_json(text)
        if parsed_json:
            for key in sections:
                val = parsed_json.get(key, '')
                sections[key] = self._sanitize_section(str(val))
            self._ensure_non_empty_sections(sections)
            return SOAPNote(
                subjective=sections['subjective'],
                objective=sections['objective'],
                assessment=sections['assessment'],
                plan=sections['plan'],
                raw_output=text,
            )

        # Header-based extraction fallback.
        lowered = text.lower()
        indices = {}
        for name, pattern in self.SECTION_HEADERS.items():
            match = pattern.search(lowered)
            if match:
                indices[name] = match.start()

        if indices:
            ordered = sorted(indices.items(), key=lambda kv: kv[1])
            for i, (name, start_idx) in enumerate(ordered):
                end_idx = ordered[i + 1][1] if i + 1 < len(ordered) else len(text)
                chunk = text[start_idx:end_idx]
                # Remove header line itself
                chunk = re.sub(r'^(?:\*\*)?\s*' + name + r'\s*:?\s*(?:\*\*)?\s*', '', chunk, flags=re.IGNORECASE)
                sections[name] = self._sanitize_section(chunk)
        else:
            sections = self._parse_by_line_headers(text)

        # If one or more sections are still empty, recover from line-wise parser.
        if any(not v.strip() for v in sections.values()):
            recovered = self._parse_by_line_headers(text)
            for key in sections:
                if not sections[key].strip() and recovered.get(key, '').strip():
                    sections[key] = recovered[key]

        # Additional fallback for clinical-note style outputs without SOAP headers.
        if any(not v.strip() for v in sections.values()):
            recovered = self._parse_by_clinical_headings(text)
            for key in sections:
                if not sections[key].strip() and recovered.get(key, '').strip():
                    sections[key] = recovered[key]

        # Last fallback: keep full text in subjective so user sees output instead of blanks.
        if not any(v.strip() for v in sections.values()):
            sections['subjective'] = self._sanitize_section(text)

        self._ensure_non_empty_sections(sections)
        
        return SOAPNote(
            subjective=sections['subjective'],
            objective=sections['objective'],
            assessment=sections['assessment'],
            plan=sections['plan'],
            raw_output=text
        )

    def _try_parse_json(self, text: str) -> Optional[Dict[str, str]]:
        """Try to parse dict-like model output containing SOAP keys."""
        candidate = text.strip()
        if '{' not in candidate or '}' not in candidate:
            return None
        try:
            start = candidate.find('{')
            end = candidate.rfind('}') + 1
            obj = json.loads(candidate[start:end])
            if isinstance(obj, dict) and any(k in obj for k in ('subjective', 'objective', 'assessment', 'plan')):
                return obj
        except Exception:
            return None
        return None

    def _parse_by_line_headers(self, text: str) -> Dict[str, str]:
        """Parse SOAP sections line-by-line, including short headers like S:/O:/A:/P:."""
        buckets = {'subjective': [], 'objective': [], 'assessment': [], 'plan': []}
        current = None

        lines = text.splitlines()
        for raw in lines:
            line = raw.strip()
            if not line:
                continue

            matched = None
            for name, pattern in self.SECTION_HEADERS.items():
                if pattern.fullmatch(line) or pattern.match(line):
                    matched = name
                    break

            if not matched:
                for name, pattern in self.SHORT_SECTION_HEADERS.items():
                    if pattern.match(line):
                        matched = name
                        break

            if matched:
                current = matched
                continue

            if current:
                buckets[current].append(line)

        return {k: self._sanitize_section('\n'.join(v)) for k, v in buckets.items()}

    def _match_clinical_heading(self, line: str) -> Optional[str]:
        normalized = re.sub(r'[^a-z0-9 ]+', ' ', line.lower()).strip()
        normalized = re.sub(r'\s+', ' ', normalized)

        for section, aliases in self.CLINICAL_HEADING_MAP.items():
            for alias in aliases:
                if normalized == alias or normalized.startswith(alias + ' '):
                    return section
        return None

    def _is_plan_like_line(self, line: str) -> bool:
        low = line.lower()
        plan_terms = [
            'medical treatment',
            'treatment',
            'additional testing',
            'order',
            'patient education',
            'counseling',
            'follow-up',
            'follow up',
            'recommend',
            'referral',
            'monitor',
        ]
        return any(term in low for term in plan_terms)

    def _parse_by_clinical_headings(self, text: str) -> Dict[str, str]:
        """Parse clinical notes that use headings like CHIEF COMPLAINT / HPI / PHYSICAL EXAM."""
        buckets = {'subjective': [], 'objective': [], 'assessment': [], 'plan': []}
        current: Optional[str] = None
        in_assessment_plan_block = False

        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue

            matched = self._match_clinical_heading(line.rstrip(':'))
            if matched:
                current = matched
                in_assessment_plan_block = line.lower().strip().rstrip(':') == 'assessment and plan'
                continue

            if not current:
                continue

            target_section = current
            if in_assessment_plan_block and self._is_plan_like_line(line):
                target_section = 'plan'

            buckets[target_section].append(line)

        return {k: self._sanitize_section('\n'.join(v)) for k, v in buckets.items()}

    def _ensure_non_empty_sections(self, sections: Dict[str, str]) -> None:
        """Guarantee all SOAP fields are non-empty for stable UI rendering."""
        default_text = "- Not clearly elicited from interview."
        for key in ('subjective', 'objective', 'assessment', 'plan'):
            if not sections.get(key, '').strip():
                sections[key] = default_text

    def _sanitize_section(self, text: str) -> str:
        """Remove heading leakage/noise and enforce one clinical point per line without markdown headings."""
        if not text:
            return ""

        # Flatten markdown heading markers from noisy model output.
        text = re.sub(r'\s*#{3,}\s*', '\n', text)
        # Ensure bullet-like separators begin on fresh lines.
        text = re.sub(r'\s+[•●]\s*', '\n- ', text)

        lines = []
        seen = set()
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue

            low = line.lower().strip('*: ')
            if low in {'subjective', 'objective', 'assessment', 'plan'}:
                continue
            if low.startswith('```'):
                continue

            # Remove any residual markdown heading prefix.
            line = re.sub(r'^#{1,6}\s*', '', line).strip()

            is_heading = bool(re.match(r'^[\u0900-\u097FA-Za-z][^\n]{2,120}:$', line))

            # Preserve headings; normalize everything else to bullets
            if not is_heading and not line.startswith('-'):
                line = f"- {line}"
            elif line.startswith('-'):
                line = '- ' + line.lstrip('-').strip()

            dedupe_key = re.sub(r'\s+', ' ', line.lower())
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            lines.append(line)

        return '\n'.join(lines).strip()
    
    def generate_from_session(self, session_data: Dict, 
                               dialect: str = "standard_pune") -> SOAPNote:
        """
        Generate SOAP note from session data
        
        Args:
            session_data: Session dict with 'dialects', 'phq8_score', etc.
            dialect: Which dialect to use
            
        Returns:
            SOAPNote object
        """
        # Get conversation turns
        turns = session_data.get('dialects', {}).get(dialect, [])
        if not turns:
            dialects = session_data.get('dialects', {})
            if dialects:
                dialect = list(dialects.keys())[0]
                turns = dialects[dialect]
        
        if not turns:
            return SOAPNote("", "", "", "", "Error: No conversation found")
        
        # Format conversation
        conversation = self._format_conversation(turns)
        
        # Generate
        return self.generate(
            conversation=conversation,
            phq8_score=session_data.get('phq8_score', 0),
            severity=session_data.get('severity', 'unknown'),
            gender=session_data.get('gender', 'unknown')
        )
    
    def _format_conversation(self, turns: List[Dict], max_turns: int = 40) -> str:
        """Format conversation turns — capped at 40 to keep prompt short on CPU."""
        lines = []

        if len(turns) > max_turns:
            # first 20 + last 20: preserve opening context and recent state
            selected = turns[:max_turns // 2] + turns[-(max_turns // 2):]
        else:
            selected = turns

        for turn in selected:
            role = turn.get('role', 'Unknown')
            # Prefer English text so Gemma doesn't decode Devanagari
            text = turn.get('text_en', '') or turn.get('text', '')
            if text:
                lines.append(f"{role}: {text}")

        return "\n".join(lines)


def get_soap_generator(model: str = "gemma2:2b") -> SOAPGenerator:
    """Factory function to get SOAP generator"""
    return SOAPGenerator(model=model)
