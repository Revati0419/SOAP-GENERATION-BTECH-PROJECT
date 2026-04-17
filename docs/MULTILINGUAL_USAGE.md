# Multilingual SOAP Generation - Usage Guide

## 🎯 Overview

Your system now accepts **transcripts in ANY language** (Marathi, Hindi, English, or mixed) and generates **bilingual SOAP notes** (English + Input Language).

---

## 🔄 System Flow

```
┌──────────────────────────────────────────────────────┐
│  INPUT: Raw Transcript                               │
│  • Marathi: "डॉक्टर: तुम्हाला कसे वाटते?"          │
│  • Hindi: "डॉक्टर: आप कैसा महसूस कर रहे हैं?"       │
│  • English: "Doctor: How are you feeling?"          │
│  • Mixed: Any combination                            │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│  Step 1: Language Detection                          │
│  • Automatically detects: Marathi/Hindi/English      │
│  • Uses script analysis (Devanagari vs Latin)        │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│  Step 2: Translation to English (if needed)          │
│  • If input is Marathi/Hindi → Translate to English │
│  • If already English → Skip                         │
│  • Model: NLLB-200 (600M parameters)                │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│  Step 3: SOAP Generation                             │
│  • Gemma 2B processes English conversation           │
│  • Generates structured SOAP note                    │
│  • Extracts clinical information                     │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│  Step 4: Translation to Target Language              │
│  • Translates SOAP sections back to input language   │
│  • Maintains clinical terminology accuracy           │
└──────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────┐
│  OUTPUT: Bilingual SOAP Note                         │
│  • English version (for medical records)             │
│  • Marathi/Hindi version (for patient understanding) │
│  • JSON format with metadata                         │
└──────────────────────────────────────────────────────┘
```

---

## 📡 API Endpoints

### 1️⃣ New Endpoint: `/api/generate-from-transcript`

**Purpose:** Generate SOAP from raw transcript in any language

**Method:** POST

**Request Body:**
```json
{
    "conversation": "डॉक्टर: आज तुम्हाला कसे वाटते?\nरुग्ण: मला झोप येत नाही रात्री...",
    "phq8_score": 15,
    "severity": "moderate",
    "gender": "female",
    "target_lang": "marathi"
}
```

**Response:**
```json
{
    "english": {
        "subjective": "Patient reports sleep disturbance...",
        "objective": "Patient appears anxious...",
        "assessment": "Moderate depression (PHQ-8: 15)...",
        "plan": "Recommend CBT therapy..."
    },
    "marathi": {
        "subjective": "रुग्णाने झोपेच्या विकाराची तक्रार...",
        "objective": "रुग्ण चिंताग्रस्त दिसतो...",
        "assessment": "मध्यम नैराश्य (PHQ-8: 15)...",
        "plan": "CBT थेरपीची शिफारस..."
    },
    "metadata": {
        "input_language": "marathi",
        "target_language": "marathi"
    }
}
```

### 2️⃣ Updated Endpoint: `/api/generate-from-json`

**Purpose:** Generate SOAP from structured JSON file (with auto-detection)

**Method:** POST (multipart/form-data)

**Parameters:**
- `file`: JSON file with conversation data
- `target_lang`: Target language (default: "marathi")

**JSON File Format:**
```json
{
    "session_id": 300,
    "phq8_score": 15,
    "severity": "moderate",
    "gender": "male",
    "dialects": {
        "standard_pune": [
            {
                "role": "Doctor",
                "text": "तुम्हाला कसे वाटते?",
                "text_en": "How are you feeling?"
            },
            {
                "role": "Patient",
                "text": "मला झोप येत नाही",
                "text_en": "I can't sleep"
            }
        ]
    }
}
```

---

## 💻 Python Usage

### Example 1: Direct Transcript Input

```python
from src.generation import MultilingualSOAPGenerator

# Initialize generator
config = {
    'llm_model': 'gemma2:2b',
    'translator_type': 'nllb',
    'device': 'cpu'
}
generator = MultilingualSOAPGenerator(config)

# Marathi input
marathi_transcript = """
डॉक्टर: आज तुम्हाला कसे वाटते?
रुग्ण: मला खूप थकवा वाटतो. झोप येत नाही.
डॉक्टर: कधीपासून असं होतंय?
रुग्ण: गेल्या दोन आठवड्यांपासून.
"""

# Generate SOAP
result = generator.generate_from_transcript(
    conversation=marathi_transcript,
    phq8_score=12,
    severity="moderate",
    gender="female",
    target_lang="marathi"  # Optional, auto-detects if None
)

# Access results
print(f"Detected Language: {result.input_language}")
print(f"English Subjective: {result.english.subjective}")
print(f"Marathi Subjective: {result.target_language.subjective}")
```

### Example 2: JSON Session Data

```python
# Load from JSON file
import json

with open("data/300_marathi.json") as f:
    session_data = json.load(f)

# Generate SOAP
result = generator.generate_from_session(
    session_data=session_data,
    dialect=None,  # Auto-detect
    target_lang="marathi"
)

# Export to dict
output = result.to_dict()
```

