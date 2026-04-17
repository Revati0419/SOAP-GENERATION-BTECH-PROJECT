# 🎙️ Whisper Medical ASR — Marathi + English
### CPU-Optimised Fine-tuning Pipeline

---

## What This Project Does
Fine-tunes OpenAI Whisper (tiny variant) to accurately transcribe
doctor-patient conversations in Marathi, English, and code-switched speech,
with special focus on medical vocabulary.

## Project Structure
```
whisper_asr_pipeline/
├── data/
│   ├── raw/              ← Put your audio files + transcripts here
│   ├── processed/        ← Auto-generated: cleaned & resampled audio
│   └── augmented/        ← Auto-generated: speed/noise augmented clips
├── src/
│   ├── 01_prepare_data.py       ← Step 1: Data prep & validation
│   ├── 02_augment_data.py       ← Step 2: Audio augmentation
│   ├── 03_train.py              ← Step 3: Fine-tune Whisper
│   ├── 04_evaluate.py           ← Step 4: WER evaluation
│   ├── 05_quantize.py           ← Step 5: Quantize for fast CPU inference
│   └── 06_inference.py          ← Step 6: Run transcription
├── scripts/
│   ├── install.sh               ← One-shot install script
│   └── generate_synthetic.py    ← Generate synthetic data via TTS
├── notebooks/
│   └── explore_data.ipynb       ← EDA notebook
├── evaluation/                  ← WER results saved here
└── models/                      ← Trained model checkpoints saved here
```

## Quick Start

### 1. Install dependencies
```bash
bash scripts/install.sh
```

### 2. Prepare your data
Place your files in `data/raw/` in this format:
```
data/raw/
  ├── metadata.csv      ← columns: file_name, transcript, language
  ├── audio_001.wav
  ├── audio_002.wav
  └── ...
```

metadata.csv example:
```csv
file_name,transcript,language
audio_001.wav,"रुग्णाला तीन दिवसांपासून डोकेदुखी आहे",marathi
audio_002.wav,"Patient has severe headache for 3 days",english
audio_003.wav,"Patient la headache ahe ani nausea pan ahe",mixed
```

### 3. Run the pipeline — Step by Step
```bash
# Step 1: Validate & process your audio files
python src/01_prepare_data.py

# Step 2: Augment data (creates 3x more training samples)
python src/02_augment_data.py

# Step 3: Fine-tune (CPU - runs overnight, ~8-12 hours for 500 samples)
python src/03_train.py

# Step 4: Evaluate WER on test set
python src/04_evaluate.py

# Step 5: Quantize model for fast CPU inference
python src/05_quantize.py

# Step 6: Transcribe new audio
python src/06_inference.py --audio path/to/audio.wav

# Optional: True speaker diarization (Doctor/Patient segmentation)
# Requires: pyannote.audio + HF token (see section below)
python src/06_inference.py --audio path/to/audio.wav --diarization
```

## Optional: True Speaker Diarization (pyannote)

Whisper by itself does **not** do reliable speaker identity mapping. For robust
speaker segmentation, enable diarization with `pyannote.audio`.

### Install (inside `whisper_asr_pipeline/.venv_whisper`)
```bash
pip install "pyannote.audio>=3.1,<4"
```

### Auth token
Set a Hugging Face token that has access to pyannote models:
```bash
export HF_TOKEN="your_hf_token_here"
```

### Run with diarization
```bash
python src/06_inference.py --audio path/to/audio.mp3 --diarization --base_model openai/whisper-small
```

When diarization is enabled but unavailable (missing token/package), the script
automatically falls back to heuristic speaker hints so your pipeline still runs.

## CPU Training Notes
- Uses `whisper-tiny` (39M params) — trainable on CPU in ~8-12 hours
- Uses `gradient_checkpointing` + `fp32` (no fp16 on CPU)
- Batch size = 2 to stay within RAM limits
- Expected WER after fine-tuning: 15-25% on medical Marathi

## No Audio Yet? Generate Synthetic Data First
```bash
python scripts/generate_synthetic.py
```
This uses Google TTS to generate Marathi + English medical audio clips
for bootstrapping your dataset before real recordings are available.

## Target Metrics
| Language | Baseline WER | Target WER after fine-tuning |
|----------|-------------|------------------------------|
| English (medical) | ~12% | < 8% |
| Marathi (medical) | ~35% | < 20% |
| Code-switched | ~45% | < 28% |
