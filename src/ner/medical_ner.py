"""
Named Entity Recognition (NER) for Medical/Clinical Entities

Uses open-source models:
- IndicNER (AI4Bharat) - for Indian languages
- BioBERT-NER - for medical entities
- Clinical-BERT - for clinical text

Now includes comprehensive Marathi regex patterns for rule-based extraction.
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import re


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
        
        # Comprehensive Marathi regex patterns for rule-based extraction
        self.marathi_patterns = {
            "SYMPTOM": [
                # Sleep issues
                r"(निद्रानाश|झोप\s+(?:येत\s+नाही|नीट\s+होत\s+नाही|कमी|व्यत्यय|समस्या))",
                r"(रात्री\s+झोप\s+(?:घेणे|लागणे))",
                r"(उशिरा\s+झोपतो|उशिरा\s+झोपणे)",
                # Fatigue / energy
                r"(थकवा|थकलेलो|थकलेली|कमी\s+उर्जा|ऊर्जा\s+कमी)",
                # Appetite
                r"(भूक\s+(?:कमी|नाही|लागत\s+नाही)|जेवण\s+(?:कमी|नाही))",
                # Concentration
                r"(एकाग्रता\s+(?:कमी|समस्या|नाही)|लक्ष\s+(?:लागत\s+नाही|कमी|कमतरता))",
                r"(लक्ष\s+कमतरता\s+विकार)",
                # Suicidal
                r"(आत्महत्या(?:चे\s+विचार)?|स्वतःला\s+इजा|जगणे\s+नको)",
                # Somatic
                r"(डोकेदुखी|छातीत\s+दुखणे|पोटदुखी|श्वास\s+(?:घेणे\s+कठीण|लागणे))",
                # Panic
                r"(भयग्रस्त\s+झटका|घाबरणे|धडधड)",
            ],
            "EMOTION": [
                r"(नैराश्य(?:ाचे|ाने)?)",
                r"(चिंता(?:ग्रस्त)?|काळजी(?:\s+वाटते)?)",
                r"(ताण(?:\s+आहे|\s+वाटतो)?)",
                r"(दुःख(?:ी)?|उदास|मन\s+(?:खिन्न|जड))",
                r"(राग(?:\s+येतो|\s+नियंत्रण)?|चिडचिड(?:ेपणा)?)",
                r"(भीती(?:\s+वाटते)?|घाबरतो|घाबरते)",
                r"(लाज(?:\s+वाटली|\s+वाटते)?|लाजाळू)",
                r"(अपराध(?:बोध|ी\s+वाटणे))",
                r"(निराशा|निरुत्साह)",
                r"(एकटेपणा|एकटे\s+(?:वाटते|असणे))",
                r"(आनंद(?:ी)?|उत्साह(?:ी)?|समाधान(?:ी)?)",
                r"(अस्वस्थ(?:ता)?|बेचैन)",
            ],
            "DURATION": [
                r"(\d+\s+(?:दिवसांपूर्वी|आठवड्यांपूर्वी|महिन्यांपूर्वी|वर्षांपूर्वी))",
                r"(\d+\s+(?:दिवस|आठवडे|महिने|वर्षे)\s+(?:झाले|पासून))",
                r"(महिन्यातून\s+(?:एकदा|दोनदा|तीनदा|\d+\s+वेळा?))",
                r"(आठवड्यातून\s+(?:एकदा|दोनदा|\d+\s+वेळा?))",
                r"(नेहमी|नेहमीच|सतत|सर्व\s+वेळ)",
                r"(कधीकधी|कधी\s+कधी|अधूनमधून)",
                r"(क्वचित(?:च)?|कधीच\s+नाही|बऱ्याच\s+वेळा)",
                r"(अलीकडे|अलीकडील|गेल्या\s+काही\s+(?:दिवसांत|महिन्यांत))",
            ],
            "SEVERITY": [
                r"(सौम्य\s+(?:लक्षणे|समस्या|स्थिती))",  # Mild symptoms/condition
                r"(मध्यम\s+(?:लक्षणे|समस्या|तीव्रता))",  # Moderate symptoms
                r"(तीव्र\s+(?:लक्षणे|समस्या|नैराश्य|चिंता))",  # Severe symptoms
                r"(गंभीर\s+(?:परिस्थिती|स्थिती|समस्या))",  # Serious condition
                r"(वाढत\s+(?:आहे|चालले)|आणखी\s+(?:वाईट|त्रासदायक))",
                r"(सुधारत\s+(?:आहे|आहोत)|बरे\s+होत\s+(?:आहे|आहोत))",
            ],
            "TREATMENT": [
                r"(मनोचिकित्स(?:क|ा|ेकडे))",
                r"(समुपदेशन|समुपदेशक)",
                r"(थेरपी|थेरपिस्ट)",
                r"(औषध(?:े|ोपचार|े\s+घेतो|े\s+घेते)?)",
                r"(डॉक्टर(?:ांकडे|ांना)?)",
                r"(उपचार(?:\s+घेतो|\s+घेते|\s+सुरू)?)",
                r"(रुग्णालय|हॉस्पिटल)",
            ],
            "LIFESTYLE": [
                r"(व्यायाम(?:\s+करतो|\s+करते)?)",
                r"(झोपणे|झोपतो|झोपते|उशिरा\s+झोपणे)",
                r"(प्रवास(?:\s+करतो|\s+करते|\s+करायला)?)",
                r"(गोल्फ|पोहणे|पोहतो)",
                r"(मित्र(?:ांसोबत)?|मैत्रिणींसोबत)",
                r"(कॉफी|बिअर|मद्यपान|धूम्रपान)",
                r"(मैफिल|संगीत\s+(?:ऐकणे|वाजवणे))",
            ],
        }
        
        # Mental health specific patterns (English + basic Marathi)
        self.mental_health_patterns = {
            'SYMPTOM': [
                'depression', 'anxiety', 'stress', 'insomnia', 'fatigue',
                'sadness', 'hopelessness', 'irritability', 'panic',
                'mood swings', 'lack of interest', 'poor concentration',
                'appetite loss', 'sleep disturbance', 'low energy', 'lack of motivation',
                # Marathi clinical terms only
                'नैराश्य', 'चिंता', 'ताण', 'थकवा', 'निद्रानाश', 'भूक कमी',
            ],
            'SEVERITY': [
                'mild depression', 'moderate anxiety', 'severe stress',
                'minimal symptoms', 'extreme distress',
                'significant impairment', 'chronic condition', 'acute episode',
                # Marathi - only when followed by clinical context
                'सौम्य लक्षणे', 'मध्यम नैराश्य', 'तीव्र चिंता', 'गंभीर स्थिती',
            ],
            'DURATION': [
                # Only temporal patterns with clinical context - removed standalone time words
            ],
            'MEDICATION': [
                'antidepressant', 'anxiolytic', 'ssri', 'snri',
                'therapy', 'counseling', 'medication', 'psychotherapy',
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
                if not isinstance(results, list):
                    results = []

                for r in results:
                    if not isinstance(r, dict):
                        continue

                    word = r.get("word")
                    entity_group = r.get("entity_group")
                    start = r.get("start")
                    end = r.get("end")
                    score = r.get("score")

                    if not isinstance(word, str) or not isinstance(entity_group, str):
                        continue
                    if not isinstance(start, int) or not isinstance(end, int):
                        continue

                    if isinstance(score, (int, float, str)):
                        try:
                            confidence = float(score)
                        except ValueError:
                            confidence = 0.0
                    else:
                        confidence = 0.0

                    entities.append(Entity(
                        text=word,
                        label=entity_group,
                        start=start,
                        end=end,
                        confidence=confidence,
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
        """
        Rule-based entity extraction for mental health terms
        Now supports both simple keyword matching AND Marathi regex patterns
        """
        entities = []
        text_lower = text.lower()
        
        # 1. Simple keyword matching (existing logic)
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
        
        # 2. Regex-based matching for Marathi patterns
        for label, regex_patterns in self.marathi_patterns.items():
            for pattern in regex_patterns:
                try:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        matched_text = match.group(0)
                        entities.append(Entity(
                            text=matched_text,
                            label=label,
                            start=match.start(),
                            end=match.end(),
                            confidence=0.95  # Higher confidence for regex matches
                        ))
                except re.error as e:
                    print(f"⚠️ Regex error in pattern '{pattern}': {e}")
        
        return entities
    
    def extract_from_conversation(self, turns: List[Dict]) -> Dict[str, List[Entity]]:
        """
        Extract entities from a conversation
        
        Now handles BOTH:
        - 'text' field (Marathi conversation)
        - 'text_en' field (English translation)
        
        Args:
            turns: List of conversation turns with 'role'/'speaker' and 'text'/'text_en'
            
        Returns:
            Dict with 'patient' and 'doctor' entity lists
        """
        patient_entities = []
        doctor_entities = []
        
        for turn in turns:
            # Get role (support both 'role' and 'speaker' fields)
            role = turn.get('role', turn.get('speaker', '')).lower()
            
            # Get text - prioritize Marathi (text), fallback to English (text_en)
            # Process BOTH if available for maximum entity coverage
            texts_to_process = []
            
            marathi_text = turn.get('text', '')
            english_text = turn.get('text_en', '')
            
            if marathi_text:
                texts_to_process.append(('marathi', marathi_text))
            if english_text:
                texts_to_process.append(('english', english_text))
            
            # Extract entities from all available text versions
            for lang, text in texts_to_process:
                if not text:
                    continue
                
                entities = self.extract_entities(text)
                
                # Tag entities with language source
                for entity in entities:
                    entity.text = entity.text + f" [{lang}]"
                
                if 'patient' in role or 'रुग्ण' in role:
                    patient_entities.extend(entities)
                elif 'therapist' in role or 'doctor' in role or 'थेरपिस्ट' in role:
                    doctor_entities.extend(entities)
                else:
                    # Default: assume patient if role unclear
                    patient_entities.extend(entities)
        
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
