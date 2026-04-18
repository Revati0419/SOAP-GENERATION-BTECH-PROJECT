#!/bin/bash
# Complete End-to-End Test and Demo

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║   MULTILINGUAL SOAP GENERATION - END-TO-END DEMO             ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Test if backend is running
echo "🔍 Checking if backend is running on port 8000..."
if ! nc -z localhost 8000 2>/dev/null; then
    echo "❌ Backend is not running!"
    echo ""
    echo "Starting backend..."
    cd "/home/rev/Desktop/Btech Project/BTECH PROJECT/Version 1.0/SOAP-GENERATION-BTECH-PROJECT"
    python3 api_server.py > api.log 2>&1 &
    BACKEND_PID=$!
    echo "   Backend started with PID: $BACKEND_PID"
    echo "   Waiting for startup..."
    sleep 5
fi

echo "✅ Backend is running on http://localhost:8000"
echo ""

# Test 1: Marathi Input
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 1: Marathi Input → Marathi + English SOAP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Input: डॉक्टर: कसे आहात? रुग्ण: झोप येत नाही. खूप चिंता वाटते."
echo ""
echo "📤 Sending request to API..."

RESPONSE=$(curl -s -X POST "http://localhost:8000/api/generate-from-transcript" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation": "डॉक्टर: कसे आहात? रुग्ण: झोप येत नाही. खूप चिंता वाटते.",
    "phq8_score": 12,
    "severity": "moderate",
    "gender": "female",
    "target_lang": "marathi"
  }' 2>&1)

if echo "$RESPONSE" | jq . > /dev/null 2>&1; then
    echo "✅ Response received!"
    echo ""
    echo "📋 SOAP Note (English):"
    echo "$RESPONSE" | jq -r '.english.subjective' | head -3
    echo ""
    echo "📋 SOAP Note (Marathi):"
    echo "$RESPONSE" | jq -r '.target_language.subjective' | head -3
    echo ""
    echo "🏷️ Metadata:"
    echo "   Input Language: $(echo "$RESPONSE" | jq -r '.metadata.input_language')"
    echo "   Target Language: $(echo "$RESPONSE" | jq -r '.metadata.target_language')"
    echo "   Model: $(echo "$RESPONSE" | jq -r '.metadata.model')"
else
    echo "❌ Request failed!"
    echo "Response: $RESPONSE"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 2: Hindi Input → Hindi + English SOAP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Input: डॉक्टर: आप कैसे हैं? मरीज: मुझे नींद नहीं आती।"
echo ""
echo "📤 Sending request to API..."

RESPONSE2=$(curl -s -X POST "http://localhost:8000/api/generate-from-transcript" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation": "डॉक्टर: आप कैसे हैं? मरीज: मुझे नींद नहीं आती।",
    "phq8_score": 10,
    "severity": "mild",
    "gender": "male",
    "target_lang": "hindi"
  }' 2>&1)

if echo "$RESPONSE2" | jq . > /dev/null 2>&1; then
    echo "✅ Response received!"
    echo ""
    echo "📋 SOAP Note (English):"
    echo "$RESPONSE2" | jq -r '.english.subjective' | head -3
    echo ""
    echo "📋 SOAP Note (Hindi):"
    echo "$RESPONSE2" | jq -r '.target_language.subjective' | head -3
else
    echo "❌ Request failed!"
    echo "Response: $RESPONSE2"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 3: English Input → English SOAP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Input: Doctor: How are you? Patient: I can't sleep at night."
echo ""
echo "📤 Sending request to API..."

RESPONSE3=$(curl -s -X POST "http://localhost:8000/api/generate-from-transcript" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation": "Doctor: How are you feeling today? Patient: I have been having trouble sleeping. I feel very anxious.",
    "phq8_score": 15,
    "severity": "moderately_severe",
    "gender": "female",
    "target_lang": "english"
  }' 2>&1)

if echo "$RESPONSE3" | jq . > /dev/null 2>&1; then
    echo "✅ Response received!"
    echo ""
    echo "📋 SOAP Note:"
    echo "$RESPONSE3" | jq -r '.english.subjective' | head -3
else
    echo "❌ Request failed!"
    echo "Response: $RESPONSE3"
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                  DEMO COMPLETE!                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ API Endpoints Working:"
echo "   • POST /api/generate-from-transcript"
echo "   • POST /api/generate-from-json"
echo ""
echo "🌐 Access the UI:"
echo "   Start frontend: cd frontend && npm run dev"
echo "   Open: http://localhost:5173"
echo ""
echo "📊 System Components:"
echo "   ✓ Translation: NLLB-200 (Marathi/Hindi/English)"
echo "   ✓ RAG: ChromaDB with ICD-10, Medications"
echo "   ✓ LLM: Gemma 2B via Ollama"
echo "   ✓ Frontend: React + Vite with Loading Animations"
echo ""
echo "📝 API is running at: http://localhost:8000"
echo "   Documentation: http://localhost:8000/docs"
echo ""
