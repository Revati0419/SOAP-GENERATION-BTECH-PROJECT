"""Generation module"""
from .soap_generator import SOAPGenerator, SOAPNote, get_soap_generator
from .multilingual_soap_generator import (
    MultilingualSOAPGenerator, 
    MultilingualSOAPNote,
    LanguageDetector,
    get_multilingual_soap_generator
)

__all__ = [
    'SOAPGenerator', 
    'SOAPNote', 
    'get_soap_generator',
    'MultilingualSOAPGenerator',
    'MultilingualSOAPNote',
    'LanguageDetector',
    'get_multilingual_soap_generator'
]
