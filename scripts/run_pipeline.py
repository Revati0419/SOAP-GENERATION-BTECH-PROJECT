#!/usr/bin/env python3
"""
Main SOAP Generation Pipeline - Fully Open Source

This script orchestrates the complete pipeline:
1. Load conversation data
2. Extract medical entities (NER)
3. Generate English SOAP note (LLM)
4. Translate to Marathi/Hindi (IndicTrans2)
5. Refine clinical terms (RAG)

All components are open-source and can run locally.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_json, save_json, get_project_root, format_conversation
from src.generation import SOAPGenerator, SOAPNote
from src.translation import IndicTranslator, get_translator
from src.ner import MedicalNER, get_ner_model
from src.rag import RAGTranslator, ClinicalTermDatabase, ClinicalVectorStore


class SOAPPipeline:
    """
    Complete SOAP generation pipeline
    
    Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │  [Conversation] → [NER] → [LLM] → [Translate] → [RAG]  │
    │                                                         │
    │  Components:                                            │
    │  - NER: IndicNER / BioBERT (medical entity extraction) │
    │  - LLM: Gemma 2 / Llama 3.1 (SOAP generation)         │
    │  - Translation: IndicTrans2 (En → Marathi/Hindi)       │
    │  - RAG: ChromaDB (clinical term refinement)            │
    └─────────────────────────────────────────────────────────┘
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize pipeline components
        
        Args:
            config: Configuration dict (or load from configs/config.yaml)
        """
        self.config = config or {}
        self.project_root = get_project_root()
        
        # Component flags
        self.use_ner = self.config.get('use_ner', True)
        self.use_translation = self.config.get('use_translation', True)
        self.use_rag = self.config.get('use_rag', True)
        
        # Initialize components lazily
        self._ner = None
        self._generator = None
        self._translator = None
        self._rag = None
    
    @property
    def ner(self) -> MedicalNER:
        """Lazy load NER model"""
        if self._ner is None and self.use_ner:
            print("📦 Loading NER model...")
            self._ner = get_ner_model(
                model_type=self.config.get('ner_type', 'rule_based'),
                device=self.config.get('device', 'cpu')
            )
        return self._ner
    
    @property
    def generator(self) -> SOAPGenerator:
        """Lazy load SOAP generator"""
        if self._generator is None:
            print("📦 Loading SOAP generator...")
            self._generator = SOAPGenerator(
                model=self.config.get('llm_model', 'gemma2:2b')
            )
        return self._generator
    
    @property
    def translator(self) -> IndicTranslator:
        """Lazy load translator"""
        if self._translator is None and self.use_translation:
            print("📦 Loading translator...")
            self._translator = get_translator(
                model_type=self.config.get('translator_type', 'indictrans'),
                device=self.config.get('device', 'cpu')
            )
        return self._translator
    
    @property
    def rag(self) -> RAGTranslator:
        """Lazy load RAG translator"""
        if self._rag is None and self.use_rag:
            print("📦 Loading RAG system...")
            vector_store = ClinicalVectorStore()
            ClinicalTermDatabase.initialize_vector_store(vector_store)
            self._rag = RAGTranslator(
                vector_store=vector_store,
                translator=self.translator
            )
        return self._rag
    
    def process_session(self, session_data: Dict, 
                        dialect: str = "standard_pune",
                        target_lang: str = "marathi") -> Dict:
        """
        Process a single session through the complete pipeline
        
        Args:
            session_data: Session dict with conversation data
            dialect: Which dialect to use
            target_lang: Target translation language
            
        Returns:
            Dict with SOAP notes in English and target language
        """
        result = {
            'session_id': session_data.get('session_id'),
            'phq8_score': session_data.get('phq8_score'),
            'severity': session_data.get('severity'),
            'gender': session_data.get('gender'),
            'dialect': dialect,
        }
        
        # Get conversation
        turns = session_data.get('dialects', {}).get(dialect, [])
        if not turns:
            dialects = session_data.get('dialects', {})
            if dialects:
                dialect = list(dialects.keys())[0]
                turns = dialects[dialect]
        
        if not turns:
            result['error'] = "No conversation found"
            return result
        
        # Step 1: Extract entities (optional)
        if self.use_ner and self.ner:
            print("  🔍 Extracting medical entities...")
            entities = self.ner.extract_from_conversation(turns)
            result['entities'] = {
                'patient': [e.__dict__ for e in entities.get('patient', [])],
                'doctor': [e.__dict__ for e in entities.get('doctor', [])]
            }
        
        # Step 2: Generate English SOAP
        print("  📝 Generating English SOAP note...")
        soap_note = self.generator.generate_from_session(session_data, dialect)
        
        result['soap_english'] = soap_note.to_dict()
        
        # Step 3: Translate to target language
        if self.use_translation and self.translator and soap_note.raw_output:
            print(f"  🔄 Translating to {target_lang}...")
            
            # Translate each section
            translated_sections = {}
            for section in ['subjective', 'objective', 'assessment', 'plan']:
                content = getattr(soap_note, section, '')
                if content:
                    if self.use_rag and self.rag:
                        # Use RAG-enhanced translation
                        translated = self.rag.translate_with_rag(
                            content, target_lang
                        )
                    else:
                        # Direct translation
                        translated = self.translator.translate(
                            content, "english", target_lang
                        )
                    translated_sections[section] = translated
                else:
                    translated_sections[section] = ""
            
            result[f'soap_{target_lang}'] = translated_sections
        
        return result
    
    def process_batch(self, input_dir: str, output_dir: str,
                      dialect: str = "standard_pune",
                      target_lang: str = "marathi",
                      limit: Optional[int] = None,
                      skip_existing: bool = True) -> int:
        """
        Process multiple sessions
        
        Args:
            input_dir: Directory with input conversation files
            output_dir: Directory for output SOAP notes
            dialect: Dialect to use
            target_lang: Target translation language
            limit: Max files to process
            skip_existing: Skip already processed files
            
        Returns:
            Number of files processed
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Get input files
        input_files = sorted(input_path.glob('*_marathi.json'))
        if limit:
            input_files = input_files[:limit]
        
        print(f"\n{'='*60}")
        print(f"  SOAP GENERATION PIPELINE")
        print(f"  Input: {input_dir}")
        print(f"  Output: {output_dir}")
        print(f"  Files: {len(input_files)}")
        print(f"  Target Language: {target_lang}")
        print(f"{'='*60}\n")
        
        # Check Ollama
        if not self.generator.check_ollama():
            print("❌ Ollama not running. Start with: ollama serve")
            return 0
        
        processed = 0
        for filepath in tqdm(input_files, desc="Processing"):
            session_id = filepath.stem.split('_')[0]
            output_file = output_path / f"{session_id}_soap.json"
            
            # Skip existing
            if skip_existing and output_file.exists():
                continue
            
            try:
                session_data = load_json(str(filepath))
                result = self.process_session(
                    session_data, dialect, target_lang
                )
                save_json(result, str(output_file))
                processed += 1
                
            except Exception as e:
                print(f"\n❌ Error processing {filepath.name}: {e}")
        
        print(f"\n✅ Processed {processed} sessions")
        return processed


