#!/usr/bin/env python3
"""
SOAP Note Generator v3 - Complete Open-Source Pipeline
================================================================
Architecture: NER → RAG → LLM → IndicTrans2 → Bilingual SOAP

Components:
1. NER: Extract medical entities (symptoms, emotions, conditions)
2. RAG: Retrieve clinical terminology from knowledge base
3. LLM: Generate English SOAP note (Gemma 2B via Ollama)
4. Translation: English → Marathi (IndicTrans2 or Transformers)
5. Output: Bilingual clinical documentation

Author: BTECH Project Team
Date: March 5, 2026
Version: 3.0 (Fully Open Source)
"""

import json
import os
import sys
import argparse
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import transformers for NER and translation
try:
    from transformers import (
        AutoTokenizer, 
        AutoModelForTokenClassification,
        AutoModelForSeq2SeqLM,
        pipeline
    )
    import torch
except ImportError:
    print("⚠️  Transformers not found. Installing...")
    os.system("pip install transformers torch sentencepiece")
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
    import torch

# Import ChromaDB for RAG
try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    print("⚠️  ChromaDB not found. Installing...")
    os.system("pip install chromadb sentence-transformers")
    import chromadb
    from chromadb.utils import embedding_functions


# ============================================================
# CONFIGURATION
# ============================================================

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma2:2b"

# NER Model Configuration
NER_MODEL = "dslim/bert-base-NER"  # Fallback, replace with IndicNER if available
ENTITY_TYPES = ["SYMPTOM", "EMOTION", "DURATION", "FREQUENCY", "SEVERITY"]

# Translation Model Configuration
TRANSLATION_MODEL = "facebook/mbart-large-50-many-to-many-mmt"  # Fallback for IndicTrans2
SOURCE_LANG = "en_XX"
TARGET_LANG = "mr_IN"  # Marathi

# Clinical SOAP Prompt with Entity Enhancement
SOAP_PROMPT_TEMPLATE = """You are an experienced psychiatrist creating a clinical SOAP note from a mental health interview.

Patient Information:
- PHQ-8 Depression Score: {phq8_score}/24
- Severity Classification: {severity}
- Gender: {gender}

Extracted Medical Entities:
{entities}

Clinical Terminology Context:
{rag_context}

Interview Transcript:
{conversation}

Generate a detailed, clinically accurate SOAP note following this exact format:

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
- Perception: [Hallucitations - auditory, visual]
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

Be specific and clinically accurate. Use the extracted entities and terminology context to enhance clinical precision."""


# ============================================================
# 1. NER: MEDICAL ENTITY EXTRACTION
# ============================================================

