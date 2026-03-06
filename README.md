# SOAP Note Generation for Mental Health - Complete System# SOAP Note Generation for Mental Health - Complete System# SOAP Generation in Indic Languages — Dataset Pipeline



> **Fully Open-Source, End-to-End Pipeline for Bilingual Clinical Documentation**  

> Specialized for Indian Languages (Marathi/Hindi) with Human-in-the-Loop Learning

> **Fully Open-Source, End-to-End Pipeline for Bilingual Clinical Documentation**  > **Phase 1** — Build a bilingual (Hindi + Marathi) doctor-patient mental health conversation dataset from DAIC-WOZ transcripts.

---

> Specialized for Indian Languages (Marathi/Hindi) with Human-in-the-Loop Learning> **Phase 2** (future) — Train a model to generate SOAP notes from those conversations.

## 📋 Table of Contents



1. [Project Overview](#-project-overview)

2. [Quick Start Guide](#-quick-start-guide)------

3. [Installation & Setup](#-installation--setup)

4. [Models to Download](#-models-to-download)

5. [Usage - Step by Step](#-usage---step-by-step)

6. [Architecture](#-architecture)## 📋 Table of Contents## Project Overview

7. [Training with QLoRA](#-training-with-qlora)

8. [Validation Strategy](#-validation-strategy)

9. [Project Structure](#-project-structure)

10. [B.Tech Project Contributions](#-btech-project-contributions)1. [Project Overview](#project-overview)The [DAIC-WOZ dataset](https://dcapswoz.ict.usc.edu/wwwdaicwoz/) contains clinical interview recordings in English between a virtual interviewer (Ellie) and participants, annotated with PHQ-8 depression scores.



---2. [Architecture](#architecture)



## 🎯 Project Overview3. [Models & Components](#models--components)This pipeline:



### What This Does4. [Dataset](#dataset)1. **Downloads** the DAIC-WOZ transcripts (only `_TRANSCRIPT.csv` from each ZIP — audio/video skipped)



Generates clinical SOAP notes from mental health interview conversations in **bilingual format** (English + Marathi/Hindi):5. [Project Structure](#project-structure)2. **Parses** them and attaches PHQ-8 labels



- **S**ubjective: Patient's reported symptoms and concerns6. [Installation](#installation)3. **Translates** English → Hindi & Marathi with **three linguistic style layers**

- **O**bjective: Clinician's observations (appearance, behavior, affect)

- **A**ssessment: Diagnosis, PHQ-8 score, risk assessment7. [Usage](#usage)4. **Assembles** a final dataset ready for model training

- **P**lan: Treatment recommendations, follow-up, safety planning

8. [Training with QLoRA](#training-with-qlora)

### Why This Matters

9. [Validation Strategy](#validation-strategy)---

- **Language Barrier**: Most Indian patients don't speak English fluently

- **Clinical Efficiency**: Automates time-consuming documentation10. [B.Tech Project Contributions](#btech-project-contributions)

- **Quality Healthcare**: Standardized, comprehensive clinical notes

- **Continuous Learning**: Improves from doctor feedback using QLoRA## Why Three Style Layers?



### Key Features---



✅ **100% Open Source** - No API dependencies, fully reproducible  Real Indian patients don't speak in formal translated Hindi. They use:

✅ **Bilingual Output** - English + Marathi (Hindi support ready)  

✅ **Clinical Accuracy** - NER + RAG for medical terminology  ## 🎯 Project Overview

✅ **Resource Efficient** - Runs on CPU, QLoRA training feasible on 16GB RAM  

✅ **Continual Learning** - Human-in-the-loop with incremental retraining  | Style | Example (Hindi) | Example (Marathi) |



---### What This Does|---|---|---|



## 🚀 Quick Start Guide| `formal_translated` | *मुझे अवसाद है* | *मला नैराश्य आहे* |



### PrerequisitesGenerates clinical SOAP notes from mental health interview conversations in **bilingual format** (English + Marathi/Hindi):| `colloquial` | *मन बहुत उदास रहता है* | *मन खूप उदास राहतं* |



- **OS**: Linux (Ubuntu 20.04+) or macOS| `code_mixed` | *मुझे depression feel हो रहा है* | *मला depression सारखं वाटतंय* |

- **Python**: 3.10+ (Python 3.10.12 tested)

- **RAM**: 16GB minimum (32GB recommended for full training)- **S**ubjective: Patient's reported symptoms and concerns

- **Disk Space**: 60GB free (for models, data, and cache)

- **Internet**: Required for initial model downloads- **O**bjective: Clinician's observations (appearance, behavior, affect)---



### 5-Minute Quick Test- **A**ssessment: Diagnosis, PHQ-8 score, risk assessment



```bash- **P**lan: Treatment recommendations, follow-up, safety planning## File Structure

# 1. Clone/Navigate to repository

cd /path/to/SOAP-GENERATION-BTECH-PROJECT



# 2. Create virtual environment### Why This Matters```

python3 -m venv .venv

source .venv/bin/activate  # On Windows: .venv\Scripts\activateSOAP-GENERATION-BTECH-PROJECT/



# 3. Install dependencies- **Language Barrier**: Most Indian patients don't speak English fluently│

pip install -r requirements.txt

- **Clinical Efficiency**: Automates time-consuming documentation├── pipeline/

# 4. Install Ollama (for LLM inference)

curl -fsSL https://ollama.com/install.sh | sh- **Quality Healthcare**: Standardized, comprehensive clinical notes│   ├── download.py           # Stage 1: Download ZIPs, extract transcripts



# 5. Download Gemma 2 2B model- **Continuous Learning**: Improves from doctor feedback using QLoRA│   ├── parse_transcripts.py  # Stage 2: Parse + attach PHQ-8 labels

ollama pull gemma2:2b

│   ├── translate.py          # Stage 3: Translate to Hindi & Marathi

# 6. Test single SOAP note generation

python pipeline/generate_soap_v3.py --session_id 300 --dialect standard_pune### Key Features│   └── assemble_dataset.py   # Stage 4: Build final dataset

```

│

**Expected output**: `data/soap_notes/soap_300_standard_pune_v3.md` (bilingual SOAP note)

✅ **100% Open Source** - No API dependencies, fully reproducible  ├── vocab/

---

✅ **Bilingual Output** - English + Marathi (Hindi support ready)  │   ├── hindi_clinical_vocab.json    # Clinical + slang + code-mixed vocab (Hindi)

## 📦 Installation & Setup

✅ **Clinical Accuracy** - NER + RAG for medical terminology  │   └── marathi_clinical_vocab.json  # Clinical + slang + code-mixed vocab (Marathi)

### Step 1: System Requirements Check

✅ **Resource Efficient** - Runs on CPU, QLoRA training feasible on 16GB RAM  │

```bash

# Check Python version (must be 3.10+)✅ **Continual Learning** - Human-in-the-loop with incremental retraining  ├── data/                      # Created by the pipeline

python3 --version

│   ├── raw/                   # Extracted transcripts

# Check available disk space (need 60GB free)

df -h .---│   ├── labels/                # PHQ-8 label CSVs from DAIC-WOZ



# Check RAM (16GB minimum)│   ├── parsed/                # Parsed JSON per session

free -h

```## 🏗️ Architecture│   ├── translated/            # Translated JSON per session x language



### Step 2: Create Virtual Environment│   └── final/



```bash### Complete Pipeline Flow│       ├── master_dataset.csv   <- flat CSV, one row per turn

# Create isolated Python environment

python3 -m venv .venv│       └── master_dataset.json  <- grouped by session



# Activate environment```│

source .venv/bin/activate  # Linux/Mac

# OR┌─────────────────────────────────────────────────────────────────────┐├── References/

.venv\Scripts\activate     # Windows

```│                    INPUT: Mental Health Interview                    ││   └── 301_P/                 # Sample DAIC-WOZ session (included)



### Step 3: Install Python Dependencies│              (182 DAIC-WOZ sessions in English/Marathi)             ││



```bash└─────────────────────────────────────────────────────────────────────┘├── run_pipeline.py            # Single entry point

# Install all required packages

pip install --upgrade pip                              ↓├── requirements.txt

pip install -r requirements.txt

┌─────────────────────────────────────────────────────────────────────┐└── README.md

# Verify installation

python -c "import peft, bitsandbytes, transformers, datasets, chromadb, sentence_transformers; print('✅ All packages installed successfully')"│  STEP 1: Named Entity Recognition (NER)                             │```

```

│  ┌───────────────────────────────────────────────────────────────┐  │

**Key packages installed:**

- `transformers` - HuggingFace models (NER, translation, embeddings)│  │ Model: ai4bharat/IndicNER (550 MB)                           │  │---

- `peft` - Parameter-efficient fine-tuning (QLoRA)

- `bitsandbytes` - 4-bit quantization for memory efficiency│  │ Purpose: Extract symptoms, medications, temporal markers      │  │

- `accelerate` - Distributed training support

- `trl` - Transformer Reinforcement Learning│  │ Output: Tagged entities → ["depression", "anxiety", "2 weeks"]│  │## What Each ZIP Contains (DAIC-WOZ)

- `datasets` - HuggingFace dataset utilities

- `chromadb` - Vector database for RAG│  └───────────────────────────────────────────────────────────────┘  │

- `sentence-transformers` - Text embeddings

- `sentencepiece` - Tokenization for Indic languages└─────────────────────────────────────────────────────────────────────┘Each `<id>_P.zip` (300-492) contains:



### Step 4: Install Ollama (LLM Runtime)                              ↓



```bash┌─────────────────────────────────────────────────────────────────────┐| File | Used in Phase 1? | Description |

# Install Ollama (local LLM server)

curl -fsSL https://ollama.com/install.sh | sh│  STEP 2: RAG - Clinical Terminology Retrieval                       │|---|---|---|



# Verify installation│  ┌───────────────────────────────────────────────────────────────┐  │| `<id>_TRANSCRIPT.csv` | YES | Tab-separated: start_time, stop_time, speaker, text |

ollama --version

│  │ Vector DB: ChromaDB (~50 MB)                                  │  │| `<id>_COVAREP.csv` | Phase 2 | 74 acoustic features per frame |

# Start Ollama service (runs in background)

ollama serve &│  │ Embeddings: all-MiniLM-L6-v2 (80 MB)                         │  │| `<id>_FORMANT.csv` | Phase 2 | 5 formant frequencies per frame |

```

│  │ Database: 40+ mental health terms (English, Marathi, Hindi)  │  │| `<id>_CLNF_AUs.txt` | Phase 2 | Facial action units (OpenFace) |

---

│  │ Output: Contextually relevant clinical terminology            │  │| `<id>_CLNF_gaze.txt` | Phase 2 | Eye gaze vectors |

## 🤖 Models to Download

│  └───────────────────────────────────────────────────────────────┘  │| `<id>_CLNF_pose.txt` | Phase 2 | Head pose |

### Required Models (Download Before Running)

└─────────────────────────────────────────────────────────────────────┘

#### 1. **Gemma 2 2B** (Primary LLM for SOAP Generation)

                              ↓**Phase 1 only extracts `_TRANSCRIPT.csv`** — ZIPs are 300-900 MB each but we keep only a few KB per session.

```bash

ollama pull gemma2:2b┌─────────────────────────────────────────────────────────────────────┐

```

│  STEP 3: SOAP Generation (LLM)                                      │---

- **Size**: 1.6 GB

- **Purpose**: Generate English SOAP notes from conversations│  ┌───────────────────────────────────────────────────────────────┐  │

- **Where it runs**: Via Ollama API (localhost:11434)

- **Status**: ✅ Required for pipeline│  │ Model: Gemma 2 2B via Ollama (1.6 GB)                        │  │## Quick Start



#### 2. **NLLB-200-Distilled-600M** (Translation Model)│  │ Temperature: 0.3 (clinical accuracy)                          │  │



This downloads automatically on first run, but you can pre-download:│  │ Enhanced Prompt: Conversation + NER entities + RAG terms      │  │### 1. Install dependencies



```bash│  │ Output: Structured 4-section SOAP note in English            │  │```bash

python -c "

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer│  └───────────────────────────────────────────────────────────────┘  │pip install -r requirements.txt

model_name = 'facebook/nllb-200-distilled-600M'

print('Downloading NLLB translation model...')└─────────────────────────────────────────────────────────────────────┘```

tokenizer = AutoTokenizer.from_pretrained(model_name)

model = AutoModelForSeq2SeqLM.from_pretrained(model_name)                              ↓

print('✅ NLLB model cached successfully')

"┌─────────────────────────────────────────────────────────────────────┐### 2a. Run with local sample (no download — recommended first)

```

│  STEP 4: Translation (English → Marathi/Hindi)                      │```bash

- **Size**: 2.46 GB

- **Purpose**: Translate English SOAP notes to Marathi/Hindi│  ┌───────────────────────────────────────────────────────────────┐  │python run_pipeline.py --sample

- **Where it's stored**: `~/.cache/huggingface/hub/`

- **Status**: ✅ Required for bilingual output│  │ Model: ai4bharat/IndicTrans2-en-indic-1B (1.2 GB)           │  │```



#### 3. **Sentence-Transformers MiniLM** (RAG Embeddings)│  │ Specialized for Indian languages (better than Google API)    │  │



Downloads automatically, or pre-download:│  │ Preserves clinical terminology during translation            │  │### 2b. Download specific sessions



```bash│  │ Output: Marathi SOAP note (4 sections)                       │  │```bash

python -c "

from sentence_transformers import SentenceTransformer│  └───────────────────────────────────────────────────────────────┘  │python run_pipeline.py --ids 301 302 303

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

print('✅ Embeddings model cached successfully')└─────────────────────────────────────────────────────────────────────┘```

"

```                              ↓



- **Size**: 80 MB┌─────────────────────────────────────────────────────────────────────┐### 2c. Download first 10 sessions (for testing)

- **Purpose**: Generate embeddings for clinical term retrieval (RAG)

- **Where it's stored**: `~/.cache/torch/sentence_transformers/`│              OUTPUT: Bilingual SOAP Note (JSON Format)               │```bash

- **Status**: ✅ Required for RAG pipeline

│    ├─ English: {subjective, objective, assessment, plan}            │python run_pipeline.py --limit 10

#### 4. **IndicNER** (Named Entity Recognition)

│    ├─ Marathi: {subjective, objective, assessment, plan}            │```

*Currently uses generic NER, IndicNER integration in progress:*

│    └─ Metadata: session_id, PHQ-8 score, severity, timestamp        │

```bash

# Will be integrated in future update└─────────────────────────────────────────────────────────────────────┘### 2d. Hindi only

python -c "

from transformers import AutoTokenizer, AutoModelForTokenClassification```bash

tokenizer = AutoTokenizer.from_pretrained('ai4bharat/IndicNER')

model = AutoModelForTokenClassification.from_pretrained('ai4bharat/IndicNER')                              ↓python run_pipeline.py --sample --lang hindi

print('✅ IndicNER model cached')

"```

```

┌─────────────────────────────────────────────────────────────────────┐

- **Size**: 550 MB

- **Purpose**: Extract medical entities (symptoms, medications, durations)│          PHASE 2: QLoRA Fine-Tuning (Human-in-the-Loop)             │### 2e. Skip stages already done

- **Status**: ⏭️ Optional (will improve entity extraction)

│  ┌───────────────────────────────────────────────────────────────┐  │```bash

### Optional Models (For Advanced Use)

│  │ Base Model: Gemma 2 2B (quantized to 4-bit = 400 MB)        │  │python run_pipeline.py --skip download parse

#### **LLaMA 3.1 8B** (Alternative LLM)

│  │ Method: QLoRA (trains only 0.1% of parameters)               │  │```

```bash

ollama pull llama3.1:8b│  │ Training Data: 182 SOAP notes + doctor corrections           │  │

```

│  │ Memory: ~6 GB RAM (CPU training feasible!)                   │  │---

- **Size**: 4.9 GB

- **Purpose**: Alternative to Gemma 2 (better quality, slower)│  │ Output: LoRA adapters (~16 MB per version)                   │  │

- **Status**: ⏭️ Optional (removed to save space by default)

│  │ Versions: v1.0, v1.1, v1.2... (iterative improvement)       │  │## Output: master_dataset.csv columns

### Model Storage Locations

│  └───────────────────────────────────────────────────────────────┘  │

```

~/.cache/huggingface/hub/          ← HuggingFace models (NLLB, embeddings)└─────────────────────────────────────────────────────────────────────┘| Column | Description |

~/.ollama/models/                  ← Ollama models (Gemma, LLaMA)

~/.cache/torch/sentence_transformers/ ← Sentence embedding models```|---|---|

.cache/vector_db/                  ← ChromaDB vector database (project-local)

```| `session_id` | DAIC-WOZ session number |



### Total Disk Space Required---| `language` | hindi or marathi |



| Component | Size | Required? || `style` | formal_translated / colloquial / code_mixed |

|-----------|------|-----------|

| Gemma 2 2B | 1.6 GB | ✅ Yes |## 🤖 Models & Components| `turn_id` | Turn index |

| NLLB-200 Translation | 2.46 GB | ✅ Yes |

| MiniLM Embeddings | 80 MB | ✅ Yes || `role` | Doctor or Patient |

| IndicNER | 550 MB | ⏭️ Optional |

| Python packages | 1.5 GB | ✅ Yes |### Active Models (Production)| `role_label` | In Indic script |

| Dataset (182 sessions) | 50 MB | ✅ Yes |

| Generated SOAP notes | 10 MB | - || `text_en` | Original English text |

| **TOTAL** | **~6 GB** | **Required** |

| Component | Model | Size | Purpose | Status || `text` | Translated Indic text |

---

|-----------|-------|------|---------|--------|| `phq8_score` | PHQ-8 score (0-24) |

## 📖 Usage - Step by Step

| **SOAP Generation** | Gemma 2 2B (Ollama) | 1.6 GB | Generate clinical notes | ✅ Active || `phq8_binary` | 0=non-depressed, 1=depressed |

### Workflow Overview

| **Translation** | IndicTrans2-en-indic-1B | 1.2 GB | English → Marathi/Hindi | 🔄 To Install || `severity` | minimal/mild/moderate/moderately_severe/severe |

```

PHASE 1: Data Preparation (run once)| **NER** | ai4bharat/IndicNER | 550 MB | Medical entity extraction | 🔄 To Install || `split` | train / dev / test |

  ↓

PHASE 2: SOAP Generation (run 182 times, once per session)| **Embeddings** | all-MiniLM-L6-v2 | 80 MB | RAG vector search | 🔄 To Install |

  ↓

PHASE 3: Validation (quality checks)| **Vector DB** | ChromaDB | 50 MB | Clinical terminology store | 🔄 To Install |---

  ↓

PHASE 4: Fine-Tuning (human feedback → QLoRA)

```

**Total Disk Usage**: ~3.5 GB (models + cache)## Vocabulary Files

---



### PHASE 1: Data Preparation (One-Time Setup)

### Training Infrastructure (Phase 2)Edit `vocab/hindi_clinical_vocab.json` or `vocab/marathi_clinical_vocab.json` to add slang, fix translations, or add dialect variants — no code changes needed.

**Purpose**: Download and translate DAIC-WOZ dataset to Marathi



#### Option A: Use Local Sample (Fastest - Recommended for Testing)

| Component | Size | Purpose |---

```bash

python run_pipeline.py --sample|-----------|------|---------|

```

| PEFT (LoRA) | 50 MB | Parameter-efficient fine-tuning |## Phase 2 (Planned)

**Output**: Processes session 301 (already included in `References/301_P/`)

| BitsAndBytes | 100 MB | 4-bit quantization for QLoRA |

#### Option B: Download Specific Sessions

| LoRA Adapters | 16 MB each | Fine-tuned model weights (per version) |Fine-tune a multilingual model (IndicBERT / mT5 / Gemma) to auto-generate SOAP notes:

```bash

# Download sessions 300-305- **S** (Subjective) — patient's own words

python run_pipeline.py --ids 300 301 302 303 304 305

```---- **O** (Objective) — observed tone, affect, speech patterns



#### Option C: Download All 182 Sessions (Full Dataset)- **A** (Assessment) — condition + PHQ-8 severity



```bash## 📊 Dataset- **P** (Plan) — therapy, medication, follow-up

# WARNING: Downloads ~50GB, takes 2-3 hours

python run_pipeline.py

```

### Source: DAIC-WOZ---

#### Option D: Download First N Sessions (For Testing)

- **Description**: Distress Analysis Interview Corpus - Wizard-of-Oz

```bash

# Download first 10 sessions only- **Sessions**: 182 clinical interviews for depression screening## Dataset Source

python run_pipeline.py --limit 10

```- **Format**: Doctor-patient dialogues with PHQ-8 scores



#### Skip Already Completed Stages- **Languages**: Original (English) + Translated (Marathi with 5 dialects)Gratch, J., et al. (2014). The Distress Analysis Interview Corpus of human and computer interviews. LREC.



```bashhttps://dcapswoz.ict.usc.edu/wwwdaicwoz/

# If you already have raw data, skip download/parse

python run_pipeline.py --skip download parse### Dialect Coverage

```

| Dialect | Region | Example |

**What this creates:**|---------|--------|---------|

- `data/raw/` - Original DAIC-WOZ transcripts| Standard Pune | Pune, Western Maharashtra | मला नैराश्य आहे |

- `data/translated/` - English → Marathi translations (182 files)| Mumbai | Mumbai Metropolitan | मला डिप्रेशन आहे |

- `data/dialect_marathi/` - 5 dialect variations (910 files total)| Vidarbha | Eastern Maharashtra | मला उदासीपणा आहे |

| Marathwada | Central Maharashtra | मला मन उदास आहे |

---| Konkan | Coastal Maharashtra | म्हाका उदास वाटतं |



### PHASE 2: SOAP Note Generation### PHQ-8 Distribution



#### Generate Single SOAP Note| Severity | PHQ-8 Range | Sessions | Percentage |

|----------|-------------|----------|------------|

```bash| Minimal | 0-4 | ~20 | 11% |

# Generate SOAP for session 300 (standard Pune Marathi)| Mild | 5-9 | ~40 | 22% |

python pipeline/generate_soap_v3.py --session_id 300 --dialect standard_pune| Moderate | 10-14 | ~60 | 33% |

```| Moderately Severe | 15-19 | ~40 | 22% |

| Severe | 20-24 | ~22 | 12% |

**Output**: `data/soap_notes/soap_300_standard_pune_v3.md`

---

#### Generate Multiple Sessions

## 📁 Project Structure

```bash

# Generate for sessions 300-305```

for i in {300..305}; doSOAP-GENERATION-BTECH-PROJECT/

  python pipeline/generate_soap_v3.py --session_id $i --dialect standard_pune│

done├── 📂 data/                          # All datasets

```│   ├── dialect_marathi/              # 182 sessions × 5 dialects = 910 files

│   ├── labels/                       # PHQ-8 scores and metadata

#### Generate All 182 SOAP Notes (Production Run)│   ├── soap_notes/                   # Generated SOAP notes (JSON)

│   └── sessions_index.csv            # Session metadata

```bash│

# Process all sessions with progress tracking├── 📂 src/                           # Modular source code

python pipeline/generate_soap_v3.py --all│   ├── generation/                   # SOAP generation

```│   │   └── soap_generator.py         # SOAPGenerator class (Ollama LLM)

│   ├── translation/                  # Translation modules

**Expected time**: ~2 minutes per session = ~6 hours total for 182 sessions│   │   └── indic_translator.py       # IndicTranslator (IndicTrans2)

│   ├── ner/                          # Named Entity Recognition

#### Use Different Dialects│   │   └── medical_ner.py            # MedicalNER (IndicNER)

│   ├── rag/                          # RAG system

```bash│   │   └── clinical_rag.py           # ClinicalVectorStore, RAGTranslator

# Available dialects: standard_pune, mumbai, vidarbha, marathwada, konkan│   └── utils/                        # Helper functions

python pipeline/generate_soap_v3.py --session_id 300 --dialect mumbai│       └── helpers.py                # Config loading, file I/O

```│

├── 📂 pipeline/                      # Data processing scripts

#### Batch Generation with Custom Settings│   ├── download.py                   # Download DAIC-WOZ

│   ├── parse_transcripts.py         # Parse conversations

```bash│   ├── translate.py                  # Translate to Marathi

# Generate 10 sessions with custom model│   ├── transform_dialects.py        # Create dialect variations

python pipeline/generate_soap_v3.py \│   └── generate_soap_v2.py           # ⭐ Current SOAP generator (working)

  --sessions 300 301 302 303 304 305 306 307 308 309 \│

  --dialect standard_pune \├── 📂 scripts/                       # Utility scripts

  --model gemma2:2b \│   ├── validate_soap_notes.py        # Automated quality checks

  --temperature 0.3│   ├── manual_review_interface.py    # Interactive review tool

```│   └── cleanup_project.py            # Project maintenance

│

---├── 📂 configs/                       # Configuration files

│   └── config.yaml                   # Model paths, hyperparameters

### PHASE 3: Validation│

├── 📄 README.md                      # ⭐ This file (comprehensive guide)

#### Automated Quality Checks├── 📄 requirements.txt               # Python dependencies

└── 📄 run_pipeline.py                # Data preprocessing orchestrator

```bash```

# Run automated validation on all generated SOAP notes

python scripts/validate_soap_notes.py---

```

## 🚀 Installation

**What it checks:**

- ✅ All 4 sections present (S, O, A, P)### Prerequisites

- ✅ Bilingual alignment (English ↔ Marathi)- Python 3.10+

- ✅ Minimum content length per section- 16 GB RAM (8 GB minimum for inference only)

- ✅ Clinical keyword coverage- 5 GB disk space for models

- ✅ Devanagari script correctness- Ollama installed (for Gemma 2 2B)



**Output**: `data/validation/review_list.json` (sessions flagged for manual review)### Step 1: Clone Repository

```bash

#### Manual Review Interfacegit clone https://github.com/Revati0419/SOAP-GENERATION-BTECH-PROJECT.git

cd SOAP-GENERATION-BTECH-PROJECT

```bash```

# Interactive review tool for flagged sessions

python scripts/manual_review_interface.py### Step 2: Create Virtual Environment

``````bash

python3 -m venv .venv

**Features:**source .venv/bin/activate  # Linux/Mac

- Display conversation + generated SOAP# .venv\Scripts\activate   # Windows

- Side-by-side English/Marathi comparison```

- Guided checklist (accuracy, completeness, language quality)

- Save corrections and ratings### Step 3: Install Dependencies

```bash

**Output**: `data/validation/manual_review_log.json`pip install -r requirements.txt

```

#### Validation Strategy

### Step 4: Install Ollama Models

Uses **stratified sampling** to review 20 sessions (11% of 182):```bash

- 95% confidence interval# Install Ollama (if not already installed)

- 5% margin of errorcurl -fsSL https://ollama.com/install.sh | sh

- Stratified by complexity (high/medium/low)

# Pull Gemma 2 2B model

---ollama pull gemma2:2b

```

### PHASE 4: Fine-Tuning with QLoRA

---

#### Prepare Training Data

## 💻 Usage

```bash

# Convert validated SOAP notes to training format### Quick Start: Generate SOAP Note for One Session

python scripts/prepare_training_data.py \

  --soap_dir data/soap_notes \```bash

  --review_log data/validation/manual_review_log.json \# Test on session 300 (fastest - uses existing test data)

  --output_dir data/trainingpython pipeline/generate_soap_v2.py --test --model gemma2:2b

``````



**Creates:****Output**: `data/soap_notes/300_soap.json`

- `data/training/train.jsonl` (80% of data)

- `data/training/val.jsonl` (20% for validation)### Generate SOAP Notes for All 182 Sessions



**Format**: Each line is a JSON object with `prompt` and `response` fields.```bash

# Full dataset generation (~6 hours on CPU)

#### Dry-Run Training (Test Setup)python pipeline/generate_soap_v2.py --model gemma2:2b

```

```bash

# Test training on 5 samples (validates configuration)### Data Preprocessing (If Starting from Scratch)

python scripts/qlora_train.py \

  --model_name_or_path google/gemma-2b \```bash

  --train_file data/training/train.jsonl \# Download and process DAIC-WOZ dataset

  --validation_file data/training/val.jsonl \python run_pipeline.py --sample              # Test with sample

  --output_dir outputs/qlora_testpython run_pipeline.py --limit 10            # First 10 sessions

```python run_pipeline.py                       # Full dataset (182 sessions)

```

**Expected output**: Validates model loading, dataset parsing, and training loop setup.

### Quality Validation

#### Full QLoRA Training

```bash

```bash# Step 1: Automated quality checks

# Train on full dataset with QLoRA (4-bit quantization)python scripts/validate_soap_notes.py

python scripts/qlora_train.py \

  --model_name_or_path google/gemma-2b \# Step 2: Manual review (interactive)

  --train_file data/training/train.jsonl \python scripts/manual_review_interface.py

  --validation_file data/training/val.jsonl \```

  --output_dir outputs/qlora_v1 \

  --num_train_epochs 3 \---

  --per_device_train_batch_size 4 \

  --learning_rate 2e-4 \## 🎓 Training with QLoRA

  --lora_rank 8 \

  --lora_alpha 16 \### Phase 1: Generate Training Dataset

  --do_train

``````bash

# Generate all 182 SOAP notes

**Training parameters:**python pipeline/generate_soap_v2.py --model gemma2:2b

- **Quantization**: 4-bit (NF4) via bitsandbytes

- **LoRA rank**: 8 (trainable parameters: ~8M = 0.1% of 8B)# Validate quality

- **Batch size**: 4 (adjust based on RAM)python scripts/validate_soap_notes.py

- **Epochs**: 3 (can increase for better quality)

- **Learning rate**: 2e-4 (standard for QLoRA)# Manual review sample (20-25 sessions)

python scripts/manual_review_interface.py

**Expected time**: ~2-4 hours on CPU for 182 samples (3 epochs)```



**Output**: `outputs/qlora_v1/adapter_model.bin` (16 MB LoRA adapter)### Phase 2: Setup QLoRA Infrastructure



#### Use Fine-Tuned Model```bash

# Install training libraries

```bashpip install peft bitsandbytes accelerate trl

# Generate SOAP with fine-tuned adapter

python pipeline/generate_soap_v3.py \# Prepare training data

  --session_id 300 \python scripts/prepare_training_data.py

  --dialect standard_pune \```

  --adapter_path outputs/qlora_v1

```### Phase 3: Initial Training



---```bash

# Train on 182 SOAP notes (2-3 hours on CPU)

## 🏗️ Architecturepython scripts/train_qlora.py \

    --config configs/training_config.yaml \

### Complete Pipeline Flow    --output soap-lora-v1.0

```

```

┌─────────────────────────────────────────────────────────────────────┐**Output**: LoRA adapters (~16 MB) saved to `soap-lora-v1.0/`

│                    INPUT: Mental Health Interview                    │

│              (182 DAIC-WOZ sessions in English/Marathi)             │---

└─────────────────────────────────────────────────────────────────────┘

                              ↓## ✅ Validation Strategy

┌─────────────────────────────────────────────────────────────────────┐

│  STEP 1: Named Entity Recognition (NER)                             │### Why Smart Sampling?

│  ┌───────────────────────────────────────────────────────────────┐  │

│  │ Model: Generic NER (IndicNER integration pending)            │  │**Problem**: Can't manually read all 182 SOAP notes  

│  │ Purpose: Extract symptoms, medications, temporal markers      │  │**Solution**: Stratified random sampling (statistically valid)

│  │ Output: Tagged entities → ["depression", "anxiety", "2 weeks"]│  │

│  └───────────────────────────────────────────────────────────────┘  │### Automated Validation

└─────────────────────────────────────────────────────────────────────┘

                              ↓```bash

┌─────────────────────────────────────────────────────────────────────┐python scripts/validate_soap_notes.py

│  STEP 2: RAG - Clinical Terminology Retrieval                       │```

│  ┌───────────────────────────────────────────────────────────────┐  │

│  │ Vector DB: ChromaDB (~50 MB)                                  │  │**Checks**:

│  │ Embeddings: all-MiniLM-L6-v2 (80 MB)                         │  │- ✅ Completeness (all 4 sections present)

│  │ Database: 40+ mental health terms (English, Marathi, Hindi)  │  │- ✅ Minimum length (50+ chars per section)

│  │ Output: Contextually relevant clinical terminology            │  │- ✅ Language purity (Marathi not 30%+ English)

│  └───────────────────────────────────────────────────────────────┘  │- ✅ Clinical consistency (severity matches PHQ-8)

└─────────────────────────────────────────────────────────────────────┘

                              ↓### Manual Review (11% Sample)

┌─────────────────────────────────────────────────────────────────────┐

│  STEP 3: SOAP Generation (LLM)                                      │**Sample Size**: 20-25 sessions (95% confidence, ±10% margin)  

│  ┌───────────────────────────────────────────────────────────────┐  │**Strategy**: Stratified by severity level

│  │ Model: Gemma 2 2B via Ollama (1.6 GB)                        │  │

│  │ Temperature: 0.3 (clinical accuracy)                          │  │| Severity | Total | Sample |

│  │ Enhanced Prompt: Conversation + NER entities + RAG terms      │  │|----------|-------|--------|

│  │ Output: Structured 4-section SOAP note in English            │  │| Minimal | ~20 | 3-4 |

│  └───────────────────────────────────────────────────────────────┘  │| Mild | ~40 | 5-6 |

└─────────────────────────────────────────────────────────────────────┘| Moderate | ~60 | 6-8 |

                              ↓| Severe | ~62 | 6-8 |

┌─────────────────────────────────────────────────────────────────────┐

│  STEP 4: Translation (English → Marathi/Hindi)                      │**Interactive Tool**:

│  ┌───────────────────────────────────────────────────────────────┐  │```bash

│  │ Model: facebook/nllb-200-distilled-600M (2.46 GB)           │  │python scripts/manual_review_interface.py

│  │ Specialized for 200+ languages including Indic languages     │  │```

│  │ Preserves clinical terminology during translation            │  │

│  │ Output: Marathi SOAP note (4 sections)                       │  │**Time Required**: 2-4 hours (5-10 min per session)

│  └───────────────────────────────────────────────────────────────┘  │

└─────────────────────────────────────────────────────────────────────┘---

                              ↓

┌─────────────────────────────────────────────────────────────────────┐## 🎯 B.Tech Project Contributions

│              OUTPUT: Bilingual SOAP Note (Markdown)                  │

│    ├─ English: {subjective, objective, assessment, plan}            │### Novel Aspects (8-Credit Project)

│    ├─ Marathi: {subjective, objective, assessment, plan}            │

│    └─ Metadata: session_id, PHQ-8 score, severity, timestamp        │1. **Hybrid NER-RAG-LLM Architecture**

└─────────────────────────────────────────────────────────────────────┘   - First integration of NER + RAG for clinical Indic language generation

                              ↓   - Published approach: Entity extraction → Terminology retrieval → Generation

┌─────────────────────────────────────────────────────────────────────┐

│          PHASE 2: QLoRA Fine-Tuning (Human-in-the-Loop)             │2. **IndicTrans2 for Clinical Translation**

│  ┌───────────────────────────────────────────────────────────────┐  │   - Specialized Indian language model for medical documentation

│  │ Base Model: Gemma 2 2B (quantized to 4-bit = 400 MB)        │  │   - Better quality than Google Translate API for clinical terms

│  │ Method: QLoRA (trains only 0.1% of parameters)               │  │

│  │ Training Data: 182 SOAP notes + doctor corrections           │  │3. **QLoRA for Continual Learning**

│  │ Memory: ~6 GB RAM (CPU training feasible!)                   │  │   - Efficient fine-tuning (0.1% parameters, CPU feasible)

│  │ Output: LoRA adapters (~16 MB per version)                   │  │   - Human-in-the-loop feedback integration

│  │ Versions: v1.0, v1.1, v1.2... (iterative improvement)       │  │   - Version tracking with performance metrics

│  └───────────────────────────────────────────────────────────────┘  │

└─────────────────────────────────────────────────────────────────────┘4. **Multi-Dialect Marathi Support**

```   - 5 regional dialects (Pune, Mumbai, Vidarbha, Marathwada, Konkan)

   - Dialect-aware translation and validation

### Model Components

5. **Statistically Valid Quality Assurance**

| Component | Model | Size | Purpose | Status |   - Stratified random sampling methodology

|-----------|-------|------|---------|--------|   - Automated + manual validation pipeline

| **LLM** | Gemma 2 2B | 1.6 GB | SOAP generation | ✅ Active |   - 95% confidence interval with 11% sample

| **Translation** | NLLB-200-distilled-600M | 2.46 GB | English → Marathi/Hindi | ✅ Active |

| **Embeddings** | all-MiniLM-L6-v2 | 80 MB | RAG vector search | ✅ Active |### Technical Stack (100% Open Source)

| **NER** | Generic NER | - | Entity extraction | 🔄 Basic (IndicNER pending) |

| **Vector DB** | ChromaDB | 50 MB | Clinical term storage | ✅ Active |- **LLM**: Gemma 2 2B (Google, open weights)

| **QLoRA** | PEFT + bitsandbytes | - | Parameter-efficient fine-tuning | ✅ Ready |- **Translation**: IndicTrans2 (AI4Bharat)

- **NER**: IndicNER (AI4Bharat)

---- **Embeddings**: MiniLM-L6-v2 (Sentence Transformers)

- **Vector DB**: ChromaDB

## 🎓 Training with QLoRA- **Training**: PEFT/QLoRA (Hugging Face)

- **Infrastructure**: Ollama (local LLM serving)

### What is QLoRA?

---

**QLoRA** (Quantized Low-Rank Adaptation) enables fine-tuning large language models on consumer hardware:

## 📚 References

- **4-bit Quantization**: Reduces model size from 8GB → 2GB

- **LoRA Adapters**: Trains only 0.1% of parameters (8M out of 8B)### Dataset

- **Memory Efficient**: Runs on 16GB RAM (CPU training feasible!)- **DAIC-WOZ**: Gratch, J., et al. (2014). "The Distress Analysis Interview Corpus of human and computer interviews."

- **Fast Iteration**: Train in 2-4 hours vs days for full fine-tuning

- **Version Control**: Small adapters (16MB) easy to store and version### Models

- **Gemma**: Google (2024). "Gemma: Open Models Based on Gemini Research and Technology"

### Training Workflow- **IndicTrans2**: AI4Bharat (2023). "IndicTrans2: Towards High-Quality and Accessible Machine Translation Models for all 22 Scheduled Indian Languages"

- **IndicNER**: AI4Bharat (2022). "Named Entity Recognition for Indian Languages"

```

1. Generate initial SOAP notes (182 sessions)### Methods

   ↓- **LoRA**: Hu et al. (2021). "LoRA: Low-Rank Adaptation of Large Language Models"

2. Doctor reviews and corrects 20 samples (stratified sampling)- **QLoRA**: Dettmers et al. (2023). "QLoRA: Efficient Finetuning of Quantized LLMs"

   ↓- **RAG**: Lewis et al. (2020). "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"

3. Convert corrections to training data (prompt/response pairs)

   ↓---

4. Train QLoRA adapter (v1.0) - 2-4 hours

   ↓## 👥 Contributors

5. Generate new SOAP notes with v1.0 adapter

   ↓- **Revati** - B.Tech Project Lead

6. Collect more corrections, train v1.1, v1.2...- GitHub: [@Revati0419](https://github.com/Revati0419)

   ↓

7. Continual improvement over time---

```

## 📄 License

---

This project is for academic/research purposes. The DAIC-WOZ dataset requires separate licensing from USC.

## ✅ Validation Strategy

---

### Automated Quality Checks

**Last Updated**: March 5, 2026  

Run on all 182 generated SOAP notes:**Version**: 2.0 (Consolidated Documentation)  

**Status**: Phase 2 - Ready for Full Integration

```bash
python scripts/validate_soap_notes.py
```

**Checks performed:**
1. **Completeness**: All 4 sections present (S, O, A, P)
2. **Length**: Minimum 200 characters per section
3. **Bilingual Alignment**: English ↔ Marathi consistency
4. **Clinical Keywords**: Required terms in each section
5. **Script Validation**: Proper Devanagari encoding
6. **PHQ-8 Integration**: Score mentioned in Assessment
7. **Entity Coverage**: NER entities referenced in SOAP

### Manual Review Sampling

**Strategy**: Stratified random sampling for 95% confidence
- **Sample size**: 20 sessions (11% of 182)
- **Confidence interval**: 95%
- **Margin of error**: ±5%
- **Stratification**: By conversation complexity and PHQ-8 score

---

## 📁 Project Structure

```
SOAP-GENERATION-BTECH-PROJECT/
├── README.md                    ← This file (comprehensive guide)
├── PIPELINE_GUIDE.md           ← Explains two entry points
├── requirements.txt             ← Python dependencies
├── configs/
│   └── config.yaml             ← Model paths and hyperparameters
│
├── pipeline/
│   ├── generate_soap_v3.py     ← Main SOAP generation script ⭐
│   ├── download.py             ← Download DAIC-WOZ dataset
│   ├── parse_transcripts.py   ← Parse conversations
│   ├── translate.py            ← Translate to Marathi/Hindi
│   └── assemble_dataset.py    ← Create final dataset
│
├── scripts/
│   ├── qlora_train.py          ← QLoRA fine-tuning script ⭐
│   ├── prepare_training_data.py ← Convert SOAP notes to training format
│   ├── validate_soap_notes.py  ← Automated quality checks
│   ├── manual_review_interface.py ← Interactive review tool
│   └── cleanup_project.py      ← Project maintenance
│
├── src/
│   ├── generation/             ← SOAP generation modules
│   ├── translation/            ← Translation utilities
│   ├── ner/                    ← Named Entity Recognition
│   ├── rag/                    ← Retrieval-Augmented Generation
│   └── utils/                  ← Helper functions
│
├── data/
│   ├── raw/                    ← Original DAIC-WOZ transcripts
│   ├── labels/                 ← PHQ-8 depression scores
│   ├── translated/             ← English → Marathi translations
│   ├── dialect_marathi/        ← 5 dialect variations (910 files)
│   ├── soap_notes/             ← Generated bilingual SOAP notes ⭐
│   ├── training/               ← QLoRA training data (JSONL)
│   └── validation/             ← Quality check results
│
├── vocab/
│   ├── clinical_vocab_marathi.json ← Medical terminology database
│   └── clinical_vocab_hindi.json
│
├── outputs/
│   └── qlora_v1/               ← Fine-tuned LoRA adapters
│
├── .cache/
│   ├── models/                 ← HuggingFace model cache
│   └── vector_db/              ← ChromaDB persistence
│
└── References/
    └── 301_P/                  ← Sample DAIC-WOZ session (for testing)
```

---

## 🎓 B.Tech Project Contributions

### Academic Context

**Project Type**: 8-Credit B.Tech Capstone Project  
**Domain**: AI/ML in Healthcare, NLP for Indian Languages  
**Innovation**: Human-in-the-loop learning system for clinical documentation  

### Novel Contributions

1. **Bilingual Clinical Documentation**
   - First open-source system for Marathi clinical SOAP notes
   - Addresses language barrier in Indian healthcare

2. **Resource-Efficient QLoRA Training**
   - Enables continual learning on consumer hardware (16GB RAM)
   - ~16MB adapter updates vs multi-GB full model retraining

3. **NER + RAG + LLM Integration**
   - Complete pipeline: entity extraction → knowledge retrieval → generation
   - Preserves clinical terminology during translation

4. **Stratified Validation Strategy**
   - Statistically sound sampling (95% CI, ±5% error)
   - Reduces manual review effort from 182 → 20 sessions

5. **Dialect Support**
   - 5 Marathi regional variants (Pune, Mumbai, Vidarbha, Marathwada, Konkan)
   - Real-world applicability across Maharashtra

---

## 🔧 Troubleshooting

### Common Issues

**1. Ollama connection error**
```bash
# Start Ollama service
ollama serve &

# Test connection
curl http://localhost:11434/api/generate
```

**2. Model not found**
```bash
# List installed Ollama models
ollama list

# Pull missing model
ollama pull gemma2:2b
```

**3. Out of memory during training**
```bash
# Reduce batch size in training command
--per_device_train_batch_size 2
```

**4. Devanagari encoding issues**
```bash
# Ensure UTF-8 locale
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
```

**5. Slow translation**
- First run downloads NLLB model (2.46GB) - wait ~10 minutes
- Subsequent runs use cached model

---

## 📚 References

- **DAIC-WOZ Dataset**: [USC Institute for Creative Technologies](https://dcapswoz.ict.usc.edu/wwwdaicwoz/)
- **Gemma Models**: [Google Gemma](https://ai.google.dev/gemma)
- **QLoRA Paper**: [Dettmers et al., 2023](https://arxiv.org/abs/2305.14314)
- **NLLB Translation**: [Meta AI NLLB-200](https://github.com/facebookresearch/fairseq/tree/nllb)

---

## 📧 Contact

**Project Maintainer**: Revati  
**Institution**: B.Tech Project  
**Repository**: [github.com/Revati0419/SOAP-GENERATION-BTECH-PROJECT](https://github.com/Revati0419/SOAP-GENERATION-BTECH-PROJECT)

---

**Last Updated**: March 6, 2026  
**Version**: 3.0 (QLoRA-ready, NLLB translation, RAG integration)
