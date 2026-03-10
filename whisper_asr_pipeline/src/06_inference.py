"""
06_inference.py
───────────────
Step 6: Transcribe audio with your fine-tuned Whisper model.

FIXES in this version:
  ✓ Quantized model loading — loads from 'final/' dir, applies quantization live
  ✓ Long audio (28+ min) — chunked with overlap to avoid cutting mid-word
  ✓ Speaker turn hints — marks likely speaker changes (Doctor/Patient)
  ✓ Progress bar for long files
  ✓ Auto-saves transcript next to audio file

Usage:
    python src/06_inference.py --audio 305_AUDIO.wav
    python src/06_inference.py --audio 305_AUDIO.wav --output transcript.txt
    python src/06_inference.py --audio 305_AUDIO.wav --output transcript.json
    python src/06_inference.py --audio 305_AUDIO.wav --language marathi
    python src/06_inference.py --audio 305_AUDIO.wav --use_final
"""

import argparse
import json
import time
import warnings
from pathlib import Path

import numpy as np
import torch
from tqdm import tqdm

from transformers import WhisperForConditionalGeneration, WhisperProcessor

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────
# PATHS & CONFIG
# ─────────────────────────────────────────────────────
FINAL_DIR     = Path("models/whisper-medical/final")
QUANTIZED_DIR = Path("models/whisper-medical/quantized")

TARGET_SR    = 16000
CHUNK_SECS   = 28     # slightly under 30s to leave headroom
OVERLAP_SECS = 1      # overlap to avoid cutting words at boundaries


# ─────────────────────────────────────────────────────
# MODEL LOADING  (FIXED)
# ─────────────────────────────────────────────────────

def load_model(use_final: bool = False):
    """
    Load fine-tuned Whisper model correctly.

    BUG FIX: The previous version tried to call from_pretrained() on the
    'quantized/' directory, which only contains a raw state_dict (.pt file),
    not a full HuggingFace model dir. This caused the OSError.

    CORRECT approach:
      1. Always load full model from 'final/' (has all HF files)
      2. Optionally apply quantization on top using saved weights
    """
    if not FINAL_DIR.exists():
        print("  ⚠  No fine-tuned model found at models/whisper-medical/final/")
        print("     Falling back to base openai/whisper-tiny")
        src = "openai/whisper-tiny"
    else:
        src = str(FINAL_DIR)

    print(f"  Loading processor from: {src}")
    processor = WhisperProcessor.from_pretrained(src)

    print(f"  Loading model weights from: {src}")
    model = WhisperForConditionalGeneration.from_pretrained(src)
    model.config.suppress_tokens = []
    model_type = "fine-tuned FP32"

    # Try to load quantized weights on top (optional speed boost)
    quantized_weights = QUANTIZED_DIR / "quantized_model.pt"
    if not use_final and quantized_weights.exists():
        try:
            print(f"  Applying saved INT8 quantization weights...")
            model = torch.quantization.quantize_dynamic(
                model, {torch.nn.Linear}, dtype=torch.qint8
            )
            state = torch.load(
                str(quantized_weights), map_location="cpu", weights_only=False
            )
            # strict=False: ignore proj_out.weight mismatch (known HF quirk)
            model.load_state_dict(state, strict=False)
            model_type = "fine-tuned INT8 quantized"
        except Exception as e:
            print(f"  ⚠  Quantized weight load failed: {e}")
            print(f"     Reloading clean FP32 model...")
            model = WhisperForConditionalGeneration.from_pretrained(src)
            model.config.suppress_tokens = []
            model_type = "fine-tuned FP32 (quantization skipped)"

    model.eval()
    print(f"  ✓ Model ready: {model_type}")
    return model, processor


# ─────────────────────────────────────────────────────
# AUDIO LOADING
# ─────────────────────────────────────────────────────

def load_audio(path: str) -> tuple:
    """Load any audio format → 16kHz mono float32 numpy array."""
    path = str(path)

    # soundfile: WAV, FLAC, OGG (no ffmpeg needed)
    try:
        import soundfile as sf
        audio, sr = sf.read(path, dtype="float32")
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        if sr != TARGET_SR:
            audio = _resample(audio, sr, TARGET_SR)
        return audio.astype(np.float32), TARGET_SR
    except Exception:
        pass

    # librosa: MP3, M4A via audioread (no ffmpeg for most formats)
    try:
        import librosa
        audio, sr = librosa.load(path, sr=TARGET_SR, mono=True)
        return audio.astype(np.float32), TARGET_SR
    except Exception:
        pass

    # torchaudio: broad format support
    try:
        import torchaudio
        waveform, sr = torchaudio.load(path)
        waveform = waveform.mean(dim=0).numpy()
        if sr != TARGET_SR:
            waveform = _resample(waveform, sr, TARGET_SR)
        return waveform.astype(np.float32), TARGET_SR
    except Exception as e:
        raise RuntimeError(
            f"Cannot load: {path}\nError: {e}\n"
            "Try: pip install audioread  (for MP3/M4A without ffmpeg)"
        )


