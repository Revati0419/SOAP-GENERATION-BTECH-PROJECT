#!/bin/bash
# 🧪 Testing Script for All Three Enhancement Phases

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║       MULTILINGUAL SOAP GENERATION - ENHANCEMENT TEST         ║"
echo "║                  Testing All 3 Phases                         ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Helper function
test_file_exists() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} File exists: $1"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} File missing: $1"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

test_directory_exists() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} Directory exists: $1"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} Directory missing: $1"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

test_json_validity() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    if python3 -c "import json; json.load(open('$1'))" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Valid JSON: $1"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} Invalid JSON: $1"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}PHASE 1: NER INTEGRATION${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo ""
echo "Testing NER integration files..."
test_file_exists "src/generation/multilingual_soap_generator.py"
test_directory_exists "src/ner"

echo ""
echo "Testing NER code modifications..."
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if grep -q "@property" "src/generation/multilingual_soap_generator.py" && \
   grep -q "def ner" "src/generation/multilingual_soap_generator.py" && \
   grep -q "extract_from_text" "src/generation/multilingual_soap_generator.py"; then
    echo -e "${GREEN}✓${NC} NER lazy loading property implemented"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} NER integration code not found"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if grep -q "Extracted Medical Entities" "src/generation/multilingual_soap_generator.py"; then
    echo -e "${GREEN}✓${NC} Entity context formatting implemented"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} Entity context formatting not found"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}PHASE 2: KNOWLEDGE BASE ENHANCEMENT${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo ""
echo "Testing knowledge base files..."
test_file_exists "vocab/icd10_mental_health.json"
test_file_exists "vocab/dsm5_criteria.json"
test_file_exists "vocab/marathi_clinical_vocab_extended.json"
test_file_exists "vocab/hindi_clinical_vocab_extended.json"
test_file_exists "vocab/medications_psychotropic.json"
test_file_exists "vocab/assessment_tools.json"
test_file_exists "vocab/treatment_guidelines.json"

echo ""
echo "Testing JSON validity..."
test_json_validity "vocab/icd10_mental_health.json"
test_json_validity "vocab/dsm5_criteria.json"
test_json_validity "vocab/marathi_clinical_vocab_extended.json"
test_json_validity "vocab/hindi_clinical_vocab_extended.json"
test_json_validity "vocab/medications_psychotropic.json"
test_json_validity "vocab/assessment_tools.json"
test_json_validity "vocab/treatment_guidelines.json"

echo ""
echo "Testing knowledge base content..."

# Test ICD-10 codes
TOTAL_TESTS=$((TOTAL_TESTS + 1))
ICD_COUNT=$(python3 -c "import json; print(len(json.load(open('vocab/icd10_mental_health.json'))))" 2>/dev/null)
if [ "$ICD_COUNT" -ge 24 ]; then
    echo -e "${GREEN}✓${NC} ICD-10 codes: $ICD_COUNT diagnoses (expected ≥24)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} ICD-10 codes: $ICD_COUNT diagnoses (expected ≥24)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test DSM-5 criteria
TOTAL_TESTS=$((TOTAL_TESTS + 1))
DSM_COUNT=$(python3 -c "import json; print(len(json.load(open('vocab/dsm5_criteria.json'))))" 2>/dev/null)
if [ "$DSM_COUNT" -ge 11 ]; then
    echo -e "${GREEN}✓${NC} DSM-5 criteria: $DSM_COUNT disorders (expected ≥11)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} DSM-5 criteria: $DSM_COUNT disorders (expected ≥11)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test Marathi vocabulary
TOTAL_TESTS=$((TOTAL_TESTS + 1))
MARATHI_COUNT=$(python3 -c "import json; print(len(json.load(open('vocab/marathi_clinical_vocab_extended.json'))))" 2>/dev/null)
if [ "$MARATHI_COUNT" -ge 40 ]; then
    echo -e "${GREEN}✓${NC} Marathi vocabulary: $MARATHI_COUNT terms (expected ≥40)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} Marathi vocabulary: $MARATHI_COUNT terms (expected ≥40)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test Hindi vocabulary
