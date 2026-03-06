# Pipeline Guide: Understanding the Two Entry Points

## Overview

This project has **TWO SEPARATE PIPELINES** with different purposes:

```
📦 SOAP-GENERATION-BTECH-PROJECT/
├── run_pipeline.py          ← DATA PREPARATION (Stage 1-4)
└── scripts/
    └── run_pipeline.py      ← SOAP GENERATION (Stage 5-9)
```

---

## Pipeline 1: Data Preparation (Root)

**File:** `/run_pipeline.py`  
**Purpose:** Prepare the DAIC-WOZ dataset for SOAP generation  
**Status:** ✅ COMPLETE (already executed)

### What it does:

```
Stage 1: DOWNLOAD  → Fetch DAIC-WOZ transcripts from source
Stage 2: PARSE     → Extract conversations + PHQ-8 labels
Stage 3: TRANSLATE → English → Marathi/Hindi (3 style variants)
Stage 4: ASSEMBLE  → Combine into final dataset (CSV + JSON)
```

### Usage Examples:

```bash
# Full pipeline (all 182 sessions)
python run_pipeline.py

# Use local sample only (no download)
python run_pipeline.py --sample

# Process specific sessions
python run_pipeline.py --ids 301 302 303

# Only Hindi translation
python run_pipeline.py --sample --lang hindi

# Skip stages (e.g., already downloaded)
python run_pipeline.py --skip download parse

# Test with first 10 sessions
python run_pipeline.py --limit 10
```

### Output:

- `data/raw/` - Original DAIC-WOZ transcripts
- `data/parsed/` - Parsed conversations (**deleted during cleanup**)
- `data/translated/` - Base translations (182 files)
- `data/dialect_marathi/` - Dialect variations (910 files = 182 × 5 dialects)

---

## Pipeline 2: SOAP Generation (Scripts)

**File:** `/scripts/run_pipeline.py`  
**Purpose:** Generate bilingual clinical SOAP notes from conversations  
**Status:** 🔄 READY TO UPGRADE (currently using v2)

### What it does:

```
Stage 5: LOAD      → Read translated conversation
Stage 6: NER       → Extract medical entities (symptoms, emotions, etc.)
Stage 7: RAG       → Retrieve clinical terminology from knowledge base
Stage 8: GENERATE  → Create English SOAP note (Gemma 2B)
Stage 9: TRANSLATE → English → Marathi (IndicTrans2)
```

### Current Architecture (v2):

```
[Conversation] → [Gemma 2B] → [Google Translate API] → [Bilingual SOAP]
                    ↓
            English SOAP Note
```

### Target Architecture (v3 - TO IMPLEMENT):

```
[Conversation] → [IndicNER] → [ChromaDB RAG] → [Gemma 2B] → [IndicTrans2] → [Bilingual SOAP]
                    ↓              ↓               ↓              ↓
              Medical Entities  Clinical Terms  English SOAP  Marathi SOAP
```

### Usage Examples:

```bash
# Generate SOAP for one session
python scripts/run_pipeline.py --session_id 300 --dialect standard_pune

# Generate for specific sessions
python scripts/run_pipeline.py --sessions 300 301 302

# Generate all 182 SOAP notes
python scripts/run_pipeline.py --all

# Use specific dialect
python scripts/run_pipeline.py --session_id 300 --dialect mumbai

# Custom model configuration
python scripts/run_pipeline.py --session_id 300 --model gemma2:2b --temperature 0.3
```

### Output:

- `data/soap_notes/` - Generated bilingual clinical notes
- Each file: `soap_note_{session_id}_{dialect}.md`

---

## Key Differences

| Aspect | Pipeline 1 (Root) | Pipeline 2 (Scripts) |
|--------|-------------------|----------------------|
| **Purpose** | Dataset preparation | Clinical documentation |
| **Input** | DAIC-WOZ source data | Translated conversations |
| **Output** | Translated transcripts | Bilingual SOAP notes |
| **Models** | Google Translate API | Gemma 2B + IndicTrans2 + NER + RAG |
| **Status** | ✅ Already executed | 🔄 Ready for v3 upgrade |
| **Run frequency** | Once (dataset setup) | 182 times (one per session) |
| **Execution time** | ~2-3 hours (full dataset) | ~2 minutes per session |

---

## Execution Order

For a complete workflow from scratch:

```bash
# Step 1: Prepare dataset (ONLY RUN ONCE)
python run_pipeline.py --sample

# Step 2: Generate SOAP notes (RUN FOR EACH SESSION)
python scripts/run_pipeline.py --session_id 300 --dialect standard_pune
python scripts/run_pipeline.py --session_id 301 --dialect standard_pune
# ... repeat for all 182 sessions

# OR: Generate all at once
python scripts/run_pipeline.py --all
```

---

## Recommendation: Keep Both Files

✅ **DO NOT RENAME OR MERGE**

Both pipelines serve distinct purposes in the workflow:

1. **`run_pipeline.py`** (root) = Data prep infrastructure  
   - Rarely executed (only when adding new data)
   - Different command-line interface
   - Focused on translation & dialect generation

2. **`scripts/run_pipeline.py`** = Clinical documentation generation  
   - Frequently executed (main production pipeline)
   - Includes ML models (NER, RAG, LLM)
   - Outputs actual deliverables (SOAP notes)

**Alternative naming** (if confusion persists):
- Root: `prepare_dataset.py` ← More descriptive
- Scripts: Keep as `run_pipeline.py` (main entry point)

---

## Current Status

### Pipeline 1 (Data Prep):
✅ All 182 sessions downloaded  
✅ Parsed and translated to Marathi  
✅ 5 dialect variations created (910 files total)  
✅ No further action needed

### Pipeline 2 (SOAP Generation):
🔄 Using v2 (Gemma 2B + Google API)  
⏭️ Need to upgrade to v3 (full open-source stack)  
📊 Generated 3 test SOAP notes (300, 301, 302)  
🎯 Target: 182 bilingual SOAP notes

---

## Next Steps

1. ✅ **Config updated** - `configs/config.yaml` now reflects new architecture
2. ⏭️ **Install models** - IndicTrans2, IndicNER, ChromaDB
3. ⏭️ **Create v3** - New pipeline with NER → RAG → LLM → Translate
4. ⏭️ **Test v3** - Validate on sessions 300-305
5. ⏭️ **Generate all** - Run on all 182 sessions
6. ⏭️ **Validate** - Quality checks (automated + manual 20 sessions)
7. ⏭️ **Train QLoRA** - Human-in-the-loop feedback

---

**Last Updated:** March 5, 2026  
**Related Files:**
- `README.md` - Complete project documentation
- `configs/config.yaml` - Model configurations
- `pipeline/generate_soap_v2.py` - Current working generator
- `scripts/validate_soap_notes.py` - Quality validation