def main():
    parser = argparse.ArgumentParser(
        description="SOAP Generation Pipeline (Fully Open Source)"
    )
    
    # Input/Output
    parser.add_argument('--input-dir', type=str, 
                        default='data/dialect_marathi',
                        help='Input directory with conversation files')
    parser.add_argument('--output-dir', type=str,
                        default='data/soap_notes',
                        help='Output directory for SOAP notes')
    
    # Model options
    parser.add_argument('--llm-model', type=str, default='gemma2:2b',
                        help='LLM model for SOAP generation (Ollama)')
    parser.add_argument('--translator', type=str, default='indictrans',
                        choices=['indictrans', 'nllb', 'none'],
                        help='Translation model')
    parser.add_argument('--target-lang', type=str, default='marathi',
                        choices=['marathi', 'hindi'],
                        help='Target translation language')
    
    # Processing options
    parser.add_argument('--dialect', type=str, default='standard_pune',
                        help='Input dialect to use')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of files')
    parser.add_argument('--no-ner', action='store_true',
                        help='Disable NER extraction')
    parser.add_argument('--no-rag', action='store_true',
                        help='Disable RAG refinement')
    parser.add_argument('--no-translate', action='store_true',
                        help='Disable translation (English only)')
    
    # Single file mode
    parser.add_argument('--session-id', type=str, default=None,
                        help='Process single session by ID')
    parser.add_argument('--test', action='store_true',
                        help='Test mode: process first file only')
    
    args = parser.parse_args()
    
    # Build config
    config = {
        'llm_model': args.llm_model,
        'translator_type': args.translator if args.translator != 'none' else None,
        'use_ner': not args.no_ner,
        'use_rag': not args.no_rag,
        'use_translation': not args.no_translate and args.translator != 'none',
        'device': 'cpu',  # Change to 'cuda' if GPU available
    }
    
    # Initialize pipeline
    pipeline = SOAPPipeline(config)
    
    # Process
    project_root = get_project_root()
    input_dir = project_root / args.input_dir
    output_dir = project_root / args.output_dir
    
    limit = 1 if args.test else args.limit
    
    pipeline.process_batch(
        input_dir=str(input_dir),
        output_dir=str(output_dir),
        dialect=args.dialect,
        target_lang=args.target_lang,
        limit=limit
    )


if __name__ == "__main__":
    main()