class MedicalEntityExtractor:
    """Extract medical entities with rule-based + ML hybrid approach"""
    
    def __init__(self, model_name: str = NER_MODEL):
        print(f"🔧 Loading NER model: {model_name}")
        
        # Medical keyword patterns for mental health
        self.symptom_keywords = [
            'sad', 'sadness', 'depressed', 'depression', 'anxious', 'anxiety',
            'tired', 'fatigue', 'energy', 'sleep', 'sleeping', 'insomnia',
            'appetite', 'eating', 'weight', 'concentration', 'focus',
            'worry', 'nervous', 'irritable', 'angry', 'hopeless', 'worthless',
            'suicidal', 'self-harm', 'crying', 'mood', 'interest', 'pleasure'
        ]
        
        self.emotion_keywords = [
            'happy', 'sad', 'angry', 'frustrated', 'hopeless', 'helpless',
            'guilty', 'ashamed', 'worried', 'scared', 'nervous', 'calm',
            'stressed', 'overwhelmed', 'isolated', 'lonely'
        ]
        
        try:
            self.ner_pipeline = pipeline(
                "ner", 
                model=model_name, 
                grouped_entities=True,
                device=-1  # CPU
            )
            print("✅ NER model loaded successfully")
        except Exception as e:
            print(f"⚠️  NER model loading failed: {e}")
            print("   Using rule-based extraction only...")
            self.ner_pipeline = None
    
    def extract_entities(self, text: str) -> List[Dict]:
        """Extract medical entities using hybrid approach"""
        entities = []
        text_lower = text.lower()
        
        # Rule-based extraction for symptoms
        for symptom in self.symptom_keywords:
            if symptom in text_lower:
                # Find context around the symptom
                idx = text_lower.find(symptom)
                context_start = max(0, idx - 30)
                context_end = min(len(text), idx + len(symptom) + 30)
                context = text[context_start:context_end]
                
                entities.append({
                    'text': symptom,
                    'type': 'SYMPTOM',
                    'score': 0.95,
                    'context': context.strip()
                })
        
        # Extract emotions
        for emotion in self.emotion_keywords:
            if emotion in text_lower and not any(e['text'] == emotion for e in entities):
                entities.append({
                    'text': emotion,
                    'type': 'EMOTION',
                    'score': 0.90,
                    'context': ''
                })
        
        # ML-based extraction (if available)
        if self.ner_pipeline:
            try:
                ml_entities = self.ner_pipeline(text[:512])
                for ent in ml_entities:
                    entities.append({
                        'text': ent['word'],
                        'type': self._map_entity_type(ent['entity_group']),
                        'score': ent['score'],
                        'context': ''
                    })
            except Exception as e:
                pass
        
        # Deduplicate
        seen = set()
        unique_entities = []
        for ent in sorted(entities, key=lambda x: -x['score']):
            key = (ent['text'].lower(), ent['type'])
            if key not in seen:
                seen.add(key)
                unique_entities.append(ent)
        
        return unique_entities[:15]
    
    def _map_entity_type(self, entity_type: str) -> str:
        """Map NER entity types to clinical categories"""
        mapping = {
            'PER': 'PERSON',
            'LOC': 'LOCATION',
            'ORG': 'ORGANIZATION',
            'MISC': 'SYMPTOM'
        }
        return mapping.get(entity_type, entity_type)
    
    def format_entities(self, entities: List[Dict]) -> str:
        """Format entities for display"""
        if not entities:
            return "No specific medical entities extracted."
        
        # Group by type
        by_type = {}
        for ent in entities:
            if ent['type'] not in by_type:
                by_type[ent['type']] = []
            by_type[ent['type']].append(ent)
        
        # Format output
        lines = []
        for ent_type in ['SYMPTOM', 'EMOTION', 'PERSON', 'LOCATION']:
            if ent_type in by_type:
                items = by_type[ent_type]
                lines.append(f"\n**{ent_type}S:**")
                for item in items[:8]:
                    if item.get('context'):
                        lines.append(f"  - {item['text']}: \"{item['context']}\"")
                    else:
                        lines.append(f"  - {item['text']}")
        
        return '\n'.join(lines) if lines else "No specific medical entities extracted."


# ============================================================
# 2. RAG: CLINICAL TERMINOLOGY RETRIEVAL
# ============================================================

class ClinicalRAG:
    """Retrieve relevant clinical terminology using ChromaDB"""
    
    def __init__(self, collection_name: str = "clinical_terms_marathi"):
        print("🔧 Initializing ChromaDB for RAG...")
        try:
            self.client = chromadb.Client()
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            
            # Try to get existing collection or create new
            try:
                self.collection = self.client.get_collection(
                    name=collection_name,
                    embedding_function=self.embedding_fn
                )
                print(f"✅ Loaded existing collection: {collection_name}")
            except:
                self.collection = self.client.create_collection(
                    name=collection_name,
                    embedding_function=self.embedding_fn
                )
                print(f"✅ Created new collection: {collection_name}")
                self._populate_default_terms()
        except Exception as e:
            print(f"⚠️  ChromaDB initialization failed: {e}")
            print("   Continuing without RAG...")
            self.collection = None
    
    def _populate_default_terms(self):
        """Populate collection with default clinical terms"""
        default_terms = [
            {"en": "depression", "mr": "नैराश्य", "type": "condition"},
            {"en": "anxiety", "mr": "चिंता", "type": "condition"},
            {"en": "feeling sad", "mr": "दुःखी वाटणे", "type": "symptom"},
            {"en": "difficulty sleeping", "mr": "झोप येत नाही", "type": "symptom"},
            {"en": "low energy", "mr": "कमी ऊर्जा", "type": "symptom"},
            {"en": "loss of interest", "mr": "रस नसणे", "type": "symptom"},
            {"en": "therapy", "mr": "थेरपी", "type": "treatment"},
            {"en": "counseling", "mr": "समुपदेशन", "type": "treatment"},
            {"en": "medication", "mr": "औषधोपचार", "type": "treatment"},
            {"en": "follow-up", "mr": "पुढचे भेटीचे नियोजन", "type": "plan"}
        ]
        
        if self.collection:
            docs = [t['en'] for t in default_terms]
            metadatas = [{'marathi': t['mr'], 'type': t['type']} for t in default_terms]
            ids = [f"term_{i}" for i in range(len(default_terms))]
            
            self.collection.add(
                documents=docs,
                metadatas=metadatas,
                ids=ids
            )
            print(f"   Added {len(default_terms)} default clinical terms")
    
    def retrieve(self, query: str, top_k: int = 5) -> str:
        """Retrieve relevant clinical terms"""
        if not self.collection:
            return "Clinical terminology database not available."
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            if not results['documents'][0]:
                return "No relevant clinical terms found."
            
            # Format retrieved terms
            formatted = ["Relevant Clinical Terminology:"]
            for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                marathi = metadata.get('marathi', 'N/A')
                formatted.append(f"- {doc} (मराठी: {marathi})")
            
            return "\n".join(formatted)
        except Exception as e:
            print(f"⚠️  RAG retrieval failed: {e}")
            return "Clinical terminology retrieval unavailable."


