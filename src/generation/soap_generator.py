import json
import re
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class SOAPNote:
    """Structured Clinical Note with 10-section dictionary"""
    sections: Dict[str, str] 
    raw_output: str = ""
    
    def to_dict(self) -> Dict:
        return {**self.sections, 'raw': self.raw_output}

class SOAPGenerator:
    """Generates 10-section clinical notes via Ollama (Gemma 2)"""

    PROMPT_TEMPLATE = """You are a professional senior psychiatrist. Summarize the transcript into 10 SPECIFIC clinical subsections. 
Use ONLY evidence from the transcript. If info is missing, write "नाही (None)".

PHQ-8: {phq8_score}/24 | Severity: {severity} | Gender: {gender}

TRANSCRIPT:
{conversation}

FORMAT YOUR RESPONSE EXACTLY AS FOLLOWS (Keep the bracketed headers):

[CHIEF_COMPLAINT]: Primary symptoms or reason for visit.
[HPI]: History of present illness and recent emotional triggers.
[TRAUMA_HISTORY]: Past trauma, significant life events, or deep regrets.
[PSYCHOSOCIAL]: Family, upbringing, and social support system.
[FUNCTIONAL_STATUS]: Hobbies, education, work, and daily activities.
[MEDICAL_HISTORY]: Physical illnesses or medical conditions.
[PAST_PSYCH_HISTORY]: Previous psychiatric treatment or diagnoses.
[BIOLOGICAL]: Observations on sleep, appetite, and energy levels.
[MSE]: Observed behavior, speech, mood, and thought process.
[PLAN]: Treatment plan, therapy recommendations, and safety plan.
"""

    SECTION_HEADERS = {
        'cc':           re.compile(r'\[CHIEF_COMPLAINT\]', re.IGNORECASE),
        'hpi':          re.compile(r'\[HPI\]', re.IGNORECASE),
        'trauma':       re.compile(r'\[TRAUMA_HISTORY\]', re.IGNORECASE),
        'psychosocial': re.compile(r'\[PSYCHOSOCIAL\]', re.IGNORECASE),
        'functional':   re.compile(r'\[FUNCTIONAL_STATUS\]', re.IGNORECASE),
        'medical':      re.compile(r'\[MEDICAL_HISTORY\]', re.IGNORECASE),
        'past_psych':   re.compile(r'\[PAST_PSYCH_HISTORY\]', re.IGNORECASE),
        'biological':   re.compile(r'\[BIOLOGICAL\]', re.IGNORECASE),
        'mse':          re.compile(r'\[MSE\]', re.IGNORECASE),
        'plan':         re.compile(r'\[PLAN\]', re.IGNORECASE),
    }

    def __init__(self, model: str = "gemma2:2b", ollama_url: str = "http://localhost:11434"):
        self.model = model
        self.ollama_url = ollama_url
        self.api_endpoint = f"{ollama_url}/api/generate"

    def generate(self, conversation: str, phq8_score: int = 0, severity: str = "unknown", gender: str = "unknown") -> SOAPNote:
        clean_conversation = self._prepare_conversation(conversation)
        prompt = self.PROMPT_TEMPLATE.format(
            conversation=clean_conversation, phq8_score=phq8_score, severity=severity, gender=gender
        )
        raw_output = ""
        try:
            response = requests.post(self.api_endpoint, json={
                "model": self.model, "prompt": prompt, "stream": False,
                "options": {"temperature": 0.2, "num_ctx": 4096}
            }, timeout=300)
            raw_output = response.json().get("response", "").strip()
        except Exception as e:
            print(f"❌ LLM Error: {e}")
        return self._parse_soap(raw_output)

    def _prepare_conversation(self, conversation: str, max_chars: int = 7000) -> str:
        if not conversation: return ""
        lines = []
        for l in conversation.splitlines():
            clean = l.strip()
            if clean: lines.append(clean)
        return "\n".join(lines)[:max_chars]

    def _parse_soap(self, text: str) -> SOAPNote:
        parsed = {k: "माहिती उपलब्ध नाही." for k in self.SECTION_HEADERS.keys()}
        lowered = text.lower()
        indices = []
        for key, pattern in self.SECTION_HEADERS.items():
            match = pattern.search(lowered)
            if match: indices.append((key, match.start(), match.end()))
        indices.sort(key=lambda x: x[1])
        for i, (key, start, end) in enumerate(indices):
            next_start = indices[i+1][1] if i+1 < len(indices) else len(text)
            content = text[end:next_start].strip()
            content = re.sub(r'^[:\s*#-]+', '', content).strip()
            if content: parsed[key] = content
        return SOAPNote(sections=parsed, raw_output=text)

def get_soap_generator(model: str = "gemma2:2b", ollama_url: str = "http://localhost:11434") -> SOAPGenerator:
    return SOAPGenerator(model=model, ollama_url=ollama_url)