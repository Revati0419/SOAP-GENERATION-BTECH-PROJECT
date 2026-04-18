#!/bin/bash

# Quick Start Script for Multilingual SOAP Generator
# This script tests the new multilingual functionality

echo "=========================================="
echo "🚀 Multilingual SOAP Generator - Quick Start"
echo "=========================================="
echo ""

# Check if Ollama is running
echo "1️⃣ Checking Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "   ✅ Ollama is running"
else
    echo "   ❌ Ollama is not running"
    echo "   Please start Ollama: ollama serve"
    exit 1
fi

# Check if Gemma is available
echo ""
echo "2️⃣ Checking Gemma 2B model..."
if ollama list | grep -q "gemma2:2b"; then
    echo "   ✅ Gemma 2B is available"
else
    echo "   ⚠️  Gemma 2B not found"
    echo "   Pulling model... (this may take a few minutes)"
    ollama pull gemma2:2b
fi

# Check Python dependencies
echo ""
echo "3️⃣ Checking Python dependencies..."
python3 -c "import fastapi; import transformers" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✅ Core dependencies installed"
else
    echo "   ⚠️  Installing missing dependencies..."
    pip install fastapi uvicorn transformers sentencepiece sacremoses
fi

# Run test suite
echo ""
echo "4️⃣ Running tests..."
echo "=========================================="
python3 scripts/test_multilingual_generator.py

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "📌 Next Steps:"
echo ""
echo "1. Start API Server:"
echo "   python3 api_server.py"
echo ""
echo "2. Test API:"
echo "   curl -X POST http://localhost:8000/api/generate-from-transcript \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"conversation\": \"डॉक्टर: तुम्हाला कसे वाटते?\"}'"
echo ""
echo "3. View API Docs:"
echo "   Open browser: http://localhost:8000/docs"
echo ""
echo "4. Read Documentation:"
echo "   cat docs/MULTILINGUAL_USAGE.md"
echo ""
echo "=========================================="