# ============================================================
# 3. LLM: SOAP NOTE GENERATION
# ============================================================

def generate_with_ollama(prompt: str, model: str = DEFAULT_MODEL, 
                         temperature: float = 0.3, timeout: int = 180) -> str:
    """Generate SOAP note using Ollama API"""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "temperature": temperature,
                "stream": False
            },
            timeout=timeout
        )
        
        if response.status_code == 200:
            return response.json()['response']
        else:
            return f"Error: Ollama API returned status {response.status_code}"
    
    except requests.exceptions.Timeout:
        return "Error: Request timed out"
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to Ollama. Is it running?"
    except Exception as e:
        return f"Error: {str(e)}"


# ============================================================
# 4. TRANSLATION: ENGLISH → MARATHI (IMPROVED)
# ============================================================

class MarathiTranslator:
    """Translate English SOAP to Marathi with manual mappings + model"""
    
    def __init__(self, model_name: str = "facebook/nllb-200-distilled-600M"):
        """Use NLLB model which has better Marathi support"""
        print(f"🔧 Loading translation model: {model_name}")
        
        # Clinical term mappings (high quality manual translations)
        self.term_mappings = {
            # Symptoms
            "sad": "दुःखी",
            "sadness": "दुःख",
            "depression": "नैराश्य",
            "anxiety": "चिंता",
            "feeling sad": "दुःखी वाटणे",
            "low energy": "कमी ऊर्जा",
            "difficulty sleeping": "झोपेत अडचण",
            "sleep problems": "झोपेच्या समस्या",
            "appetite": "भूक",
            "concentration": "एकाग्रता",
            "motivation": "प्रेरणा",
            "energy level": "ऊर्जा पातळी",
            
            # Clinical terms
            "patient": "रुग्ण",
            "diagnosis": "निदान",
            "treatment": "उपचार",
            "therapy": "थेरपी",
            "counseling": "समुपदेशन",
            "medication": "औषध",
            "follow-up": "पुढील भेट",
            "assessment": "मूल्यमापन",
            "symptoms": "लक्षणे",
            
            # SOAP sections
            "SUBJECTIVE": "व्यक्तिनिष्ठ माहिती",
            "OBJECTIVE": "वस्तुनिष्ठ निरीक्षण",
            "ASSESSMENT": "मूल्यमापन",
            "PLAN": "उपचार योजना"
        }
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model.to(self.device)
            print(f"✅ Translation model loaded on {self.device}")
        except Exception as e:
            print(f"⚠️  Translation model loading failed: {e}")
            print("   Using manual term mappings only...")
            self.model = None
            self.tokenizer = None
    
    def translate(self, text: str) -> str:
        """Translate with hybrid approach: mappings + model"""
        if not self.model:
            return self._manual_translate(text)
        
        try:
            # NLLB language codes
            src_lang = "eng_Latn"  # English
            tgt_lang = "mar_Deva"  # Marathi
            
            # Split by lines to preserve structure
            lines = text.split('\n')
            translated_lines = []
            
            for line in lines:
                if not line.strip():
                    translated_lines.append(line)
                    continue
                
                # Check for manual mappings first
                translated_line = line
                for en_term, mr_term in self.term_mappings.items():
                    if en_term.lower() in line.lower():
                        translated_line = translated_line.replace(en_term, mr_term)
                        translated_line = translated_line.replace(en_term.capitalize(), mr_term)
                        translated_line = translated_line.replace(en_term.upper(), mr_term)
                
                # If line still mostly English, translate with model
                if self._is_mostly_english(translated_line):
                    inputs = self.tokenizer(line, return_tensors="pt", padding=True, truncation=True, max_length=256)
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    
                    translated_tokens = self.model.generate(
                        **inputs,
                        forced_bos_token_id=self.tokenizer.convert_tokens_to_ids(tgt_lang),
                        max_length=256
                    )
                    
                    decoded = self.tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]
                    translated_lines.append(decoded)
                else:
                    translated_lines.append(translated_line)
            
            return '\n'.join(translated_lines)
        
        except Exception as e:
            print(f"⚠️  Translation failed: {e}")
            return self._manual_translate(text)
    
    def _is_mostly_english(self, text: str) -> bool:
        """Check if text is mostly English (Latin script)"""
        latin_chars = sum(1 for c in text if ord(c) < 128)
        return latin_chars / max(len(text), 1) > 0.7
    
    def _manual_translate(self, text: str) -> str:
        """Basic translation using manual mappings"""
        translated = text
        for en_term, mr_term in self.term_mappings.items():
            translated = translated.replace(en_term, mr_term)
            translated = translated.replace(en_term.capitalize(), mr_term)
            translated = translated.replace(en_term.upper(), mr_term)
        return translated