### Example 3: Hindi Input

```python
hindi_transcript = """
डॉक्टर: आप कैसा महसूस कर रहे हैं?
मरीज: मुझे नींद नहीं आ रही है।
"""

result = generator.generate_from_transcript(
    conversation=hindi_transcript,
    target_lang="hindi"  # Will output in Hindi + English
)
```

### Example 4: English Input → Marathi Output

```python
english_transcript = """
Doctor: How are you feeling today?
Patient: I'm feeling very tired and anxious.
"""

result = generator.generate_from_transcript(
    conversation=english_transcript,
    target_lang="marathi"  # Translate SOAP to Marathi
)
```

---

## 🧪 Testing

Run the test suite:

```bash
python scripts/test_multilingual_generator.py
```

This will test:
- ✅ Marathi input → English + Marathi SOAP
- ✅ Hindi input → English + Hindi SOAP
- ✅ English input → English + Marathi SOAP
- ✅ API format compatibility

---

## 🚀 Starting the API Server

```bash
# Start the server
python3 api_server.py

# Server will run on: http://localhost:8000

# View API documentation
# Open browser: http://localhost:8000/docs
```

---

## 📋 Supported Languages

### Input Languages (Auto-detected):
- ✅ **Marathi** (मराठी)
- ✅ **Hindi** (हिन्दी)
- ✅ **English**
- ✅ **Mixed** (any combination)

### Output Languages:
- ✅ **English** (always included)
- ✅ **Marathi** (translation)
- ✅ **Hindi** (translation)

---

## 🎯 Key Features

1. **Auto Language Detection**
   - Detects script (Devanagari vs Latin)
   - Identifies Marathi vs Hindi

2. **Bidirectional Translation**
   - Input language → English (for LLM)
   - English → Output language (for SOAP)

3. **Bilingual Output**
   - Always returns English + Target language
   - Medical records in English
   - Patient-friendly in local language

4. **Clinical Accuracy**
   - Uses Gemma 2B for SOAP generation
   - Maintains medical terminology
   - Structured SOAP format

5. **Flexible Input**
   - Raw text transcript
   - Structured JSON
   - Multiple dialects

---

## 🔧 Configuration

Edit `configs/config.yaml`:

```yaml
models:
  generation:
    primary: "gemma2:2b"  # LLM for SOAP generation
    
  translation:
    primary: "facebook/nllb-200-distilled-600M"  # Multilingual translation
    fallback: "ai4bharat/indictrans2-en-indic-1B"  # Better for Indic languages
```

---

## 📊 Performance

- **Language Detection**: < 1ms
- **Translation**: ~2-5 seconds (CPU)
- **SOAP Generation**: ~10-15 seconds (CPU, Gemma 2B)
- **Total**: ~15-20 seconds per transcript

---

## 🐛 Troubleshooting

### Issue: Translation not working
```bash
# Install translation models
pip install transformers sentencepiece sacremoses
```

### Issue: Language detection fails
- System uses script analysis (Devanagari vs Latin)
- For mixed language, defaults to detected majority
- Can manually specify `target_lang` parameter

### Issue: Gemma not responding
```bash
# Check Ollama is running
ollama list

# Restart Ollama
ollama serve

# Test model
ollama run gemma2:2b
```

---

## 📝 Examples

### Curl Request
```bash
curl -X POST "http://localhost:8000/api/generate-from-transcript" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation": "डॉक्टर: आज तुम्हाला कसे वाटते?\nरुग्ण: मला झोप येत नाही.",
    "phq8_score": 15,
    "severity": "moderate",
    "gender": "female"
  }'
```

### Python Requests
```python
import requests

response = requests.post(
    "http://localhost:8000/api/generate-from-transcript",
    json={
        "conversation": "डॉक्टर: आज तुम्हाला कसे वाटते?\nरुग्ण: मला झोप येत नाही.",
        "phq8_score": 15,
        "severity": "moderate",
        "gender": "female",
        "target_lang": "marathi"
    }
)

result = response.json()
print(result['english']['subjective'])
print(result['marathi']['subjective'])
```

---

## 🎓 B.Tech Project Notes

This multilingual system demonstrates:

1. **NLP Pipeline Design**
   - Language detection
   - Machine translation
   - Text generation
   - Multi-stage processing

2. **Clinical AI Application**
   - Medical documentation automation
   - Bilingual healthcare support
   - PHQ-8 integration

3. **Production-Ready Features**
   - REST API
   - Error handling
   - Auto-detection
   - Flexible input formats

4. **Open Source Stack**
   - No paid APIs
   - Runs on CPU
   - Reproducible results
   - Community models

---

## 📚 References

- **NLLB-200**: Meta's No Language Left Behind
- **Gemma 2B**: Google's lightweight LLM
- **IndicTrans2**: AI4Bharat's Indic language translator
- **DAIC-WOZ**: Depression screening dataset

---

✅ **Your system is now fully multilingual and ready to use!** 🎉
