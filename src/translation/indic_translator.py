"""
Open-Source Translation Module using IndicTrans2 / NLLB-200

IndicTrans2: Best for Indian languages (AI4Bharat, IIT Madras)
NLLB-200: Meta's multilingual model (200 languages)
"""

import os
from typing import Optional, List
from pathlib import Path


class IndicTranslator:
    """
    Open-source translator using IndicTrans2 or NLLB-200
    
    IndicTrans2 is specifically trained for Indian languages and provides
    better quality for Marathi/Hindi than generic models.
    """
    
    def __init__(self, model_name: str = "ai4bharat/indictrans2-en-indic-1B",
                 device: str = "cpu", cache_dir: Optional[str] = None):
        """
        Initialize the translator
        
        Args:
            model_name: HuggingFace model name
                - "ai4bharat/indictrans2-en-indic-1B" (recommended for Indic)
                - "facebook/nllb-200-distilled-600M" (smaller, multilingual)
            device: "cpu" or "cuda"
            cache_dir: Directory to cache models
        """
        self.model_name = model_name
        self.device = device
        self.cache_dir = cache_dir or str(Path.home() / ".cache" / "indictrans")
        
        self.model = None
        self.tokenizer = None
        self._loaded = False
        
        # Language codes
        self.lang_codes = {
            "marathi": "mar_Deva",
            "hindi": "hin_Deva", 
            "english": "eng_Latn",
            "bengali": "ben_Beng",
            "tamil": "tam_Taml",
            "telugu": "tel_Telu",
            "gujarati": "guj_Gujr",
            "kannada": "kan_Knda",
            "malayalam": "mal_Mlym",
            "punjabi": "pan_Guru",
        }
    
    def load_model(self):
        """Lazy load the model"""
        if self._loaded:
            return
        
        print(f"Loading translation model: {self.model_name}...")
        
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            import torch
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir,
                trust_remote_code=True
            )
            
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir,
                trust_remote_code=True,
                torch_dtype=torch.float32 if self.device == "cpu" else torch.float16
            )
            
            if self.device == "cuda":
                self.model = self.model.cuda()
            
            self._loaded = True
            print(f"✅ Model loaded successfully on {self.device}")
            
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            raise
    
    def translate(self, text: str, source_lang: str = "english",
                  target_lang: str = "marathi") -> str:
        """
        Translate text from source to target language
        
        Args:
            text: Text to translate
            source_lang: Source language name
            target_lang: Target language name
            
        Returns:
            Translated text
        """
        if not text.strip():
            return ""
        
        self.load_model()
        
        src_code = self.lang_codes.get(source_lang, source_lang)
        tgt_code = self.lang_codes.get(target_lang, target_lang)
        
        try:
            import torch
            
            # Handle IndicTrans2 format
            if "indictrans" in self.model_name.lower():
                return self._translate_indictrans(text, src_code, tgt_code)
            else:
                # NLLB format
                return self._translate_nllb(text, src_code, tgt_code)
                
        except Exception as e:
            print(f"Translation error: {e}")
            return text
    
    def _translate_indictrans(self, text: str, src_code: str, tgt_code: str) -> str:
        """Translate using IndicTrans2 format"""
        import torch
        
        # IndicTrans2 uses special preprocessing
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        
        if self.device == "cuda":
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=512,
                num_beams=5,
                early_stopping=True
            )
        
        translated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return translated
    
    def _translate_nllb(self, text: str, src_code: str, tgt_code: str) -> str:
        """Translate using NLLB-200 format"""
        import torch
        
        self.tokenizer.src_lang = src_code
        
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        
        if self.device == "cuda":
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        forced_bos_token_id = self.tokenizer.convert_tokens_to_ids(tgt_code)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                forced_bos_token_id=forced_bos_token_id,
                max_length=512,
                num_beams=5,
                early_stopping=True
            )
        
        translated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return translated
    
    def translate_batch(self, texts: List[str], source_lang: str = "english",
                        target_lang: str = "marathi", batch_size: int = 8) -> List[str]:
        """
        Translate multiple texts in batches
        
        Args:
            texts: List of texts to translate
            source_lang: Source language
            target_lang: Target language
            batch_size: Batch size for processing
            
        Returns:
            List of translated texts
        """
        self.load_model()
        
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            for text in batch:
                translated = self.translate(text, source_lang, target_lang)
                results.append(translated)
        
        return results
    
    def translate_soap_note(self, soap_sections: dict, 
                            target_lang: str = "marathi") -> dict:
        """
        Translate a complete SOAP note
        
        Args:
            soap_sections: Dict with keys 'subjective', 'objective', 'assessment', 'plan'
            target_lang: Target language
            
        Returns:
            Translated SOAP note dict
        """
        translated = {}
        
        for section, content in soap_sections.items():
            if content:
                print(f"    Translating {section}...")
                translated[section] = self.translate(content, "english", target_lang)
            else:
                translated[section] = ""
        
        return translated


# Lightweight fallback using direct API (no model download needed)
class LightweightTranslator:
    """
    Lightweight translator using Argos Translate (fully offline, open-source)
    Much smaller footprint than transformer models.
    """
    
    def __init__(self):
        self.translator = None
        self._loaded = False
    
    def load_model(self):
        """Load Argos Translate"""
        if self._loaded:
            return
            
        try:
            import argostranslate.package
            import argostranslate.translate
            
            # Download and install language package
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()
            
            # Find English to Hindi package (closest to Marathi)
            package = next(
                (p for p in available_packages 
                 if p.from_code == "en" and p.to_code == "hi"),
                None
            )
            
            if package:
                argostranslate.package.install_from_path(package.download())
            
            self._loaded = True
            print("✅ Argos Translate loaded")
            
        except ImportError:
            print("❌ argostranslate not installed. Run: pip install argostranslate")
            raise
    
    def translate(self, text: str, source_lang: str = "en", 
                  target_lang: str = "hi") -> str:
        """Translate text"""
        self.load_model()
        
        import argostranslate.translate
        return argostranslate.translate.translate(text, source_lang, target_lang)


def get_translator(model_type: str = "indictrans", device: str = "cpu"):
    """
    Factory function to get appropriate translator
    
    Args:
        model_type: "indictrans", "nllb", or "argos"
        device: "cpu" or "cuda"
    """
    if model_type == "indictrans":
        return IndicTranslator(
            model_name="ai4bharat/indictrans2-en-indic-1B",
            device=device
        )
    elif model_type == "nllb":
        return IndicTranslator(
            model_name="facebook/nllb-200-distilled-600M",
            device=device
        )
    elif model_type == "argos":
        return LightweightTranslator()
    else:
        raise ValueError(f"Unknown model type: {model_type}")
