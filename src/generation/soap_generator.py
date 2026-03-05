"""
SOAP Note Generation using Open-Source LLMs

Uses Ollama for local inference with models like:
- Gemma 2 (Google)
- Llama 3.1 (Meta)
- Mistral (Mistral AI)
- OpenHathi (Sarvam AI - Hindi-focused)
"""

import requests
from typing import Dict, List, Optional
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


class SOAPGenerator:
    """
    Generate SOAP notes using open-source LLMs via Ollama
    """
    
    # Clinical SOAP prompt optimized for mental health
    PROMPT_TEMPLATE = """You are an experienced psychiatrist creating a clinical SOAP note from a mental health interview.

Patient Information:
- PHQ-8 Depression Score: {phq8_score}/24
- Severity Classification: {severity}
- Gender: {gender}

Interview Transcript:
{conversation}

Generate a detailed SOAP note following this exact format:

**SUBJECTIVE:**
- Chief Complaint: [Main reason for visit]
- History of Present Illness: [Current symptoms, onset, duration, triggers]
- Mood & Affect: [Patient's described emotional state]
- Sleep Pattern: [Quality, duration, disturbances]
- Appetite: [Changes, weight fluctuation]
- Energy Level: [Fatigue, motivation]
- Concentration: [Focus, memory issues]
- Social Functioning: [Relationships, work, daily activities]
- Suicidal/Self-harm Ideation: [Present/Absent, if present - plan, intent]
- Substance Use: [Alcohol, drugs, medications]

**OBJECTIVE:**
- Appearance: [Grooming, hygiene, dress]
- Behavior: [Psychomotor activity, eye contact, cooperation]
- Speech: [Rate, rhythm, volume, coherence]
- Mood: [Patient's stated mood]
- Affect: [Observed emotional expression - range, congruence]
- Thought Process: [Logical, organized, tangential, circumstantial]
- Thought Content: [Delusions, obsessions, phobias]
- Perception: [Hallucinations - auditory, visual]
- Cognition: [Orientation, attention, memory]
- Insight & Judgment: [Awareness of illness, decision-making]
- PHQ-8 Score: {phq8_score} ({severity})

**ASSESSMENT:**
- Primary Diagnosis: [DSM-5 diagnosis with code if applicable]
- Differential Diagnoses: [Other considerations]
- Severity: {severity}
- Risk Assessment: [Suicide risk - low/moderate/high, protective factors]
- Contributing Factors: [Psychosocial stressors, medical conditions]

**PLAN:**
- Psychotherapy: [Type - CBT, DBT, supportive; frequency]
- Pharmacotherapy: [Medications if indicated]
- Safety Plan: [If needed - crisis contacts, coping strategies]
- Lifestyle Modifications: [Sleep hygiene, exercise, social support]
- Follow-up: [Next appointment timing]
- Referrals: [If needed - specialist, support groups]

Be specific and clinically accurate based on the interview content. Do not include information not mentioned in the interview."""

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
                 temperature: float = 0.3, max_tokens: int = 1500,
                 timeout: int = 180) -> SOAPNote:
        """
        Generate SOAP note from conversation
        
        Args:
            conversation: Formatted conversation text
            phq8_score: PHQ-8 depression score (0-24)
            severity: Severity classification
            gender: Patient gender
            temperature: LLM temperature (lower = more focused)
            max_tokens: Maximum output tokens
            timeout: Request timeout in seconds
            
        Returns:
            SOAPNote object
        """
        # Build prompt
        prompt = self.PROMPT_TEMPLATE.format(
            conversation=conversation,
            phq8_score=phq8_score,
            severity=severity,
            gender=gender
        )
        
        # Call Ollama
        try:
            response = requests.post(
                self.api_endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    }
                },
                timeout=timeout
            )
            response.raise_for_status()
            result = response.json()
            raw_output = result.get('response', '').strip()
            
        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout after {timeout}s")
            raw_output = ""
        except Exception as e:
            print(f"❌ Generation error: {e}")
            raw_output = ""
        
        # Parse sections
        return self._parse_soap(raw_output)
    
    def _parse_soap(self, text: str) -> SOAPNote:
        """Parse SOAP note text into structured sections"""
        sections = {
            'subjective': '',
            'objective': '',
            'assessment': '',
            'plan': ''
        }
        
        current_section = None
        lines = text.split('\n')
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Detect section headers
            if 'subjective' in line_lower and ('**' in line or ':' in line):
                current_section = 'subjective'
                continue
            elif 'objective' in line_lower and ('**' in line or ':' in line):
                current_section = 'objective'
                continue
            elif 'assessment' in line_lower and ('**' in line or ':' in line):
                current_section = 'assessment'
                continue
            elif 'plan' in line_lower and ('**' in line or ':' in line):
                current_section = 'plan'
                continue
            
            if current_section and line.strip():
                sections[current_section] += line.strip() + '\n'
        
        # Clean up
        for key in sections:
            sections[key] = sections[key].strip()
        
        return SOAPNote(
            subjective=sections['subjective'],
            objective=sections['objective'],
            assessment=sections['assessment'],
            plan=sections['plan'],
            raw_output=text
        )
    
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
    
    def _format_conversation(self, turns: List[Dict], max_turns: int = 60) -> str:
        """Format conversation turns"""
        lines = []
        
        if len(turns) > max_turns:
            selected = turns[:max_turns//2] + turns[-max_turns//2:]
        else:
            selected = turns
        
        for turn in selected:
            role = turn.get('role', 'Unknown')
            # Prefer English text for better LLM understanding
            text = turn.get('text_en', '') or turn.get('text', '')
            if text:
                lines.append(f"{role}: {text}")
        
        return "\n".join(lines)


def get_soap_generator(model: str = "gemma2:2b") -> SOAPGenerator:
    """Factory function to get SOAP generator"""
    return SOAPGenerator(model=model)
