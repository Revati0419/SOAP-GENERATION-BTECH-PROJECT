"""
Named Entity Recognition (NER) for Medical/Clinical Entities

Uses open-source models:
- IndicNER (AI4Bharat) - for Indian languages
- BioBERT-NER - for medical entities
- Clinical-BERT - for clinical text
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Entity:
    """Represents an extracted entity"""
    text: str
    label: str
    start: int
    end: int
    confidence: float


class MedicalNER:
    """
    Medical Named Entity Recognition using open-source models
    
    Extracts:
    - Symptoms (SYMPTOM)
    - Medications (MEDICATION)
    - Conditions (CONDITION)
    - Body parts (BODY_PART)
    - Duration (DURATION)
    - Severity (SEVERITY)
    """
    
    def __init__(self, model_name: str = "d4data/biomedical-ner-all",
                 device: str = "cpu"):
        """
        Initialize NER model
        
        Args:
            model_name: HuggingFace model name
                - "d4data/biomedical-ner-all" (recommended)
                - "alvaroalon2/biobert_diseases_ner"
                - "ai4bharat/IndicNER" (for Indian languages)
            device: "cpu" or "cuda"
        """
        self.model_name = model_name
        self.device = device
        self.ner_pipeline = None
        self._loaded = False
        
        # Mental health specific patterns
        self.mental_health_patterns = {
            'SYMPTOM': [
                'depression', 'anxiety', 'stress', 'insomnia', 'fatigue',
                'sadness', 'hopelessness', 'irritability', 'panic',
                'mood swings', 'lack of interest', 'concentration',
                'appetite', 'sleep', 'energy', 'motivation',
                # Marathi terms
                'नैराश्य', 'चिंता', 'ताण', 'थकवा', 'झोप', 'भूक',
            ],
            'SEVERITY': [
                'mild', 'moderate', 'severe', 'minimal', 'extreme',
                'slight', 'significant', 'chronic', 'acute',
                # Marathi
                'सौम्य', 'मध्यम', 'तीव्र', 'गंभीर',
            ],
            'DURATION': [
                'days', 'weeks', 'months', 'years', 'daily', 'weekly',
                'constantly', 'sometimes', 'often', 'rarely',
                # Marathi
                'दिवस', 'आठवडे', 'महिने', 'वर्षे', 'रोज', 'कधीकधी',
            ],
            'MEDICATION': [
                'antidepressant', 'anxiolytic', 'ssri', 'snri',
                'therapy', 'counseling', 'medication',
            ],
        }
    
    def load_model(self):
        """Lazy load the NER model"""
        if self._loaded:
            return
        
        print(f"Loading NER model: {self.model_name}...")
        
        try:
            from transformers import pipeline
            
            self.ner_pipeline = pipeline(
                "ner",
                model=self.model_name,
                aggregation_strategy="simple",
                device=0 if self.device == "cuda" else -1
            )
            
            self._loaded = True
            print(f"✅ NER model loaded on {self.device}")
            
        except Exception as e:
            print(f"⚠️ Failed to load transformer model: {e}")
            print("Using rule-based NER as fallback")
            self._loaded = True  # Mark as loaded to use fallback
    
    def extract_entities(self, text: str) -> List[Entity]:
        """
        Extract medical entities from text
        
        Args:
            text: Input text
            
        Returns:
            List of Entity objects
        """
        self.load_model()
        
        entities = []
        
        # Use transformer model if available
        if self.ner_pipeline:
            try:
                results = self.ner_pipeline(text)
                for r in results:
                    entities.append(Entity(
                        text=r['word'],
                        label=r['entity_group'],
                        start=r['start'],
                        end=r['end'],
                        confidence=r['score']
                    ))
            except Exception as e:
                print(f"NER error: {e}")
        
        # Add rule-based entities
        rule_entities = self._extract_rule_based(text)
        entities.extend(rule_entities)
        
        # Deduplicate
        seen = set()
        unique_entities = []
        for e in entities:
            key = (e.text.lower(), e.label)
            if key not in seen:
                seen.add(key)
                unique_entities.append(e)
        
        return unique_entities
    
    def _extract_rule_based(self, text: str) -> List[Entity]:
        """Rule-based entity extraction for mental health terms"""
        entities = []
        text_lower = text.lower()
        
        for label, patterns in self.mental_health_patterns.items():
            for pattern in patterns:
                pattern_lower = pattern.lower()
                start = 0
                while True:
                    idx = text_lower.find(pattern_lower, start)
                    if idx == -1:
                        break
                    entities.append(Entity(
                        text=text[idx:idx + len(pattern)],
                        label=label,
                        start=idx,
                        end=idx + len(pattern),
                        confidence=0.9
                    ))
                    start = idx + 1
        
        return entities
    
    def extract_from_conversation(self, turns: List[Dict]) -> Dict[str, List[Entity]]:
        """
        Extract entities from a conversation
        
        Args:
            turns: List of conversation turns with 'role' and 'text'
            
        Returns:
            Dict with 'patient' and 'doctor' entity lists
        """
        patient_entities = []
        doctor_entities = []
        
        for turn in turns:
            role = turn.get('role', '').lower()
            text = turn.get('text', '') or turn.get('text_en', '')
            
            if not text:
                continue
            
            entities = self.extract_entities(text)
            
            if 'patient' in role:
                patient_entities.extend(entities)
            else:
                doctor_entities.extend(entities)
        
        return {
            'patient': patient_entities,
            'doctor': doctor_entities
        }
    
    def summarize_entities(self, entities: List[Entity]) -> Dict[str, List[str]]:
        """
        Group entities by label
        
        Args:
            entities: List of Entity objects
            
        Returns:
            Dict mapping label to list of unique entity texts
        """
        summary = {}
        
        for entity in entities:
            if entity.label not in summary:
                summary[entity.label] = []
            if entity.text.lower() not in [e.lower() for e in summary[entity.label]]:
                summary[entity.label].append(entity.text)
        
        return summary


class IndicNER(MedicalNER):
    """
    NER specifically for Indian languages (Hindi, Marathi, etc.)
    Uses AI4Bharat's IndicNER model
    """
    
    def __init__(self, device: str = "cpu"):
        super().__init__(
            model_name="ai4bharat/IndicNER",
            device=device
        )
        
        # Add Indic language patterns
        self.mental_health_patterns.update({
            'SYMPTOM': self.mental_health_patterns['SYMPTOM'] + [
                # More Marathi terms
                'उदासीनता', 'भीती', 'अस्वस्थता', 'निद्रानाश',
                'दुःख', 'निराशा', 'चिडचिड', 'घबराट',
                # Hindi terms
                'तनाव', 'चिंता', 'थकान', 'नींद', 'भूख',
            ],
            'CONDITION': [
                'depression', 'anxiety disorder', 'ptsd', 'bipolar',
                'नैराश्य विकार', 'चिंता विकार',
            ]
        })


def get_ner_model(model_type: str = "medical", device: str = "cpu"):
    """
    Factory function to get NER model
    
    Args:
        model_type: "medical", "indic", or "rule_based"
        device: "cpu" or "cuda"
    """
    if model_type == "medical":
        return MedicalNER(device=device)
    elif model_type == "indic":
        return IndicNER(device=device)
    elif model_type == "rule_based":
        ner = MedicalNER(device=device)
        ner._loaded = True  # Skip model loading, use rules only
        ner.ner_pipeline = None
        return ner
    else:
        raise ValueError(f"Unknown model type: {model_type}")
