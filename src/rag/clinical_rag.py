"""
RAG (Retrieval-Augmented Generation) for Clinical Translation

Uses vector similarity to find relevant clinical terms and their
correct translations, improving translation accuracy for medical text.
"""

import json
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class ClinicalVectorStore:
    """
    Vector store for clinical terminology using ChromaDB
    
    Stores English clinical terms with their Marathi/Hindi translations
    for retrieval during translation.
    """
    
    def __init__(self, collection_name: str = "clinical_terms",
                 persist_dir: str = ".cache/vector_db"):
        """
        Initialize vector store
        
        Args:
            collection_name: Name of the ChromaDB collection
            persist_dir: Directory to persist the database
        """
        self.collection_name = collection_name
        self.persist_dir = persist_dir
        self.client = None
        self.collection = None
        self._loaded = False
    
    def load(self):
        """Initialize ChromaDB"""
        if self._loaded:
            return
        
        try:
            import chromadb
            from chromadb.config import Settings
            
            Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
            
            self.client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=self.persist_dir,
                anonymized_telemetry=False
            ))
            
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Clinical terms for translation"}
            )
            
            self._loaded = True
            print(f"✅ Vector store loaded: {self.collection_name}")
            
        except ImportError:
            print("❌ chromadb not installed. Run: pip install chromadb")
            raise
    
    def add_terms(self, terms: List[Dict]):
        """
        Add clinical terms to the vector store
        
        Args:
            terms: List of dicts with 'english', 'marathi', 'hindi', 'category'
        """
        self.load()
        
        documents = []
        metadatas = []
        ids = []
        
        for i, term in enumerate(terms):
            doc = term.get('english', '')
            if not doc:
                continue
            
            documents.append(doc)
            metadatas.append({
                'marathi': term.get('marathi', ''),
                'hindi': term.get('hindi', ''),
                'category': term.get('category', 'general'),
                'context': term.get('context', '')
            })
            ids.append(f"term_{i}_{hash(doc) % 10000}")
        
        if documents:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"Added {len(documents)} terms to vector store")
    
    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        Search for similar clinical terms
        
        Args:
            query: Search query (English text)
            n_results: Number of results to return
            
        Returns:
            List of matching terms with translations
        """
        self.load()
        
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        matches = []
        if results and results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                distance = results['distances'][0][i] if results['distances'] else 0
                
                matches.append({
                    'english': doc,
                    'marathi': metadata.get('marathi', ''),
                    'hindi': metadata.get('hindi', ''),
                    'category': metadata.get('category', ''),
                    'similarity': 1 - distance  # Convert distance to similarity
                })
        
        return matches
    
    def load_vocab_file(self, vocab_path: str):
        """Load vocabulary from JSON file"""
        with open(vocab_path, 'r', encoding='utf-8') as f:
            vocab = json.load(f)
        
        terms = []
        for english, translations in vocab.items():
            if isinstance(translations, dict):
                terms.append({
                    'english': english,
                    'marathi': translations.get('formal', translations.get('marathi', '')),
                    'hindi': translations.get('hindi', ''),
                    'category': 'clinical'
                })
            else:
                terms.append({
                    'english': english,
                    'marathi': str(translations),
                    'category': 'clinical'
                })
        
        self.add_terms(terms)


class RAGTranslator:
    """
    RAG-enhanced translator for clinical text
    
    Combines:
    1. Vector search for clinical terms
    2. Open-source translation model
    3. Context-aware generation
    """
    
    def __init__(self, vector_store: Optional[ClinicalVectorStore] = None,
                 translator = None):
        """
        Initialize RAG translator
        
        Args:
            vector_store: ClinicalVectorStore instance
            translator: Translation model (IndicTranslator)
        """
        self.vector_store = vector_store or ClinicalVectorStore()
        self.translator = translator
        
        # Clinical term cache
        self.term_cache = {}
    
    def translate_with_rag(self, text: str, target_lang: str = "marathi") -> str:
        """
        Translate text using RAG for better clinical accuracy
        
        Args:
            text: English text to translate
            target_lang: Target language
            
        Returns:
            Translated text with corrected clinical terms
        """
        # Step 1: Find clinical terms in the text
        clinical_matches = self._find_clinical_terms(text)
        
        # Step 2: Translate the full text
        if self.translator:
            translated = self.translator.translate(text, "english", target_lang)
        else:
            translated = text  # Fallback - no translation
        
        # Step 3: Replace clinical terms with correct translations
        for match in clinical_matches:
            if match['similarity'] > 0.8:  # High confidence match
                correct_translation = match.get(target_lang, '')
                if correct_translation:
                    # Find and replace in translated text
                    translated = self._replace_term(
                        translated, 
                        match['english'],
                        correct_translation
                    )
        
        return translated
    
    def _find_clinical_terms(self, text: str) -> List[Dict]:
        """Find clinical terms in text using vector search"""
        # Split text into potential terms
        words = text.replace(',', ' ').replace('.', ' ').split()
        
        all_matches = []
        
        # Search for multi-word phrases
        for i in range(len(words)):
            for j in range(i + 1, min(i + 4, len(words) + 1)):
                phrase = ' '.join(words[i:j])
                if len(phrase) > 3:  # Skip very short phrases
                    matches = self.vector_store.search(phrase, n_results=2)
                    all_matches.extend(matches)
        
        # Deduplicate and sort by similarity
        seen = set()
        unique_matches = []
        for m in sorted(all_matches, key=lambda x: x['similarity'], reverse=True):
            if m['english'] not in seen:
                seen.add(m['english'])
                unique_matches.append(m)
        
        return unique_matches[:10]  # Top 10 matches
    
    def _replace_term(self, text: str, english_term: str, 
                      target_translation: str) -> str:
        """Replace a term with its correct translation"""
        # This is a simplified replacement - could be improved with fuzzy matching
        # For now, we trust the vector store matches
        return text  # Placeholder - actual implementation would do fuzzy replacement


class ClinicalTermDatabase:
    """
    Pre-built database of clinical/mental health terms
    with accurate Marathi and Hindi translations
    """
    
    MENTAL_HEALTH_TERMS = [
        # Symptoms
        {"english": "depression", "marathi": "नैराश्य", "hindi": "अवसाद", "category": "symptom"},
        {"english": "anxiety", "marathi": "चिंता", "hindi": "चिंता", "category": "symptom"},
        {"english": "stress", "marathi": "ताण", "hindi": "तनाव", "category": "symptom"},
        {"english": "insomnia", "marathi": "निद्रानाश", "hindi": "अनिद्रा", "category": "symptom"},
        {"english": "fatigue", "marathi": "थकवा", "hindi": "थकान", "category": "symptom"},
        {"english": "hopelessness", "marathi": "निराशा", "hindi": "निराशा", "category": "symptom"},
        {"english": "irritability", "marathi": "चिडचिड", "hindi": "चिड़चिड़ापन", "category": "symptom"},
        {"english": "panic attack", "marathi": "घबराट", "hindi": "घबराहट का दौरा", "category": "symptom"},
        {"english": "mood swings", "marathi": "मनःस्थिती बदल", "hindi": "मिजाज में बदलाव", "category": "symptom"},
        {"english": "loss of interest", "marathi": "रुची कमी होणे", "hindi": "रुचि में कमी", "category": "symptom"},
        {"english": "concentration problems", "marathi": "एकाग्रता समस्या", "hindi": "एकाग्रता की समस्या", "category": "symptom"},
        {"english": "appetite changes", "marathi": "भूक बदल", "hindi": "भूख में बदलाव", "category": "symptom"},
        {"english": "sleep disturbance", "marathi": "झोपेत अडथळा", "hindi": "नींद में खलल", "category": "symptom"},
        {"english": "low energy", "marathi": "कमी ऊर्जा", "hindi": "कम ऊर्जा", "category": "symptom"},
        {"english": "worthlessness", "marathi": "निरर्थकता", "hindi": "बेकार होने का एहसास", "category": "symptom"},
        {"english": "guilt", "marathi": "अपराधीपणा", "hindi": "अपराध बोध", "category": "symptom"},
        {"english": "suicidal thoughts", "marathi": "आत्महत्येचे विचार", "hindi": "आत्महत्या के विचार", "category": "symptom"},
        {"english": "self-harm", "marathi": "स्वतःला इजा", "hindi": "आत्म-हानि", "category": "symptom"},
        
        # Diagnoses
        {"english": "major depressive disorder", "marathi": "मुख्य नैराश्य विकार", "hindi": "प्रमुख अवसादग्रस्तता विकार", "category": "diagnosis"},
        {"english": "generalized anxiety disorder", "marathi": "सामान्यीकृत चिंता विकार", "hindi": "सामान्यीकृत चिंता विकार", "category": "diagnosis"},
        {"english": "bipolar disorder", "marathi": "द्विध्रुवीय विकार", "hindi": "द्विध्रुवी विकार", "category": "diagnosis"},
        {"english": "PTSD", "marathi": "आघातोत्तर ताण विकार", "hindi": "पीटीएसडी", "category": "diagnosis"},
        {"english": "social anxiety", "marathi": "सामाजिक चिंता", "hindi": "सामाजिक चिंता", "category": "diagnosis"},
        
        # Severity
        {"english": "mild", "marathi": "सौम्य", "hindi": "हल्का", "category": "severity"},
        {"english": "moderate", "marathi": "मध्यम", "hindi": "मध्यम", "category": "severity"},
        {"english": "severe", "marathi": "तीव्र", "hindi": "गंभीर", "category": "severity"},
        {"english": "minimal", "marathi": "अत्यल्प", "hindi": "न्यूनतम", "category": "severity"},
        
        # Treatment
        {"english": "psychotherapy", "marathi": "मानसोपचार", "hindi": "मनोचिकित्सा", "category": "treatment"},
        {"english": "cognitive behavioral therapy", "marathi": "संज्ञानात्मक वर्तणूक उपचार", "hindi": "संज्ञानात्मक व्यवहार थेरेपी", "category": "treatment"},
        {"english": "counseling", "marathi": "समुपदेशन", "hindi": "परामर्श", "category": "treatment"},
        {"english": "medication", "marathi": "औषधोपचार", "hindi": "दवाई", "category": "treatment"},
        {"english": "antidepressant", "marathi": "प्रतिनैराश्यक", "hindi": "अवसादरोधी", "category": "treatment"},
        {"english": "follow-up", "marathi": "पाठपुरावा", "hindi": "अनुवर्ती", "category": "treatment"},
        
        # SOAP specific
        {"english": "chief complaint", "marathi": "मुख्य तक्रार", "hindi": "मुख्य शिकायत", "category": "soap"},
        {"english": "history of present illness", "marathi": "सध्याच्या आजाराचा इतिहास", "hindi": "वर्तमान बीमारी का इतिहास", "category": "soap"},
        {"english": "assessment", "marathi": "मूल्यांकन", "hindi": "मूल्यांकन", "category": "soap"},
        {"english": "treatment plan", "marathi": "उपचार योजना", "hindi": "उपचार योजना", "category": "soap"},
        {"english": "risk assessment", "marathi": "जोखीम मूल्यांकन", "hindi": "जोखिम मूल्यांकन", "category": "soap"},
        {"english": "prognosis", "marathi": "रोगनिदान", "hindi": "पूर्वानुमान", "category": "soap"},
    ]
    
    @classmethod
    def get_all_terms(cls) -> List[Dict]:
        """Get all clinical terms"""
        return cls.MENTAL_HEALTH_TERMS
    
    @classmethod
    def initialize_vector_store(cls, vector_store: ClinicalVectorStore):
        """Initialize vector store with clinical terms"""
        vector_store.add_terms(cls.MENTAL_HEALTH_TERMS)
        print(f"✅ Loaded {len(cls.MENTAL_HEALTH_TERMS)} clinical terms")


def get_rag_translator(translator = None) -> RAGTranslator:
    """Factory function to create RAG translator"""
    vector_store = ClinicalVectorStore()
    ClinicalTermDatabase.initialize_vector_store(vector_store)
    return RAGTranslator(vector_store=vector_store, translator=translator)
