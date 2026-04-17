"""
04_evaluate.py
──────────────
Step 4: Evaluate the fine-tuned Whisper model on the test set.

Computes:
  - Overall Word Error Rate (WER)
  - WER broken down by language (English / Marathi / Mixed)
  - Character Error Rate (CER) — better for Marathi Devanagari script
  - Worst-performing examples (for targeted data improvement)
  - Comparison: baseline Whisper vs your fine-tuned model

Outputs:
  evaluation/eval_results.json   — full metrics
  evaluation/worst_examples.csv  — hardest clips to debug
  evaluation/eval_report.txt     — human-readable summary

Usage:
    python src/04_evaluate.py
    python src/04_evaluate.py --model_dir models/whisper-medical/final
"""

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf
import torch
from tqdm import tqdm

from transformers import WhisperForConditionalGeneration, WhisperProcessor
import evaluate

warnings.filterwarnings("ignore")

MODEL_DIR     = Path("models/whisper-medical/final")
BASE_MODEL    = "openai/whisper-tiny"   # for baseline comparison
EVAL_DIR      = Path("evaluation")
AUGMENTED_DIR = Path("data/augmented")
EVAL_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────
# METRICS
# ─────────────────────────────────────────────────────

def compute_wer_cer(predictions: list, references: list):
    wer_metric = evaluate.load("wer")
    cer_metric = evaluate.load("cer")
    wer = 100 * wer_metric.compute(predictions=predictions, references=references)
    cer = 100 * cer_metric.compute(predictions=predictions, references=references)
    return round(wer, 2), round(cer, 2)


# ─────────────────────────────────────────────────────
# TRANSCRIPTION
# ─────────────────────────────────────────────────────

def transcribe_batch(audio_paths: list, processor: WhisperProcessor,
                     model: WhisperForConditionalGeneration) -> list:
    transcripts = []

    for audio_path in tqdm(audio_paths, desc="  Transcribing", leave=False):
        try:
            audio, sr = sf.read(str(audio_path), dtype="float32")
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)

            inputs = processor(audio, sampling_rate=16000, return_tensors="pt")
            input_features = inputs.input_features

            with torch.no_grad():
                predicted_ids = model.generate(
                    input_features,
                    max_length=225,
                    num_beams=1,        # greedy for speed on CPU
                )

            text = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
            transcripts.append(text.strip())

        except Exception as e:
            transcripts.append("")

    return transcripts


# ─────────────────────────────────────────────────────
# PER-LANGUAGE EVALUATION
# ─────────────────────────────────────────────────────

def evaluate_by_language(df: pd.DataFrame, predictions: list):
    results = {}
    languages = df["language"].unique()

    for lang in languages:
        mask = df["language"] == lang
        lang_refs  = df.loc[mask, "transcript"].tolist()
        lang_preds = [p for p, m in zip(predictions, mask) if m]

        if len(lang_refs) < 2:
            continue

        wer, cer = compute_wer_cer(lang_preds, lang_refs)
        results[lang] = {"wer": wer, "cer": cer, "n_samples": sum(mask)}

    return results


# ─────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────

