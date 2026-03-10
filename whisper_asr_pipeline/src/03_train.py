"""
03_train.py
───────────
Step 3: Fine-tune Whisper for Medical ASR (CPU-optimised)

Model: openai/whisper-tiny  (39M params — trainable on CPU)
Task:  Automatic Speech Recognition in Marathi + English

CPU Optimisations applied:
  ✓ whisper-tiny (smallest, fastest variant)
  ✓ batch_size=2 with gradient_accumulation=8 (effective batch=16)
  ✓ fp32 training (fp16 not supported on CPU)
  ✓ gradient_checkpointing to reduce RAM usage
  ✓ num_workers=0 to avoid multiprocessing issues on CPU
  ✓ Early stopping to avoid wasted compute
  ✓ Saves best checkpoint by WER automatically

Expected training time (CPU):
  100 clips  → ~2-3 hours
  500 clips  → ~8-12 hours
  1000 clips → ~20-24 hours

Tip: Run overnight. Use tmux or nohup to keep it running.

Usage:
    python src/03_train.py
    python src/03_train.py --epochs 5 --model openai/whisper-tiny
    nohup python src/03_train.py > logs/train.log 2>&1 &
"""

import os
import sys
import json
import argparse
import warnings
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
import torch
import soundfile as sf
from tqdm import tqdm

from transformers import (
    WhisperForConditionalGeneration,
    WhisperProcessor,
    WhisperFeatureExtractor,
    WhisperTokenizer,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    EarlyStoppingCallback,
)
from datasets import Dataset, Audio
import evaluate

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────

AUGMENTED_DIR  = Path("data/augmented")
MODEL_DIR      = Path("models/whisper-medical")
LOGS_DIR       = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Use whisper-tiny for CPU — upgrade to whisper-small when you get GPU
BASE_MODEL     = "openai/whisper-tiny"
LANGUAGE       = "marathi"       # primary language hint for Whisper decoder
TASK           = "transcribe"

# CPU-optimised training hyperparameters
BATCH_SIZE           = 2         # keep low for CPU RAM
GRAD_ACCUMULATION    = 8         # effective batch = 2 * 8 = 16
LEARNING_RATE        = 1e-4      # slightly higher LR for tiny model
NUM_EPOCHS           = 10        # will early-stop if no improvement
WARMUP_STEPS         = 50
EVAL_STEPS           = 100       # evaluate every N steps
SAVE_STEPS           = 100
MAX_INPUT_LENGTH     = 30        # seconds
NUM_WORKERS          = 0         # 0 = no multiprocessing (safer on CPU)

# ─────────────────────────────────────────────────────
# DATA COLLATOR
# ─────────────────────────────────────────────────────

@dataclass
class DataCollatorSpeechSeq2SeqWithPadding:
    """
    Pads audio features and label token IDs to the same length within a batch.
    This is needed because different audio clips have different lengths.
    """
    processor: Any
    decoder_start_token_id: int

    def __call__(self, features: List[Dict[str, Union[List[int], torch.Tensor]]]):
        # Pad input features (audio mel-spectrograms)
        input_features = [{"input_features": f["input_features"]} for f in features]
        batch = self.processor.feature_extractor.pad(
            input_features, return_tensors="pt"
        )

        # Pad label sequences (transcript token IDs)
        label_features = [{"input_ids": f["labels"]} for f in features]
        labels_batch = self.processor.tokenizer.pad(
            label_features, return_tensors="pt"
        )

        # Replace padding token ID with -100 so loss ignores padding
        labels = labels_batch["input_ids"].masked_fill(
            labels_batch.attention_mask.ne(1), -100
        )

        # Remove BOS token from labels if present (added by the model)
        if (labels[:, 0] == self.decoder_start_token_id).all().cpu().item():
            labels = labels[:, 1:]

        batch["labels"] = labels
        return batch


# ─────────────────────────────────────────────────────
# DATASET LOADING
# ─────────────────────────────────────────────────────

