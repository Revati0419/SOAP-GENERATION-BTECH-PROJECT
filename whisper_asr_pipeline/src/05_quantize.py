"""
05_quantize.py
──────────────
Step 5: Quantize the fine-tuned model for fast CPU inference.

Why quantize?
  Fine-tuned Whisper-tiny in fp32 = ~150MB, slow on CPU
  After INT8 quantization          = ~40MB,  3-4x faster on CPU

Method: PyTorch dynamic quantization (no data needed, lossless quality)
  - Converts Linear layer weights from fp32 → int8
  - Activations stay fp32 at runtime (computed on-the-fly)
  - No re-training needed

Expected results:
  Model size:      ~150MB → ~40MB
  Inference speed: ~3-4x faster on CPU
  WER change:      < 0.5% degradation (negligible)

Usage:
    python src/05_quantize.py
"""

import json
import time
import warnings
from pathlib import Path

import torch
import numpy as np
import soundfile as sf

from transformers import WhisperForConditionalGeneration, WhisperProcessor

warnings.filterwarnings("ignore")

MODEL_DIR      = Path("models/whisper-medical/final")
QUANTIZED_DIR  = Path("models/whisper-medical/quantized")


def get_model_size_mb(model) -> float:
    """Calculate model size in MB."""
    param_size = 0
    for param in model.parameters():
        param_size += param.nelement() * param.element_size()
    buffer_size = 0
    for buf in model.buffers():
        buffer_size += buf.nelement() * buf.element_size()
    return round((param_size + buffer_size) / 1024 / 1024, 1)


def benchmark_inference(model, processor, n_runs: int = 3) -> float:
    """Benchmark inference speed with a synthetic audio clip."""
    # Generate 3 seconds of synthetic audio (silence + small noise)
    audio = np.random.randn(48000).astype(np.float32) * 0.01
    inputs = processor(audio, sampling_rate=16000, return_tensors="pt")

    times = []
    for _ in range(n_runs):
        start = time.time()
        with torch.no_grad():
            model.generate(inputs.input_features, max_length=50, num_beams=1)
        times.append(time.time() - start)

    return round(sum(times) / len(times), 3)


def quantize():
    print("\n" + "="*60)
    print("  STEP 5: Model Quantization (CPU Optimisation)")
    print("="*60)

    if not MODEL_DIR.exists():
        print(f"❌  Fine-tuned model not found at {MODEL_DIR}")
        print(f"   Run python src/03_train.py first.")
        return

    # ── Load fine-tuned model ──────────────────────────
    print(f"\n  Loading fine-tuned model from {MODEL_DIR}...")
    processor = WhisperProcessor.from_pretrained(str(MODEL_DIR))
    model     = WhisperForConditionalGeneration.from_pretrained(str(MODEL_DIR))
    model.eval()

    original_size = get_model_size_mb(model)
    print(f"  Original model size: {original_size} MB")

    print(f"\n  Benchmarking original model speed...")
    original_speed = benchmark_inference(model, processor)
    print(f"  Original inference time: {original_speed:.3f}s per clip")

    # ── Apply dynamic INT8 quantization ───────────────
    print(f"\n  Applying PyTorch dynamic INT8 quantization...")
    print(f"  (quantizing all Linear layers: encoder + decoder)")

    quantized_model = torch.quantization.quantize_dynamic(
        model,
        {torch.nn.Linear},   # quantize all Linear layers
        dtype=torch.qint8    # INT8 weights
    )
    quantized_model.eval()

    quantized_size = get_model_size_mb(quantized_model)
    print(f"  Quantized model size: {quantized_size} MB")
    print(f"  Size reduction: {original_size - quantized_size:.1f} MB "
          f"({100 * (1 - quantized_size/original_size):.0f}% smaller)")

    print(f"\n  Benchmarking quantized model speed...")
    quantized_speed = benchmark_inference(quantized_model, processor)
    print(f"  Quantized inference time: {quantized_speed:.3f}s per clip")
    print(f"  Speed improvement: {original_speed / quantized_speed:.1f}x faster")

    # ── Save quantized model ───────────────────────────
    QUANTIZED_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n  Saving quantized model to {QUANTIZED_DIR}...")

    # Save the quantized state dict
    torch.save(
        quantized_model.state_dict(),
        QUANTIZED_DIR / "quantized_model.pt"
    )
    # Save processor (tokenizer + feature extractor) — unchanged
    processor.save_pretrained(str(QUANTIZED_DIR))
    # Save original model config for loading later
    model.config.save_pretrained(str(QUANTIZED_DIR))

    # Save quantization metadata
    meta = {
        "base_model":            str(MODEL_DIR),
        "quantization_method":   "pytorch_dynamic_int8",
        "quantized_layers":      "Linear",
        "original_size_mb":      original_size,
        "quantized_size_mb":     quantized_size,
        "size_reduction_pct":    round(100 * (1 - quantized_size/original_size), 1),
        "original_speed_s":      original_speed,
        "quantized_speed_s":     quantized_speed,
        "speedup_factor":        round(original_speed / quantized_speed, 2),
    }
    with open(QUANTIZED_DIR / "quantization_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  ✅  Quantization complete!")
    print(f"  Original:   {original_size} MB,  {original_speed:.3f}s/clip")
    print(f"  Quantized:  {quantized_size} MB,  {quantized_speed:.3f}s/clip")
    print(f"  Speedup:    {original_speed / quantized_speed:.1f}x faster")
    print(f"\n  Files saved to: {QUANTIZED_DIR}/")
    print(f"\n  Next step: python src/06_inference.py --audio your_audio.wav")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    quantize()