def main(model_dir: Path, run_baseline: bool):
    print("\n" + "="*60)
    print("  STEP 4: Model Evaluation")
    print("="*60)

    # ── Load test data ─────────────────────────────────
    test_csv = AUGMENTED_DIR / "test.csv"
    if not test_csv.exists():
        print(f"❌  test.csv not found at {test_csv}")
        return

    test_df = pd.read_csv(test_csv)
    print(f"\n  Test set: {len(test_df)} samples")

    audio_paths = test_df["audio_path"].tolist()
    references  = test_df["transcript"].tolist()

    # ── Load fine-tuned model ──────────────────────────
    if not model_dir.exists():
        print(f"❌  Model not found at {model_dir}")
        print(f"   Run python src/03_train.py first.")
        return

    print(f"\n  Loading fine-tuned model from {model_dir}...")
    ft_processor = WhisperProcessor.from_pretrained(str(model_dir))
    ft_model     = WhisperForConditionalGeneration.from_pretrained(str(model_dir))
    ft_model.eval()

    # ── Fine-tuned model predictions ──────────────────
    print("\n  Running fine-tuned model inference...")
    ft_predictions = transcribe_batch(audio_paths, ft_processor, ft_model)
    ft_wer, ft_cer = compute_wer_cer(ft_predictions, references)

    print(f"\n  Fine-tuned model:")
    print(f"    WER: {ft_wer:.1f}%")
    print(f"    CER: {ft_cer:.1f}%")

    # ── Baseline comparison ────────────────────────────
    baseline_wer, baseline_cer = None, None
    if run_baseline:
        print(f"\n  Loading baseline model ({BASE_MODEL})...")
        base_processor = WhisperProcessor.from_pretrained(BASE_MODEL, language="marathi", task="transcribe")
        base_model     = WhisperForConditionalGeneration.from_pretrained(BASE_MODEL)
        base_model.eval()

        print("  Running baseline model inference...")
        base_predictions  = transcribe_batch(audio_paths, base_processor, base_model)
        baseline_wer, baseline_cer = compute_wer_cer(base_predictions, references)

        print(f"\n  Baseline model:")
        print(f"    WER: {baseline_wer:.1f}%")
        print(f"    CER: {baseline_cer:.1f}%")

        improvement_wer = baseline_wer - ft_wer
        print(f"\n  📈 WER Improvement: {improvement_wer:+.1f}% "
              f"({'better' if improvement_wer > 0 else 'worse'})")

    # ── Per-language breakdown ─────────────────────────
    lang_results = evaluate_by_language(test_df, ft_predictions)

    print(f"\n  Per-language WER:")
    for lang, metrics in lang_results.items():
        bar = "█" * int(metrics["wer"] / 5)
        print(f"    {lang:12s} WER: {metrics['wer']:5.1f}%  CER: {metrics['cer']:5.1f}%  "
              f"(n={metrics['n_samples']})  {bar}")

    # ── Find worst examples ────────────────────────────
    sample_wers = []
    try:
        wer_metric = evaluate.load("wer")
        for ref, hyp in zip(references, ft_predictions):
            try:
                w = 100 * wer_metric.compute(predictions=[hyp], references=[ref])
            except Exception:
                w = 100.0
            sample_wers.append(w)
    except Exception:
        sample_wers = [0.0] * len(references)

    test_df = test_df.copy()
    test_df["prediction"]  = ft_predictions
    test_df["sample_wer"]  = sample_wers
    worst = test_df.nlargest(20, "sample_wer")[
        ["file_name", "transcript", "prediction", "language", "sample_wer"]
    ]
    worst.to_csv(EVAL_DIR / "worst_examples.csv", index=False)

    # ── Save results ───────────────────────────────────
    results = {
        "fine_tuned": {
            "model_dir":      str(model_dir),
            "overall_wer":    ft_wer,
            "overall_cer":    ft_cer,
            "per_language":   lang_results,
            "n_test_samples": len(test_df),
        }
    }
    if baseline_wer is not None:
        results["baseline"] = {
            "model":       BASE_MODEL,
            "overall_wer": baseline_wer,
            "overall_cer": baseline_cer,
        }
        results["improvement_wer"] = round(baseline_wer - ft_wer, 2)

    with open(EVAL_DIR / "eval_results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # ── Human-readable report ──────────────────────────
    report_lines = [
        "WHISPER MEDICAL ASR — EVALUATION REPORT",
        "=" * 55,
        "",
        f"Fine-tuned model: {model_dir}",
        f"Test samples:     {len(test_df)}",
        "",
        "OVERALL METRICS",
        "-" * 40,
        f"  Word Error Rate (WER): {ft_wer:.1f}%",
        f"  Char Error Rate (CER): {ft_cer:.1f}%",
        "",
        "INTERPRETATION:",
        "  WER < 10%  = Excellent (production ready)",
        "  WER 10-20% = Good (usable with correction)",
        "  WER 20-30% = Fair (needs more data)",
        "  WER > 30%  = Poor (collect more training data)",
        "",
        "PER-LANGUAGE BREAKDOWN",
        "-" * 40,
    ]
    for lang, m in lang_results.items():
        report_lines.append(f"  {lang:12s} WER={m['wer']:.1f}%  CER={m['cer']:.1f}%  (n={m['n_samples']})")

    if baseline_wer is not None:
        report_lines += [
            "",
            "BASELINE COMPARISON",
            "-" * 40,
            f"  Baseline WER:     {baseline_wer:.1f}%",
            f"  Fine-tuned WER:   {ft_wer:.1f}%",
            f"  WER improvement:  {baseline_wer - ft_wer:+.1f}%",
        ]

    report_lines += [
        "",
        "NEXT STEPS (if WER is high):",
        "  1. Review worst_examples.csv — find patterns in errors",
        "  2. Add more training data for the highest-WER language",
        "  3. Check if medical terms are in your training set",
        "  4. Re-run augmentation with more variants",
        "  5. When GPU available, upgrade to whisper-small",
        "",
        f"Files: {EVAL_DIR}/",
        "  eval_results.json",
        "  worst_examples.csv",
        "  eval_report.txt",
    ]

    report_text = "\n".join(report_lines)
    with open(EVAL_DIR / "eval_report.txt", "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\n{'='*60}")
    print(f"  ✅  Evaluation complete!")
    print(f"  WER: {ft_wer:.1f}%   CER: {ft_cer:.1f}%")
    print(f"\n  Files saved to: {EVAL_DIR}/")
    print(f"    eval_results.json")
    print(f"    worst_examples.csv    ← review these to improve data")
    print(f"    eval_report.txt")
    print(f"\n  Next step: python src/05_quantize.py")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate fine-tuned Whisper model")
    parser.add_argument("--model_dir",     type=str, default=str(MODEL_DIR))
    parser.add_argument("--baseline",      action="store_true",
                        help="Also run baseline Whisper for comparison (takes longer)")
    args = parser.parse_args()

    main(
        model_dir    = Path(args.model_dir),
        run_baseline = args.baseline,
    )