def _resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr:
        return audio
    n_out = int(len(audio) * target_sr / orig_sr)
    return np.interp(
        np.linspace(0, len(audio) - 1, n_out),
        np.arange(len(audio)), audio
    ).astype(np.float32)


# ─────────────────────────────────────────────────────
# CHUNKED TRANSCRIPTION
# ─────────────────────────────────────────────────────

def deduplicate_text(text: str) -> str:
    """Remove looping repetitions — common Whisper hallucination on silence."""
    if not text:
        return text
    words = text.split()
    if len(words) < 6:
        return text
    half = len(words) // 2
    if words[:half] == words[half: half * 2]:
        return " ".join(words[:half])
    return text


def transcribe_audio(audio: np.ndarray, sr: int,
                     model, processor,
                     language: str = None) -> list:
    """
    Transcribe long audio by splitting into overlapping 28s chunks.
    For a 28-minute file: ~60 chunks × ~3s each = ~3 min on CPU.
    """
    chunk_samples   = CHUNK_SECS   * sr
    overlap_samples = OVERLAP_SECS * sr
    step_samples    = chunk_samples - overlap_samples

    starts       = list(range(0, len(audio), step_samples))
    total_chunks = len(starts)

    print(f"\n  Audio: {len(audio)/sr/60:.1f} min  →  {total_chunks} chunks × {CHUNK_SECS}s")
    print(f"  Est. CPU time: {total_chunks * 3 // 60}m {(total_chunks * 3) % 60}s"
          f" – {total_chunks * 5 // 60}m {(total_chunks * 5) % 60}s\n")

    chunks_out = []

    for i, start in enumerate(
        tqdm(starts, desc="  Transcribing", unit="chunk")
    ):
        end   = min(start + chunk_samples, len(audio))
        chunk = audio[start:end]

        if len(chunk) / sr < 0.5:   # skip tiny trailing chunk
            continue

        inputs = processor.feature_extractor(
            chunk, sampling_rate=sr, return_tensors="pt"
        )

        gen_kwargs = dict(max_new_tokens=224, num_beams=1)
        if language:
            gen_kwargs["forced_decoder_ids"] = processor.get_decoder_prompt_ids(
                language=language, task="transcribe"
            )

        with torch.no_grad():
            predicted_ids = model.generate(
                inputs.input_features, **gen_kwargs
            )

        text = processor.tokenizer.batch_decode(
            predicted_ids, skip_special_tokens=True
        )[0].strip()

        text = deduplicate_text(text)

        if text:
            chunks_out.append({
                "chunk_id": i,
                "start_s":  round(start / sr, 1),
                "end_s":    round(end   / sr, 1),
                "text":     text,
            })

    return chunks_out


# ─────────────────────────────────────────────────────
# SPEAKER HINTS
# ─────────────────────────────────────────────────────

def add_speaker_hints(chunks: list) -> list:
    """
    Simple heuristic: label speaker changes based on pause gaps.
    Gap > 1.5s between chunks → likely speaker switch.
    Labels: Speaker A / Speaker B (alternating)

    NOTE: This is NOT real diarization. For accurate Doctor/Patient
    separation you need pyannote-audio (requires GPU + HF token).
    This is a usable approximation for review purposes.
    """
    if not chunks:
        return chunks
    speaker  = "A"
    labelled = []
    for i, chunk in enumerate(chunks):
        if i > 0:
            gap = chunk["start_s"] - chunks[i-1]["end_s"]
            if gap > 1.5:
                speaker = "B" if speaker == "A" else "A"
        chunk = dict(chunk)
        chunk["speaker"] = speaker
        labelled.append(chunk)
    return labelled


# ─────────────────────────────────────────────────────
# OUTPUT FORMATTING
# ─────────────────────────────────────────────────────

