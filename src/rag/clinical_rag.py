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
            
            # Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
            
            # Use new PersistentClient API (ChromaDB 0.4.0+)
            self.client = chromadb.PersistentClient(path=self.persist_dir)
            
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
    
    # In rag.py -> ClinicalTermDatabase class

    MENTAL_HEALTH_TERMS = [
        # 1. Chief Complaint (मुख्य तक्रार)
        {"english": "chief complaint", "marathi": "मुख्य तक्रार", "category": "cc"},
        {"english": "presenting symptoms", "marathi": "सध्याची लक्षणे", "category": "cc"},

        # 2. HPI (सध्याच्या आजाराचा इतिहास)
        {"english": "history of present illness", "marathi": "सध्याच्या आजाराचा इतिहास", "category": "hpi"},
        {"english": "onset", "marathi": "सुरुवात", "category": "hpi"},
        {"english": "triggering factor", "marathi": "उत्तेजक घटक", "category": "hpi"},

        # 3. Trauma History (आघाताचा इतिहास)
        {"english": "trauma history", "marathi": "आघाताचा इतिहास", "category": "trauma"},
        {"english": "emotional distress", "marathi": "भावनिक त्रास", "category": "trauma"},
        {"english": "past regret", "marathi": "भूतकाळातील खेद", "category": "trauma"},

        # 4. Psychosocial (मनोसामाजिक इतिहास)
        {"english": "psychosocial history", "marathi": "मनोसामाजिक इतिहास", "category": "psychosocial"},
        {"english": "family support", "marathi": "कौटुंबिक आधार", "category": "psychosocial"},
        {"english": "social isolation", "marathi": "सामाजिक एकाकीपणा", "category": "psychosocial"},

        # 5. Functional Status (कार्यक्षम स्थिती)
        {"english": "functional status", "marathi": "कार्यक्षम स्थिती", "category": "functional"},
        {"english": "daily activities", "marathi": "दैनंदिन क्रिया", "category": "functional"},
        {"english": "occupational history", "marathi": "व्यावसायिक इतिहास", "category": "functional"},

        # 6. Biological (जैविक निरीक्षणे)
        {"english": "biological observations", "marathi": "जैविक निरीक्षणे", "category": "biological"},
        {"english": "sleep patterns", "marathi": "झोपण्याची पद्धत", "category": "biological"},
        {"english": "appetite change", "marathi": "भूकेत बदल", "category": "biological"},

        # 7. MSE (मानसिक स्थिती तपासणी)
        {"english": "mental status exam", "marathi": "मानसिक स्थिती तपासणी", "category": "mse"},
        {"english": "affect and mood", "marathi": "प्रभाव आणि मनःस्थिती", "category": "mse"},
        {"english": "thought process", "marathi": "विचार प्रक्रिया", "category": "mse"},

        # 8. Medical History (वैद्यकीय इतिहास)
        {"english": "medical history", "marathi": "वैद्यकीय इतिहास", "category": "medical"},
        {"english": "physical illness", "marathi": "शारीरिक आजार", "category": "medical"},

        # 9. Past Psych History (पूर्व मनोरुग्ण इतिहास)
        {"english": "past psychiatric history", "marathi": "पूर्व मनोरुग्ण इतिहास", "category": "past_psych"},
        {"english": "previous diagnosis", "marathi": "पूर्वीचे निदान", "category": "past_psych"},

        # 10. Plan (उपचार योजना)
        {"english": "treatment plan", "marathi": "उपचार योजना", "category": "plan"},
        {"english": "safety precautions", "marathi": "सुरक्षा खबरदारी", "category": "plan"},
        {"english": "follow up", "marathi": "पाठपुरावा", "category": "plan"}
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
