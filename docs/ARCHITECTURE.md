# SOAP Note Generator — System Architecture
### Bilingual Clinical NLP Pipeline for Marathi Mental Health Conversations
**Team:** Mukta Naik · Sujal Nandapurkar · Revati Patare · Tanuja Patil  
**Roll Nos:** 612203122 · 612203123 · 612203131 · 612203138

---

## Table of Contents
1. [System Overview](#1-system-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Pipeline Stages](#3-pipeline-stages)
4. [Two-Phase Auto-Detection](#4-two-phase-auto-detection)
5. [API Server Architecture](#5-api-server-architecture)
6. [Frontend Architecture](#6-frontend-architecture)
7. [QLoRA Fine-Tuning](#7-qlora-fine-tuning)
8. [Data Flow — End to End](#8-data-flow--end-to-end)
9. [Technology Stack](#9-technology-stack)
10. [Output Format](#10-output-format)

---

## 1. System Overview

The system converts **unstructured Marathi / Hindi / English mental health conversations**
into **structured bilingual SOAP clinical notes** (English + Marathi/Hindi) using a
four-stage NLP pipeline: **NER → RAG → LLM → Translation**.

```
Input: Raw conversation JSON (Marathi dialects, English, or mixed)
         ↓
┌──────────────────────────────────────────────────────────┐
│  PHASE AUTO-DETECTOR                                      │
│  Phase 1 (bilingual data): text_en present → use English  │
│  Phase 2 (Marathi-only):   text_en absent  → full pipeline│
└──────────────────────────────────────────────────────────┘
         ↓
   NER → RAG → Gemma 2B → NLLB Translation
         ↓
Output: { soap_english: {...}, soap_marathi: {...}, metadata }
```

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND  (React + Vite)                     │
│   Upload JSON ──► Start Pipeline ──► Loading Animation ──► Viewer   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │  HTTP POST multipart/form-data
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FastAPI  API SERVER  :8000                      │
│                                                                      │
│  /api/generate-from-json       (upload session JSON file)           │
│  /api/generate-from-transcript (raw text input)                     │
│  /health    /                                                        │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │            Parallel Model Loading at Startup                  │   │
│  │   NLLB-200 ║ IndicNER(rule) ║ ChromaDB ║ Gemma via Ollama   │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────┬───────────────────────────────────────────────────────────┘
           │  calls
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│               MultilingualSOAPGenerator  (Python class)              │
│                                                                      │
│  generate_from_session(session_data, target_lang)                   │
│         │                                                            │
│         ├─► _extract_turns()   pick dialect → list of turns         │
│         ├─► LanguageDetector.detect_from_turns()                    │
│         ├─► Phase 1 or Phase 2 branch                               │
│         │         │                                                  │
│         │    [Phase 1]  format_turns_english → Gemma                │
│         │    [Phase 2]  IndicNER → RAG → NLLB(MR→EN) → Gemma       │
│         │                                                            │
│         └─► _translate_soap()  Gemma output → NLLB → Marathi       │
│                                                                      │
│  Returns: MultilingualSOAPNote.to_dict()                            │
│     { soap_english, soap_marathi, metadata }                        │
└─────────────────────────────────────────────────────────────────────┘
           │
    ┌──────┴───────┬───────────────┬──────────────┐
    ▼              ▼               ▼              ▼
 IndicNER       ChromaDB       Gemma 2B        NLLB-200
(rule-based)   (RAG store)    via Ollama     (translation)
```

---

## 3. Pipeline Stages

### Stage 0 — Dataset & Input

**Source:** DAIC-WOZ mental health interview corpus (English)

```
DAIC-WOZ (English transcripts)
      │
      ▼  parse_transcripts.py
  Parsed turns  {role, text_en, phq8_score, severity, gender}
      │
      ▼  translate.py  (NLLB-200)
  Marathi translations  {text_en, text (Marathi)}
      │
      ▼  transform_dialects.py
  5 Dialect variants per session:
    standard_pune / mumbai / vidarbha / marathwada / konkan
      │
      ▼  assemble_dataset.py
  Final: data/dialect_marathi/NNN_marathi.json
```

**Scale:** 182 sessions × 5 dialects = **910 conversation files**

---

### Stage 1 — NER (Named Entity Recognition)

**Goal:** Extract clinical entities from the conversation before passing to the LLM.

**Model:** IndicNER (rule-based patterns for Marathi + English)

| Entity Type | Example |
|-------------|---------|
| SYMPTOM | insomnia, loss of appetite |
| EMOTION | sadness, anxiety, hopelessness |
| DURATION | two weeks, since last month |
| SEVERITY | mild, moderate, severe |
| MEDICATION | antidepressants, sleeping pills |
| CONDITION | depression, PTSD |
| TRIGGER | job loss, bereavement |

**Output fed to RAG + Gemma:**
```json
{ "symptoms": ["insomnia","anxiety"],
  "emotions":  ["sadness"],
  "duration":  ["two weeks"],
  "severity":  ["moderate"] }
```

---

### Stage 2 — RAG (Retrieval-Augmented Generation)

**Goal:** Retrieve relevant clinical vocabulary and guidelines from a vector database
to augment the LLM prompt with accurate medical context.

```
┌────────────────────────────────────────────────┐
│           ChromaDB Vector Store                 │
│   Indexed:  DSM-5 criteria                     │
│             ICD-10 mental health codes         │
│             Psychotropic medications           │
│             Treatment guidelines               │
│             Marathi + Hindi clinical vocab     │
└────────────────────────────────────────────────┘
         ▲
  NER entities → MiniLM-L6 embedding → cosine search
         │
         ▼  top-5 relevant snippets
  Injected into Gemma prompt
```

---

### Stage 3 — LLM SOAP Generation (Gemma 2B)

**Model:** `gemma2:2b` via Ollama

**Prompt:**
```
You are a clinical psychologist generating a SOAP note.

CONVERSATION:
Doctor: How are you feeling today?
Patient: मला झोप येत नाही. खूप चिंता वाटते.
...

EXTRACTED ENTITIES:  insomnia, anxiety, two weeks, moderate
CLINICAL CONTEXT:    [DSM-5 MDD criteria from RAG]
PHQ-8 Score: 14 (moderate)

Generate SOAP note: SUBJECTIVE / OBJECTIVE / ASSESSMENT / PLAN
```

**Output parsed into 4 sections:**
```json
{
  "subjective":  "Patient reports inability to sleep for two weeks...",
  "objective":   "Patient appeared anxious, flat affect observed...",
  "assessment":  "Moderate depression (PHQ-8: 14)...",
  "plan":        "Initiate CBT, weekly follow-up..."
}
```

---

### Stage 4 — Translation (NLLB-200)

**Model:** `facebook/nllb-200-distilled-600M`

| Direction | NLLB codes |
|-----------|-----------|
| English → Marathi | `eng_Latn` → `mar_Deva` |
| Marathi → English | `mar_Deva` → `eng_Latn` |
| English → Hindi | `eng_Latn` → `hin_Deva` |

Each of the 4 SOAP sections is translated individually for quality.

---

## 4. Two-Phase Auto-Detection

```
Input session turns
        │
   Does any turn have text_en ?
        │
   ┌────┴────┐
  YES        NO
   │          │
PHASE 1    PHASE 2
   │          │
Use text_en   Use text (Marathi)
(English)     IndicNER on Marathi
↓             ↓
Gemma         RAG retrieval
directly      ↓
              NLLB: MR → EN
              ↓
              Gemma (English input)
              ↓
Both:  NLLB: EN → Marathi  → bilingual SOAP output
```

- **Phase 1** — training/research data (text_en present) → ~70s
- **Phase 2** — real clinical deployment (Marathi-only audio) → ~90s

---

## 5. API Server Architecture

**File:** `api_server_complete.py` | **Port:** `8000` | **Framework:** FastAPI

### Parallel Startup
```python
with ThreadPoolExecutor(max_workers=4) as ex:
    f_nllb  = ex.submit(load_nllb)      # NLLB-200
    f_ner   = ex.submit(load_ner)       # IndicNER
    f_rag   = ex.submit(load_chromadb)  # ChromaDB
    f_gemma = ex.submit(verify_gemma)   # Gemma via Ollama
```
All models ready in ~15s (vs ~60s sequential).

### Endpoints

| Method | Endpoint | Input | Use |
|--------|----------|-------|-----|
| GET | `/health` | — | Health check |
| POST | `/api/generate-from-json` | JSON file + target_lang | Upload session |
| POST | `/api/generate-from-transcript` | JSON body | Raw text |

### Response
```json
{
  "soap_english":    { "subjective": "...", "objective": "...",
                       "assessment": "...", "plan": "..." },
  "soap_marathi":    { "subjective": "रुग्ण सांगतो...", ... },
  "session_id":      "492",
  "input_language":  "marathi",
  "target_language": "marathi",
  "metadata":        { "processing_time": "72.83s" },
  "entities":        { "symptoms": [...] }
}
```

---

## 6. Frontend Architecture

**Stack:** React 18 + Vite + TailwindCSS | **Port:** `5173`

```
UploadPage.jsx
  ├── Drag & drop JSON file
  ├── POST → /api/generate-from-json
  ├── LoadingAnimation overlay (during ~70s processing)
  └── SoapNoteViewer on success

SoapNoteViewer.jsx
  ├── Reads: soap_english + soap_{targetLang}
  ├── Side-by-side bilingual layout
  │   ┌──────────────┬───────────────┐
  │   │ S  English   │ S  मराठी      │
  │   │ O  English   │ O  मराठी      │
  │   │ A  English   │ A  मराठी      │
  │   │ P  English   │ P  मराठी      │
  │   └──────────────┴───────────────┘
  └── NER entities tag cloud
```

---

## 7. QLoRA Fine-Tuning

**Why QLoRA?**

| Method | Trainable Params | Memory |
|--------|-----------------|--------|
| Full fine-tune | 2.5B (100%) | ~20 GB |
| QLoRA | 1.8M  (0.07%) | ~4 GB |

**LoRA injected into:** `q_proj`, `k_proj`, `v_proj`, `o_proj`  
**rank=8, alpha=16, dropout=0.05**

**Training data:**
```
data/training/train.jsonl  — 34 therapy → SOAP examples
data/training/val.jsonl    —  9 examples

Format:
{ "prompt":   "You are a clinical psychologist... [conversation]",
  "response": "## SOAP Note\n**SUBJECTIVE:**..." }
```

**Output:** `outputs/qlora_v1/adapter_model.safetensors` (~16 MB adapter)  
Loaded on top of frozen base model at inference.

---

## 8. Data Flow — End to End

```
User uploads 492_marathi.json (5 dialects, 295 turns each)
    │
    ▼  POST /api/generate-from-json  target_lang=marathi
    │
    ▼  _extract_turns()  → standard_pune dialect, 295 turns
    ▼  detect_from_turns() → "marathi"
    ▼  has_english = True  → PHASE 1
    │
    ▼  _format_turns_english()  → first 20 + last 20 turns, English
    ▼  IndicNER  → {insomnia, anxiety, sadness, two weeks}
    ▼  ChromaDB  → top-5 DSM-5 / clinical guideline snippets
    │
    ▼  Gemma 2B  (streaming, ~60s)
    ▼  _parse_soap_sections()  → {subjective, objective, assessment, plan}
    │
    ▼  NLLB-200 each section EN → mar_Deva  (~12s)
    │
    ▼  to_dict() + _normalise_response()
    │
    ▼  JSON → SoapNoteViewer → bilingual display
    
✅ Total: ~72 seconds
```

---

## 9. Technology Stack

| Layer | Technology | Role |
|-------|-----------|------|
| Frontend | React 18 + Vite | UI |
| Styling | TailwindCSS 3 | Design |
| API | FastAPI + Uvicorn | REST server |
| LLM | Gemma 2B (Ollama) | SOAP generation |
| Translation | NLLB-200-600M | EN ↔ MR/HI |
| NER | IndicNER (rule-based) | Entity extraction |
| Vector DB | ChromaDB | RAG store |
| Embeddings | MiniLM-L6-v2 | Semantic search |
| Fine-tuning | PEFT / LoRA | Adapter training |
| Dataset | DAIC-WOZ | Source corpus |
| Language | Python 3.10 | Backend |

---

## 10. Output Format

```
soap_english / soap_marathi
├── subjective   Patient's reported symptoms, history, mood
├── objective    Clinician observations: affect, speech, behavior
├── assessment   Diagnosis, PHQ-8, risk level
└── plan         CBT, medication, follow-up, safety planning

Dialect coverage: standard_pune · mumbai · vidarbha · marathwada · konkan
Sessions: 182 × 5 dialects = 910 files
```

---
*Architecture v2.0 — March 2026 | COEP Technological University*