# ============================================================
# MAIN PIPELINE
# ============================================================

def format_conversation(turns: List[Dict], max_turns: int = 60) -> str:
    """Format conversation turns for the prompt"""
    lines = []
    if len(turns) > max_turns:
        selected = turns[:max_turns//2] + turns[-max_turns//2:]
    else:
        selected = turns
    
    for turn in selected:
        role = turn.get('role', 'Unknown')
        text = turn.get('text', '') or turn.get('text_en', '') or turn.get('text_mr', '')
        if text and isinstance(text, str):
            lines.append(f"{role}: {text}")
    
    return "\n".join(lines)


def load_session_data(session_id: int, dialect: str = "standard_pune") -> Optional[Dict]:
    """Load translated conversation data"""
    data_dir = Path("data/dialect_marathi")
    
    # Try different file patterns
    possible_files = [
        data_dir / dialect / f"{session_id}_P.json",  # Subdirectory structure
        data_dir / f"{session_id}_marathi.json",      # Direct file
        data_dir / f"{session_id}.json",              # Simple pattern
    ]
    
    for filepath in possible_files:
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    print(f"❌ Session file not found. Tried:")
    for fp in possible_files:
        print(f"   - {fp}")
    return None


def generate_soap_note_v3(session_id: int, dialect: str = "standard_pune", 
                          model: str = DEFAULT_MODEL,
                          enable_ner: bool = True,
                          enable_rag: bool = True) -> Dict:
    """
    Complete pipeline: NER → RAG → LLM → Translation → Bilingual SOAP
    """
    print(f"\n{'='*60}")
    print(f"  SOAP Generation Pipeline v3 - Session {session_id}")
    print(f"  Dialect: {dialect} | Model: {model}")
    print(f"  NER: {'✅' if enable_ner else '❌'} | RAG: {'✅' if enable_rag else '❌'}")
    print(f"{'='*60}\n")
    
    # Load session data
    print("📂 Loading session data...")
    data = load_session_data(session_id, dialect)
    if not data:
        return {"error": "Session data not found"}
    
    conversation = format_conversation(data.get('turns', []))
    phq8_score = data.get('phq8_total', 0)
    gender = data.get('gender', 'Unknown')
    
    # Severity classification
    if phq8_score <= 4:
        severity = "Minimal/None"
    elif phq8_score <= 9:
        severity = "Mild"
    elif phq8_score <= 14:
        severity = "Moderate"
    elif phq8_score <= 19:
        severity = "Moderately Severe"
    else:
        severity = "Severe"
    
    # Stage 1: NER - Extract Medical Entities
    entities_text = "Entity extraction disabled."
    if enable_ner:
        print("🔍 Stage 1: Extracting medical entities (NER)...")
        ner = MedicalEntityExtractor()
        entities = ner.extract_entities(conversation)
        entities_text = ner.format_entities(entities)
        print(f"   Found {len(entities)} entities")
    
    # Stage 2: RAG - Retrieve Clinical Terminology
    rag_context = "Clinical terminology retrieval disabled."
    if enable_rag:
        print("📚 Stage 2: Retrieving clinical terminology (RAG)...")
        rag = ClinicalRAG()
        rag_context = rag.retrieve(conversation[:500])  # Use first part as query
        print("   Retrieved relevant terms")
    
    # Stage 3: LLM - Generate English SOAP
    print("🤖 Stage 3: Generating English SOAP note (LLM)...")
    prompt = SOAP_PROMPT_TEMPLATE.format(
        phq8_score=phq8_score,
        severity=severity,
        gender=gender,
        entities=entities_text,
        rag_context=rag_context,
        conversation=conversation
    )
    
    english_soap = generate_with_ollama(prompt, model=model)
    
    if english_soap.startswith("Error:"):
        return {"error": english_soap}
    
    print(f"   Generated {len(english_soap)} characters")
    
    # Stage 4: Translation - English → Marathi
    print("🌐 Stage 4: Translating to Marathi...")
    translator = MarathiTranslator()
    marathi_soap = translator.translate(english_soap)
    print(f"   Translated {len(marathi_soap)} characters")
    
    # Format bilingual output
    print("✅ Pipeline complete!\n")
    
    result = {
        "session_id": session_id,
        "dialect": dialect,
        "phq8_score": phq8_score,
        "severity": severity,
        "gender": gender,
        "soap_english": english_soap,
        "soap_marathi": marathi_soap,
        "entities": entities_text if enable_ner else None,
        "rag_context": rag_context if enable_rag else None,
        "model": model,
        "version": "3.0"
    }
    
    return result


def save_soap_note(result: Dict, output_dir: Path = Path("data/soap_notes")):
    """Save bilingual SOAP note to file"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    session_id = result['session_id']
    dialect = result['dialect']
    
    # Save JSON
    json_file = output_dir / f"soap_{session_id}_{dialect}_v3.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Saved: {json_file.name}")



# ============================================================
# MAIN CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="SOAP Note Generator v3 - Full Pipeline")
    parser.add_argument('--session_id', type=int, help='Session ID to process')
    parser.add_argument('--dialect', type=str, default='standard_pune',
                       choices=['standard_pune', 'mumbai', 'vidarbha', 'marathwada', 'konkan'],
                       help='Marathi dialect')
    parser.add_argument('--model', type=str, default=DEFAULT_MODEL,
                       help='Ollama model to use')
    parser.add_argument('--all', action='store_true',
                       help='Generate for all 182 sessions')
    parser.add_argument('--sessions', nargs='+', type=int,
                       help='Generate for specific sessions (e.g., 300 301 302)')
    parser.add_argument('--disable-ner', action='store_true',
                       help='Disable NER entity extraction')
    parser.add_argument('--disable-rag', action='store_true',
                       help='Disable RAG terminology retrieval')
    
    args = parser.parse_args()
    
    # Determine which sessions to process
    if args.all:
        sessions = list(range(300, 482))  # All 182 sessions
        print(f"🚀 Processing ALL 182 sessions...")
    elif args.sessions:
        sessions = args.sessions
        print(f"🚀 Processing {len(sessions)} specified sessions...")
    elif args.session_id:
        sessions = [args.session_id]
    else:
        print("❌ Please specify --session_id, --sessions, or --all")
        return
    
    # Process sessions
    success_count = 0
    error_count = 0
    
    for session_id in tqdm(sessions, desc="Generating SOAP notes"):
        try:
            result = generate_soap_note_v3(
                session_id=session_id,
                dialect=args.dialect,
                model=args.model,
                enable_ner=not args.disable_ner,
                enable_rag=not args.disable_rag
            )
            
            if 'error' in result:
                print(f"❌ Session {session_id}: {result['error']}")
                error_count += 1
            else:
                save_soap_note(result)
                success_count += 1
        
        except Exception as e:
            print(f"❌ Session {session_id} failed: {e}")
            error_count += 1
    
    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"  ✅ Success: {success_count} | ❌ Errors: {error_count}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