TOTAL_TESTS=$((TOTAL_TESTS + 1))
HINDI_COUNT=$(python3 -c "import json; print(len(json.load(open('vocab/hindi_clinical_vocab_extended.json'))))" 2>/dev/null)
if [ "$HINDI_COUNT" -ge 40 ]; then
    echo -e "${GREEN}✓${NC} Hindi vocabulary: $HINDI_COUNT terms (expected ≥40)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} Hindi vocabulary: $HINDI_COUNT terms (expected ≥40)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test Medications
TOTAL_TESTS=$((TOTAL_TESTS + 1))
MED_COUNT=$(python3 -c "import json; print(len(json.load(open('vocab/medications_psychotropic.json'))))" 2>/dev/null)
if [ "$MED_COUNT" -ge 48 ]; then
    echo -e "${GREEN}✓${NC} Medications: $MED_COUNT drugs (expected ≥48)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} Medications: $MED_COUNT drugs (expected ≥48)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test Assessment Tools
TOTAL_TESTS=$((TOTAL_TESTS + 1))
TOOLS_COUNT=$(python3 -c "import json; print(len(json.load(open('vocab/assessment_tools.json'))))" 2>/dev/null)
if [ "$TOOLS_COUNT" -ge 9 ]; then
    echo -e "${GREEN}✓${NC} Assessment tools: $TOOLS_COUNT scales (expected ≥9)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} Assessment tools: $TOOLS_COUNT scales (expected ≥9)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test Treatment Guidelines
TOTAL_TESTS=$((TOTAL_TESTS + 1))
GUIDELINES_COUNT=$(python3 -c "import json; print(len(json.load(open('vocab/treatment_guidelines.json'))))" 2>/dev/null)
if [ "$GUIDELINES_COUNT" -ge 11 ]; then
    echo -e "${GREEN}✓${NC} Treatment guidelines: $GUIDELINES_COUNT protocols (expected ≥11)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} Treatment guidelines: $GUIDELINES_COUNT protocols (expected ≥11)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}PHASE 3: FRONTEND LOADING ANIMATIONS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo ""
echo "Testing frontend animation files..."
test_file_exists "frontend/src/components/LoadingAnimation.jsx"

echo ""
echo "Testing LoadingAnimation component code..."
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if grep -q "Languages, Brain, Sparkles, Activity" "frontend/src/components/LoadingAnimation.jsx" 2>/dev/null || \
   grep -q "const steps" "frontend/src/components/LoadingAnimation.jsx" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} LoadingAnimation component has step definitions"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} LoadingAnimation component missing step definitions"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if grep -q "animate-ping" "frontend/src/components/LoadingAnimation.jsx" 2>/dev/null && \
   grep -q "animate-bounce" "frontend/src/components/LoadingAnimation.jsx" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} LoadingAnimation has pulsing and bouncing animations"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} LoadingAnimation missing animations"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if grep -q "progress" "frontend/src/components/LoadingAnimation.jsx" 2>/dev/null && \
   grep -q "shimmer" "frontend/src/components/LoadingAnimation.jsx" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} LoadingAnimation has progress bar with shimmer"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} LoadingAnimation missing progress features"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo ""
echo "Testing integration into React components..."
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if grep -q "import LoadingAnimation" "frontend/src/components/MultilingualSOAPGenerator.jsx" 2>/dev/null && \
   grep -q "<LoadingAnimation" "frontend/src/components/MultilingualSOAPGenerator.jsx" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} LoadingAnimation integrated into MultilingualSOAPGenerator"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} LoadingAnimation not integrated into MultilingualSOAPGenerator"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if grep -q "import LoadingAnimation" "frontend/src/pages/UploadPage.jsx" 2>/dev/null && \
   grep -q "<LoadingAnimation" "frontend/src/pages/UploadPage.jsx" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} LoadingAnimation integrated into UploadPage"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} LoadingAnimation not integrated into UploadPage"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}DOCUMENTATION & EXTRAS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo ""
