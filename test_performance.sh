#!/bin/bash
# Quick performance test

echo "⚡ PERFORMANCE TEST - Optimized Server"
echo "======================================"
echo ""

# Test 1: Simple English (should be fastest)
echo "Test 1: Simple English input"
echo "----------------------------"
START=$(date +%s.%N)

curl -s -X POST "http://localhost:8000/api/generate-from-transcript" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation": "Doctor: How are you feeling? Patient: I am feeling depressed and cannot sleep.",
    "phq8_score": 12,
    "severity": "moderate",
    "gender": "female",
    "target_lang": "english"
  }' > /tmp/result1.json

END=$(date +%s.%N)
TIME=$(echo "$END - $START" | bc)
echo "⏱️  Time: ${TIME}s"
echo ""

# Test 2: Marathi input (with translation)
echo "Test 2: Marathi input (with translation)"
echo "----------------------------------------"
START=$(date +%s.%N)

curl -s -X POST "http://localhost:8000/api/generate-from-transcript" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation": "डॉक्टर: तुम्हाला कसे वाटते? रुग्ण: मला झोप येत नाही आणि खूप चिंता वाटते.",
    "phq8_score": 15,
    "severity": "moderately_severe",
    "gender": "male",
    "target_lang": "marathi"
  }' > /tmp/result2.json

END=$(date +%s.%N)
TIME=$(echo "$END - $START" | bc)
echo "⏱️  Time: ${TIME}s"
echo ""

# Test 3: Second request (should be faster - cached models)
echo "Test 3: Second English request (cached)"
echo "---------------------------------------"
START=$(date +%s.%N)

curl -s -X POST "http://localhost:8000/api/generate-from-transcript" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation": "Doctor: Any sleep problems? Patient: Yes, I wake up frequently at night.",
    "phq8_score": 10,
    "severity": "mild",
    "gender": "female",
    "target_lang": "english"
  }' > /tmp/result3.json

END=$(date +%s.%N)
TIME=$(echo "$END - $START" | bc)
echo "⏱️  Time: ${TIME}s"
echo ""

echo "======================================"
echo "✅ Tests complete!"
echo ""
echo "Results saved to:"
echo "  /tmp/result1.json"
echo "  /tmp/result2.json"
echo "  /tmp/result3.json"
echo ""
echo "Expected performance:"
echo "  Test 1 (English): 3-5 seconds"
echo "  Test 2 (Marathi): 5-8 seconds (includes translation)"
echo "  Test 3 (Cached):  2-4 seconds"