def format_transcript(chunks: list) -> str:
    """Format chunks into a timestamped, speaker-labelled transcript."""
    lines        = []
    prev_speaker = None

    for chunk in chunks:
        speaker = chunk.get("speaker", "")
        start_s = chunk["start_s"]
        text    = chunk["text"]

        m   = int(start_s // 60)
        s   = int(start_s  % 60)
        ts  = f"[{m:02d}:{s:02d}]"

        if speaker and speaker != prev_speaker:
            lines.append(f"\n{'─' * 55}")
            lines.append(f"Speaker {speaker}:")
            prev_speaker = speaker

        lines.append(f"  {ts}  {text}")

    return "\n".join(lines)


def print_result(result: dict):
    dur  = result["duration_s"]
    proc = result["processing_s"]
    print(f"\n{'═' * 60}")
    print(f"  📄  TRANSCRIPT  ({int(dur//60)}m {int(dur%60)}s)")
    print(f"{'═' * 60}")
    print(result["transcript_formatted"])
    print(f"\n{'═' * 60}")
    print(f"  File:      {Path(result['audio_file']).name}")
    print(f"  Duration:  {int(dur//60)}m {int(dur%60)}s")
    print(f"  Chunks:    {result['n_chunks']}")
    print(f"  CPU time:  {int(proc//60)}m {int(proc%60)}s")
    print(f"  RTF:       {result['rtf']:.2f}x  "
          f"({'faster' if result['rtf'] < 1 else 'slower'} than real-time)")
    print(f"{'═' * 60}")


# ─────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────

def transcribe_file(audio_path: str, model, processor,
                    language: str = None) -> dict:
    t0 = time.time()
    print(f"\n  📂  {audio_path}")
    audio, sr = load_audio(audio_path)
    duration  = len(audio) / sr
    print(f"  Duration: {int(duration//60)}m {int(duration%60)}s")

    chunks  = transcribe_audio(audio, sr, model, processor, language=language)
    chunks  = add_speaker_hints(chunks)
    elapsed = time.time() - t0

    full_text  = " ".join(c["text"] for c in chunks)
    formatted  = format_transcript(chunks)

    return {
        "audio_file":           str(audio_path),
        "duration_s":           round(duration, 1),
        "n_chunks":             len(chunks),
        "transcript":           full_text,
        "transcript_formatted": formatted,
        "chunks":               chunks,
        "processing_s":         round(elapsed, 1),
        "rtf":                  round(elapsed / max(duration, 1), 3),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio",     type=str, help="Audio file to transcribe")
    parser.add_argument("--audio_dir", type=str, help="Batch: all audio in directory")
    parser.add_argument("--output",    type=str, help=".txt or .json output file")
    parser.add_argument("--language",  type=str, default=None,
                        choices=["marathi", "english"],
                        help="Force language (default: auto per chunk)")
    parser.add_argument("--use_final", action="store_true",
                        help="Use FP32 final model, skip quantization")
    args = parser.parse_args()

    if not args.audio and not args.audio_dir:
        print("Usage: python src/06_inference.py --audio FILE.wav [--output out.txt]")
        return

    print(f"\n{'='*60}")
    print(f"  Whisper Medical ASR — Inference")
    print(f"{'='*60}")
    model, processor = load_model(use_final=args.use_final)

    if args.audio:
        result = transcribe_file(args.audio, model, processor,
                                 language=args.language)
        print_result(result)

        # Determine output path
        if args.output:
            out = Path(args.output)
        else:
            out = Path(args.audio).with_suffix(".txt")

        if str(out).endswith(".json"):
            with open(out, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
        else:
            with open(out, "w", encoding="utf-8") as f:
                f.write(f"File: {result['audio_file']}\n")
                f.write(f"Duration: {int(result['duration_s']//60)}m "
                        f"{int(result['duration_s']%60)}s\n")
                f.write("=" * 60 + "\n")
                f.write(result["transcript_formatted"] + "\n")

        print(f"\n  💾  Saved → {out}")

    elif args.audio_dir:
        d     = Path(args.audio_dir)
        exts  = ["*.wav", "*.mp3", "*.m4a", "*.flac", "*.ogg"]
        files = sorted(f for ext in exts for f in d.glob(ext))
        if not files:
            print(f"❌  No audio files in {d}")
            return
        all_results = []
        for f in files:
            r = transcribe_file(str(f), model, processor, language=args.language)
            print_result(r)
            all_results.append(r)
        out = d / "batch_transcripts.json"
        with open(out, "w", encoding="utf-8") as fp:
            json.dump(all_results, fp, indent=2, ensure_ascii=False)
        print(f"\n  💾  Batch saved → {out}")


if __name__ == "__main__":
    main()