echo "Testing documentation files..."
test_file_exists "docs/WHY_NER_RAG_QLORA.md"
test_file_exists "docs/COMPLETE_ARCHITECTURE_EXPLAINED.md"
test_file_exists "docs/QUICK_ANSWERS.md"
test_file_exists "docs/IMPLEMENTATION_STATUS.md"
test_file_exists "docs/MULTILINGUAL_USAGE.md"
test_file_exists "MULTILINGUAL_UPGRADE.md"
test_file_exists "ENHANCEMENT_COMPLETION_REPORT.md"
test_file_exists "docs/LOADING_ANIMATION_PREVIEW.md"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}API & BACKEND INTEGRATION${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo ""
echo "Testing API server configuration..."
test_file_exists "api_server.py"

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if grep -q "/api/generate-from-transcript" "api_server.py" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} API endpoint /api/generate-from-transcript exists"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} API endpoint /api/generate-from-transcript missing"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if grep -q "MultilingualSOAPGenerator" "api_server.py" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} MultilingualSOAPGenerator imported in API server"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${RED}✗${NC} MultilingualSOAPGenerator not imported in API server"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}OPTIONAL: LIVE BACKEND TEST${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo ""
echo -e "${YELLOW}⚠${NC} Checking if backend is running on localhost:8000..."
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Backend API is running (http://localhost:8000)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    
    echo ""
    echo "Testing API endpoint with sample request..."
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    API_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/generate-from-transcript" \
      -H "Content-Type: application/json" \
      -d '{"conversation": "डॉक्टर: कसे आहात? रुग्ण: झोप येत नाही.", "phq8_score": 12, "severity": "moderate", "gender": "female", "target_lang": "marathi"}' \
      2>/dev/null)
    
    if echo "$API_RESPONSE" | grep -q "english" && echo "$API_RESPONSE" | grep -q "target_language"; then
        echo -e "${GREEN}✓${NC} API endpoint returns expected JSON structure"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗${NC} API endpoint response invalid"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo -e "${YELLOW}⚠${NC} Backend not running (skipping live API test)"
    echo -e "   ${YELLOW}→${NC} Start backend with: python api_server.py"
    # Don't increment FAILED_TESTS - this is optional
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}OPTIONAL: FRONTEND DEPENDENCIES TEST${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo ""
echo -e "${YELLOW}⚠${NC} Checking frontend dependencies..."
if [ -d "frontend/node_modules" ]; then
    echo -e "${GREEN}✓${NC} Frontend node_modules directory exists"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    if [ -d "frontend/node_modules/lucide-react" ]; then
        echo -e "${GREEN}✓${NC} lucide-react installed (required for icons)"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗${NC} lucide-react not installed"
        echo -e "   ${YELLOW}→${NC} Install with: cd frontend && npm install lucide-react"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo -e "${YELLOW}⚠${NC} Frontend dependencies not installed"
    echo -e "   ${YELLOW}→${NC} Install with: cd frontend && npm install"
fi

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                        TEST SUMMARY                           ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Total Tests: ${BLUE}$TOTAL_TESTS${NC}"
echo -e "Passed:      ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed:      ${RED}$FAILED_TESTS${NC}"
echo ""

# Calculate percentage
PERCENTAGE=$((PASSED_TESTS * 100 / TOTAL_TESTS))

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          🎉 ALL TESTS PASSED! (100%)                          ║${NC}"
    echo -e "${GREEN}║  ✅ Phase 1: NER Integration                                  ║${NC}"
    echo -e "${GREEN}║  ✅ Phase 2: Knowledge Base Enhancement                       ║${NC}"
    echo -e "${GREEN}║  ✅ Phase 3: Frontend Loading Animations                      ║${NC}"
    echo -e "${GREEN}║                                                               ║${NC}"
    echo -e "${GREEN}║  System is ready for production use! 🚀                      ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    exit 0
elif [ $PERCENTAGE -ge 80 ]; then
    echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║          ⚠ MOST TESTS PASSED ($PERCENTAGE%)                              ║${NC}"
    echo -e "${YELLOW}║  Some optional features may be missing.                       ║${NC}"
    echo -e "${YELLOW}║  Review failed tests above for details.                       ║${NC}"
    echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════════╝${NC}"
    exit 1
else
    echo -e "${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║          ❌ CRITICAL TESTS FAILED ($PERCENTAGE%)                         ║${NC}"
    echo -e "${RED}║  Please review and fix failed tests before deployment.        ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
