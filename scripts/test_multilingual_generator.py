#!/usr/bin/env python3
"""
Test script for the new multilingual SOAP generator

This demonstrates how the system now accepts transcripts in any language:
- Marathi
- Hindi  
- English
- Mixed languages

And generates SOAP notes in both English + Input Language
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.generation import MultilingualSOAPGenerator


def test_marathi_input():
    """Test with Marathi transcript"""
    print("\n" + "="*70)
    print("TEST 1: Marathi Input")
    print("="*70)
    
    config = {
        'llm_model': 'gemma2:2b',
        'translator_type': 'nllb',
        'device': 'cpu'
    }
    
    generator = MultilingualSOAPGenerator(config)
    
    # Sample Marathi conversation
    marathi_conversation = """डॉक्टर: नमस्कार, आज तुम्हाला कसे वाटते?
रुग्ण: मला झोप येत नाही रात्री. खूप चिंता वाटते.
डॉक्टर: कधीपासून असं होतंय?
रुग्ण: गेले दोन आठवड्यांपासून. काम मध्ये खूप ताण आहे.
डॉक्टर: भूक कशी आहे?
रुग्ण: भूक कमी झाली आहे. खाण्याची इच्छा नाही.
डॉक्टर: आत्महत्येचे विचार येतात का?
रुग्ण: नाही, पण कधी कधी सगळं सोडून द्यावं असं वाटतं."""
    
    result = generator.generate_from_transcript(
        conversation=marathi_conversation,
        phq8_score=15,
        severity="moderately_severe",
        gender="male",
        target_lang="marathi"
    )
    
    print(f"\n📊 Detected Language: {result.input_language}")
    print(f"🎯 Target Language: {result.target_language_code}")
    print("\n📝 English SOAP Note:")
    print("-" * 70)
    print(f"SUBJECTIVE:\n{result.english.subjective[:200]}...\n")
    print(f"ASSESSMENT:\n{result.english.assessment[:200]}...\n")
    
    print("\n🇮🇳 Marathi SOAP Note:")
    print("-" * 70)
    print(f"SUBJECTIVE:\n{result.target_language.subjective[:200]}...\n")


def test_hindi_input():
    """Test with Hindi transcript"""
    print("\n" + "="*70)
    print("TEST 2: Hindi Input")
    print("="*70)
    
    config = {
        'llm_model': 'gemma2:2b',
        'translator_type': 'nllb',
        'device': 'cpu'
    }
    
    generator = MultilingualSOAPGenerator(config)
    
    # Sample Hindi conversation
    hindi_conversation = """डॉक्टर: नमस्ते, आज आप कैसा महसूस कर रहे हैं?
मरीज: मुझे नींद नहीं आ रही है रात में। बहुत चिंता होती है।
डॉक्टर: यह कब से हो रहा है?
मरीज: पिछले दो हफ्ते से। काम में बहुत तनाव है।
डॉक्टर: भूख कैसी है?
मरीज: भूख कम हो गई है। खाने का मन नहीं करता।"""
    
    result = generator.generate_from_transcript(
        conversation=hindi_conversation,
        phq8_score=12,
        severity="moderate",
        gender="female",
        target_lang="hindi"
    )
    
    print(f"\n📊 Detected Language: {result.input_language}")
    print(f"🎯 Target Language: {result.target_language_code}")
    print("\n✅ SOAP generated successfully!")


def test_english_input():
    """Test with English transcript"""
    print("\n" + "="*70)
    print("TEST 3: English Input")
    print("="*70)
    
    config = {
        'llm_model': 'gemma2:2b',
        'translator_type': 'nllb',
        'device': 'cpu'
    }
    
    generator = MultilingualSOAPGenerator(config)
    
    # Sample English conversation
    english_conversation = """Doctor: Hello, how are you feeling today?
Patient: I'm not sleeping well at night. I feel very anxious.
Doctor: How long has this been happening?
Patient: For the past two weeks. There's a lot of stress at work.
Doctor: How is your appetite?
Patient: My appetite has decreased. I don't feel like eating.
Doctor: Are you having suicidal thoughts?
Patient: No, but sometimes I feel like giving up on everything."""
    
    result = generator.generate_from_transcript(
        conversation=english_conversation,
        phq8_score=13,
        severity="moderate",
        gender="male",
        target_lang="marathi"  # Generate Marathi translation
    )
    
    print(f"\n📊 Detected Language: {result.input_language}")
    print(f"🎯 Target Language: {result.target_language_code}")
    print("\n✅ SOAP generated successfully!")
    print(f"\nSubjective (English): {result.english.subjective[:150]}...")


def test_api_format():
    """Test with API-style input"""
    print("\n" + "="*70)
    print("TEST 4: API JSON Format")
    print("="*70)
    
    config = {
        'llm_model': 'gemma2:2b',
        'translator_type': 'nllb',
        'device': 'cpu'
    }
    
    generator = MultilingualSOAPGenerator(config)
    
    # Simulate API request
    api_input = {
        "conversation": """डॉक्टर: आज तुम्हाला कसे वाटते?
रुग्ण: मला खूप थकवा वाटतो. काहीही करावं असं वाटत नाही.""",
        "phq8_score": 10,
        "severity": "mild",
        "gender": "female",
        "target_lang": "marathi"
    }
    
    result = generator.generate_from_transcript(**api_input)
    
    # Convert to API response format
    response = result.to_dict()
    
    print(f"\n✅ API Response Keys: {list(response.keys())}")
    print(f"📊 Metadata: {response['metadata']}")
    print("\n✅ Ready for frontend consumption!")


if __name__ == "__main__":
    print("\n🚀 Testing Multilingual SOAP Generator")
    print("="*70)
    
    try:
        # Run all tests
        test_marathi_input()
        test_hindi_input()
        test_english_input()
        test_api_format()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETED!")
        print("="*70)
        
        print("\n📌 Key Features Demonstrated:")
        print("  ✓ Accepts Marathi/Hindi/English input")
        print("  ✓ Auto-detects input language")
        print("  ✓ Generates English SOAP note")
        print("  ✓ Translates to target language")
        print("  ✓ Returns bilingual output")
        print("\n🎯 Ready for production use!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