def load_split(csv_path: Path, processor: WhisperProcessor, max_samples: Optional[int] = None):
    """
    Load a dataset split from CSV, process audio into Whisper mel features.
    Returns a HuggingFace Dataset.
    """
    df = pd.read_csv(csv_path)
    if max_samples:
        df = df.sample(n=min(max_samples, len(df)), random_state=42)

    print(f"    Loading {len(df)} samples from {csv_path.name}...")

    records = []
    skipped = 0

    for _, row in tqdm(df.iterrows(), total=len(df), desc=f"    Preprocessing {csv_path.stem}"):
        audio_path = row.get("audio_path", str(Path("data/augmented") / csv_path.stem / row["file_name"]))

        try:
            # Load audio
            audio, sr = sf.read(audio_path, dtype="float32")
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)

            # Resample if needed (should already be 16kHz from Step 1)
            if sr != 16000:
                import librosa
                audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)

            # Skip clips that are too long
            if len(audio) / 16000 > MAX_INPUT_LENGTH:
                skipped += 1
                continue

            # Extract mel spectrogram features (this is what Whisper actually sees)
            input_features = processor.feature_extractor(
                audio,
                sampling_rate=16000,
                return_tensors="np"
            ).input_features[0]

            # Tokenize transcript (what Whisper should output)
            transcript = str(row["transcript"])
            labels = processor.tokenizer(transcript).input_ids

            records.append({
                "input_features": input_features,
                "labels": labels,
                "transcript": transcript,
                "language": str(row.get("language", "unknown")),
            })

        except Exception as e:
            skipped += 1
            continue

    if skipped > 0:
        print(f"    ⚠  Skipped {skipped} samples during preprocessing")

    if len(records) == 0:
        print(f"❌  No valid samples loaded from {csv_path}")
        sys.exit(1)

    return Dataset.from_list(records)


# ─────────────────────────────────────────────────────
# METRICS
# ─────────────────────────────────────────────────────

def make_compute_metrics(processor: WhisperProcessor):
    """Returns a compute_metrics function for the Trainer."""
    wer_metric = evaluate.load("wer")

    def compute_metrics(pred):
        pred_ids   = pred.predictions
        label_ids  = pred.label_ids

        # Replace -100 (padding) with pad token ID before decoding
        label_ids[label_ids == -100] = processor.tokenizer.pad_token_id

        # Decode predictions and labels to text
        pred_str  = processor.tokenizer.batch_decode(pred_ids,   skip_special_tokens=True)
        label_str = processor.tokenizer.batch_decode(label_ids,  skip_special_tokens=True)

        # Compute Word Error Rate
        wer = 100 * wer_metric.compute(predictions=pred_str, references=label_str)

        # Log a few examples to see how it's doing
        print("\n  📊 Sample predictions vs references:")
        for i in range(min(3, len(pred_str))):
            print(f"    REF: {label_str[i]}")
            print(f"    HYP: {pred_str[i]}")
            print()

        return {"wer": wer}

    return compute_metrics


# ─────────────────────────────────────────────────────
# MAIN TRAINING
# ─────────────────────────────────────────────────────

