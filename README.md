# SOAP Generation in Indic Languages — Dataset Pipeline

> **Phase 1** — Build a bilingual (Hindi + Marathi) doctor-patient mental health conversation dataset from DAIC-WOZ transcripts.
> **Phase 2** (future) — Train a model to generate SOAP notes from those conversations.

---

## Project Overview

The [DAIC-WOZ dataset](https://dcapswoz.ict.usc.edu/wwwdaicwoz/) contains clinical interview recordings in English between a virtual interviewer (Ellie) and participants, annotated with PHQ-8 depression scores.

This pipeline:
1. **Downloads** the DAIC-WOZ transcripts (only `_TRANSCRIPT.csv` from each ZIP — audio/video skipped)
2. **Parses** them and attaches PHQ-8 labels
3. **Translates** English → Hindi & Marathi with **three linguistic style layers**
4. **Assembles** a final dataset ready for model training

---

## Why Three Style Layers?

Real Indian patients don't speak in formal translated Hindi. They use:

| Style | Example (Hindi) | Example (Marathi) |
|---|---|---|
| `formal_translated` | *मुझे अवसाद है* | *मला नैराश्य आहे* |
| `colloquial` | *मन बहुत उदास रहता है* | *मन खूप उदास राहतं* |
| `code_mixed` | *मुझे depression feel हो रहा है* | *मला depression सारखं वाटतंय* |

---

## File Structure

```
SOAP-GENERATION-BTECH-PROJECT/
│
├── pipeline/
│   ├── download.py           # Stage 1: Download ZIPs, extract transcripts
│   ├── parse_transcripts.py  # Stage 2: Parse + attach PHQ-8 labels
│   ├── translate.py          # Stage 3: Translate to Hindi & Marathi
│   └── assemble_dataset.py   # Stage 4: Build final dataset
│
├── vocab/
│   ├── hindi_clinical_vocab.json    # Clinical + slang + code-mixed vocab (Hindi)
│   └── marathi_clinical_vocab.json  # Clinical + slang + code-mixed vocab (Marathi)
│
├── data/                      # Created by the pipeline
│   ├── raw/                   # Extracted transcripts
│   ├── labels/                # PHQ-8 label CSVs from DAIC-WOZ
│   ├── parsed/                # Parsed JSON per session
│   ├── translated/            # Translated JSON per session x language
│   └── final/
│       ├── master_dataset.csv   <- flat CSV, one row per turn
│       └── master_dataset.json  <- grouped by session
│
├── References/
│   └── 301_P/                 # Sample DAIC-WOZ session (included)
│
├── run_pipeline.py            # Single entry point
├── requirements.txt
└── README.md
```

---

## What Each ZIP Contains (DAIC-WOZ)

Each `<id>_P.zip` (300-492) contains:

| File | Used in Phase 1? | Description |
|---|---|---|
| `<id>_TRANSCRIPT.csv` | YES | Tab-separated: start_time, stop_time, speaker, text |
| `<id>_COVAREP.csv` | Phase 2 | 74 acoustic features per frame |
| `<id>_FORMANT.csv` | Phase 2 | 5 formant frequencies per frame |
| `<id>_CLNF_AUs.txt` | Phase 2 | Facial action units (OpenFace) |
| `<id>_CLNF_gaze.txt` | Phase 2 | Eye gaze vectors |
| `<id>_CLNF_pose.txt` | Phase 2 | Head pose |

**Phase 1 only extracts `_TRANSCRIPT.csv`** — ZIPs are 300-900 MB each but we keep only a few KB per session.

---

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2a. Run with local sample (no download — recommended first)
```bash
python run_pipeline.py --sample
```

### 2b. Download specific sessions
```bash
python run_pipeline.py --ids 301 302 303
```

### 2c. Download first 10 sessions (for testing)
```bash
python run_pipeline.py --limit 10
```

### 2d. Hindi only
```bash
python run_pipeline.py --sample --lang hindi
```

### 2e. Skip stages already done
```bash
python run_pipeline.py --skip download parse
```

---

## Output: master_dataset.csv columns

| Column | Description |
|---|---|
| `session_id` | DAIC-WOZ session number |
| `language` | hindi or marathi |
| `style` | formal_translated / colloquial / code_mixed |
| `turn_id` | Turn index |
| `role` | Doctor or Patient |
| `role_label` | In Indic script |
| `text_en` | Original English text |
| `text` | Translated Indic text |
| `phq8_score` | PHQ-8 score (0-24) |
| `phq8_binary` | 0=non-depressed, 1=depressed |
| `severity` | minimal/mild/moderate/moderately_severe/severe |
| `split` | train / dev / test |

---

## Vocabulary Files

Edit `vocab/hindi_clinical_vocab.json` or `vocab/marathi_clinical_vocab.json` to add slang, fix translations, or add dialect variants — no code changes needed.

---

## Phase 2 (Planned)

Fine-tune a multilingual model (IndicBERT / mT5 / Gemma) to auto-generate SOAP notes:
- **S** (Subjective) — patient's own words
- **O** (Objective) — observed tone, affect, speech patterns
- **A** (Assessment) — condition + PHQ-8 severity
- **P** (Plan) — therapy, medication, follow-up

---

## Dataset Source

Gratch, J., et al. (2014). The Distress Analysis Interview Corpus of human and computer interviews. LREC.
https://dcapswoz.ict.usc.edu/wwwdaicwoz/