def train(base_model: str, num_epochs: int, resume_from: Optional[str]):

    print("\n" + "="*60)
    print("  STEP 3: Fine-tuning Whisper (CPU Mode)")
    print("="*60)
    print(f"\n  Base model:  {base_model}")
    print(f"  Device:      CPU")
    print(f"  Batch size:  {BATCH_SIZE} (effective: {BATCH_SIZE * GRAD_ACCUMULATION})")
    print(f"  Epochs:      {num_epochs}")

    # ── Load processor ─────────────────────────────────
    print(f"\n  Loading Whisper processor...")
    processor = WhisperProcessor.from_pretrained(
        base_model, language=LANGUAGE, task=TASK
    )

    # ── Load model ─────────────────────────────────────
    print(f"  Loading Whisper model ({base_model})...")
    model = WhisperForConditionalGeneration.from_pretrained(base_model)

    # Force model to always generate in transcription mode
    model.config.forced_decoder_ids = processor.get_decoder_prompt_ids(
        language=LANGUAGE, task=TASK
    )
    # Tell model to suppress special timestamp tokens during training
    model.config.suppress_tokens = []

    # Gradient checkpointing saves RAM at cost of small speed penalty
    model.config.use_cache = False
    model.gradient_checkpointing_enable()

    n_params = sum(p.numel() for p in model.parameters())
    print(f"  Model parameters: {n_params:,}")

    # ── Load datasets ──────────────────────────────────
    print(f"\n  Loading datasets...")
    train_dataset = load_split(AUGMENTED_DIR / "train.csv", processor)
    val_dataset   = load_split(AUGMENTED_DIR / "val.csv",   processor)

    print(f"\n  Train: {len(train_dataset)} samples")
    print(f"  Val:   {len(val_dataset)} samples")

    # ── Data collator ──────────────────────────────────
    data_collator = DataCollatorSpeechSeq2SeqWithPadding(
        processor=processor,
        decoder_start_token_id=model.config.decoder_start_token_id,
    )

    # ── Training arguments ─────────────────────────────
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    training_args = Seq2SeqTrainingArguments(
        output_dir                  = str(MODEL_DIR),

        # Batching
        per_device_train_batch_size = BATCH_SIZE,
        per_device_eval_batch_size  = BATCH_SIZE,
        gradient_accumulation_steps = GRAD_ACCUMULATION,

        # Optimiser
        learning_rate               = LEARNING_RATE,
        warmup_steps                = WARMUP_STEPS,
        num_train_epochs            = num_epochs,
        weight_decay                = 0.01,

        # Evaluation
        evaluation_strategy         = "steps",
        eval_steps                  = EVAL_STEPS,
        save_strategy               = "steps",
        save_steps                  = SAVE_STEPS,
        save_total_limit            = 3,         # keep only 3 checkpoints
        load_best_model_at_end      = True,
        metric_for_best_model       = "wer",
        greater_is_better           = False,     # lower WER is better

        # Generation settings
        predict_with_generate       = True,
        generation_max_length       = 225,

        # CPU settings
        fp16                        = False,     # fp16 not supported on CPU
        bf16                        = False,
        dataloader_num_workers      = NUM_WORKERS,
        no_cuda                     = True,

        # Logging
        logging_dir                 = str(LOGS_DIR),
        logging_steps               = 25,
        report_to                   = ["none"],  # disable wandb/tensorboard

        # Resume support
        resume_from_checkpoint      = resume_from,
    )

    # ── Trainer ────────────────────────────────────────
    trainer = Seq2SeqTrainer(
        model          = model,
        args           = training_args,
        train_dataset  = train_dataset,
        eval_dataset   = val_dataset,
        data_collator  = data_collator,
        compute_metrics= make_compute_metrics(processor),
        callbacks      = [EarlyStoppingCallback(early_stopping_patience=3)],
        tokenizer      = processor.feature_extractor,
    )

    # ── Train ──────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  🚀 Starting training...")
    print(f"  Estimated time: {len(train_dataset) * num_epochs * 0.5 / 60:.0f}-"
          f"{len(train_dataset) * num_epochs * 1.0 / 60:.0f} minutes on CPU")
    print(f"  Tip: Run with `nohup python src/03_train.py &` overnight")
    print(f"{'='*60}\n")

    train_result = trainer.train(resume_from_checkpoint=resume_from)

    # ── Save final model ───────────────────────────────
    final_dir = MODEL_DIR / "final"
    trainer.save_model(str(final_dir))
    processor.save_pretrained(str(final_dir))

    # Save training results
    metrics = train_result.metrics
    trainer.log_metrics("train", metrics)
    trainer.save_metrics("train", metrics)

    with open(MODEL_DIR / "training_results.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  ✅  Training complete!")
    print(f"  Model saved to: {final_dir}")
    print(f"  Training loss:  {metrics.get('train_loss', 'N/A'):.4f}")
    print(f"\n  Next step: python src/04_evaluate.py")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune Whisper for medical ASR")
    parser.add_argument("--model",   type=str, default=BASE_MODEL,
                        help="Base Whisper model (default: openai/whisper-tiny)")
    parser.add_argument("--epochs",  type=int, default=NUM_EPOCHS,
                        help="Number of training epochs (default: 10)")
    parser.add_argument("--resume",  type=str, default=None,
                        help="Path to checkpoint to resume from")
    args = parser.parse_args()

    train(
        base_model   = args.model,
        num_epochs   = args.epochs,
        resume_from  = args.resume,
    )
