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
import os
import re
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

def _looks_like_hf_repo_id(value: str) -> bool:
    """Heuristic: owner/repo and not an existing local path."""
    if not value or "/" not in value:
        return False
    return not Path(value).exists()


def _detect_adapter_repo(repo_id: str) -> tuple[bool, dict]:
    """Return (is_adapter_repo, adapter_config_dict)."""
    try:
        from huggingface_hub import HfApi, hf_hub_download
    except Exception:
        return False, {}

    try:
        files = set(HfApi().list_repo_files(repo_id))
    except Exception:
        return False, {}

    has_adapter = "adapter_config.json" in files and (
        "adapter_model.safetensors" in files or "adapter_model.bin" in files
    )
    if not has_adapter:
        return False, {}

    cfg = {}
    try:
        cfg_path = hf_hub_download(repo_id=repo_id, filename="adapter_config.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    return True, cfg


def load_model(use_final: bool = False,
               base_model: str = "openai/whisper-tiny",
               adapter_base_model: str = None):
    """
    Load fine-tuned Whisper model correctly.

    BUG FIX: The previous version tried to call from_pretrained() on the
    'quantized/' directory, which only contains a raw state_dict (.pt file),
    not a full HuggingFace model dir. This caused the OSError.

    CORRECT approach:
      1. Always load full model from 'final/' (has all HF files)
      2. Optionally apply quantization on top using saved weights
    """
    # If caller passes a custom HF model/repo (non-openai), use it directly.
    # This enables commands like:
    #   --base_model muktan174/whisper-medium-ekacare-medical
    custom_hf_model = bool(base_model) and not str(base_model).startswith("openai/whisper-")

    adapter_mode = False
    adapter_cfg = {}

    if custom_hf_model:
        src = base_model
        using_finetuned = False
        print(f"  Using custom Hugging Face model: {base_model}")

        # Support adapter-only repos (PEFT) such as LoRA outputs.
        if _looks_like_hf_repo_id(base_model):
            adapter_mode, adapter_cfg = _detect_adapter_repo(base_model)
            if adapter_mode:
                print("  Detected adapter-only repo. Will load base Whisper + adapter.")
    elif not FINAL_DIR.exists():
        print("  ⚠  No fine-tuned model found at models/whisper-medical/final/")
        print(f"     Falling back to base {base_model}")
        src = base_model
        using_finetuned = False
    else:
        src = str(FINAL_DIR)
        using_finetuned = True

    if adapter_mode:
        # Base model can come from explicit override or adapter config.
        inferred_base = adapter_cfg.get("base_model_name_or_path")
        base_for_adapter = adapter_base_model or inferred_base or "openai/whisper-medium"

        print(f"  Adapter base model: {base_for_adapter}")
        print(f"  Loading processor from base model: {base_for_adapter}")
        processor = WhisperProcessor.from_pretrained(base_for_adapter)

        print(f"  Loading base model weights from: {base_for_adapter}")
        model = WhisperForConditionalGeneration.from_pretrained(base_for_adapter)
        model.config.suppress_tokens = []

        try:
            from peft import PeftModel
        except Exception as e:
            raise RuntimeError(
                "Adapter repo detected but `peft` is not installed in this environment. "
                "Install it with: ./.venv_whisper/bin/pip install peft\n"
                f"Original error: {e}"
            )

        print(f"  Loading adapter from: {base_model}")
        try:
            model = PeftModel.from_pretrained(model, base_model)
            # Merge adapter for simpler/faster inference path when available.
            if hasattr(model, "merge_and_unload"):
                model = model.merge_and_unload()
        except Exception as e:
            print(f"  ⚠  Adapter load failed: {e}")
            print("     Continuing with base model only (adapter skipped).")
            adapter_mode = False
    else:
        print(f"  Loading processor from: {src}")
        processor = WhisperProcessor.from_pretrained(src)

        print(f"  Loading model weights from: {src}")
        model = WhisperForConditionalGeneration.from_pretrained(src)
        model.config.suppress_tokens = []
    if adapter_mode:
        model_type = f"custom HF adapter merged ({base_model})"
    elif custom_hf_model:
        model_type = f"custom HF model FP32 ({base_model})"
    else:
        model_type = "fine-tuned FP32" if using_finetuned else f"base model FP32 ({base_model})"

    # Try to load quantized weights on top (optional speed boost)
    quantized_weights = QUANTIZED_DIR / "quantized_model.pt"
    if not use_final and quantized_weights.exists() and not custom_hf_model:
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

    # Collapse long runs of punctuation/noise (e.g., ". . . . ." or "-----")
    text = re.sub(r"([.·•\-]\s*){6,}", "", text).strip()
    text = re.sub(r"\s{2,}", " ", text).strip()

    words = text.split()
    if len(words) < 6:
        return text

    # Remove exact half-loop duplication
    half = len(words) // 2
    if words[:half] == words[half: half * 2]:
        return " ".join(words[:half])

    # Remove repeated short phrase loops like: "we are going ..." × many
    for n in (3, 4, 5, 6):
        if len(words) >= n * 4:
            phrase = words[:n]
            repeats = 0
            i = 0
            while i + n <= len(words) and words[i:i+n] == phrase:
                repeats += 1
                i += n
            if repeats >= 4:
                return " ".join(words[:n])

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

    def _looks_like_question(text: str) -> bool:
        t = (text or "").lower()
        if "?" in t:
            return True
        q_words = (
            "what", "why", "when", "where", "who", "how", "can you", "do you",
            "did you", "are you", "could you", "would you", "tell me",
        )
        return any(q in t for q in q_words)

    def _looks_like_brief_reply(text: str) -> bool:
        t = (text or "").lower().strip()
        starters = ("yes", "no", "hmm", "okay", "ok", "right", "yeah", "i ")
        return len(t.split()) <= 14 or any(t.startswith(s) for s in starters)

    # Pass 1: pause-based switching (original behavior)
    speaker = "A"
    labelled = []
    switches = 0
    for i, chunk in enumerate(chunks):
        if i > 0:
            gap = chunk["start_s"] - chunks[i - 1]["end_s"]
            if gap > 1.5:
                speaker = "B" if speaker == "A" else "A"
                switches += 1
        row = dict(chunk)
        row["speaker"] = speaker
        labelled.append(row)

    # Pass 2: if no switches detected, use conversational cues
    if switches == 0 and len(labelled) >= 2:
        speaker = "A"
        labelled[0]["speaker"] = speaker
        cue_switches = 0

        for i in range(1, len(labelled)):
            prev_text = labelled[i - 1].get("text", "")
            cur_text = labelled[i].get("text", "")

            if _looks_like_question(prev_text) and _looks_like_brief_reply(cur_text):
                speaker = "B" if speaker == "A" else "A"
                cue_switches += 1
            elif i % 2 == 0 and cue_switches == 0:
                # final fallback for monotonic chunks: alternate turns
                speaker = "B" if speaker == "A" else "A"
                cue_switches += 1

            labelled[i]["speaker"] = speaker

    # Pass 3: rebalance if one speaker dominates almost all chunks.
    # This keeps downstream SOAP role mapping usable when real diarization is unavailable.
    counts = {"A": 0, "B": 0}
    for row in labelled:
        sp = str(row.get("speaker", "A"))
        if sp in counts:
            counts[sp] += 1

    total = max(len(labelled), 1)
    dominant_ratio = max(counts.values()) / total

    if total >= 6 and dominant_ratio >= 0.85:
        for i, row in enumerate(labelled):
            row["speaker"] = "A" if i % 2 == 0 else "B"

    return labelled


def _assign_speaker_labels(chunks: list, diar_segments: list) -> list:
    """Assign diarization speaker labels to ASR chunks by max overlap."""
    if not chunks or not diar_segments:
        return chunks

    labelled = []
    for chunk in chunks:
        start = float(chunk["start_s"])
        end = float(chunk["end_s"])
        mid = (start + end) / 2.0

        best_label = None
        best_overlap = -1.0

        for seg_start, seg_end, seg_label in diar_segments:
            overlap = max(0.0, min(end, seg_end) - max(start, seg_start))
            if overlap > best_overlap:
                best_overlap = overlap
                best_label = seg_label

        # If no overlap, fallback to nearest diarization segment midpoint
        if best_label is None or best_overlap <= 0:
            nearest = min(
                diar_segments,
                key=lambda x: abs(((x[0] + x[1]) / 2.0) - mid)
            )
            best_label = nearest[2]

        row = dict(chunk)
        row["speaker"] = str(best_label)
        labelled.append(row)

    return labelled


def add_true_diarization(chunks: list, audio_path: str,
                         hf_token: str = None,
                         diarization_device: str = "cpu") -> tuple:
    """
    Try real diarization via pyannote-audio.

    Returns:
      (labelled_chunks, backend_name)

    If pyannote is unavailable or fails, caller can fallback to heuristic hints.
    """
    if not chunks:
        return chunks, "none"

    token = hf_token or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
    if not token:
        raise RuntimeError(
            "Diarization requested but HF token not provided. "
            "Set HF_TOKEN/HUGGINGFACE_TOKEN or pass --hf_token."
        )

    try:
        from pyannote.audio import Pipeline
    except Exception as e:
        raise RuntimeError(f"pyannote-audio not installed: {e}")

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=token,
    )

    if diarization_device == "cuda" and torch.cuda.is_available():
        pipeline.to(torch.device("cuda"))
    else:
        pipeline.to(torch.device("cpu"))

    diar = pipeline(str(audio_path))
    diar_segments = []
    for turn, _, label in diar.itertracks(yield_label=True):
        diar_segments.append((float(turn.start), float(turn.end), str(label)))

    if not diar_segments:
        raise RuntimeError("No diarization segments produced by pyannote")

    return _assign_speaker_labels(chunks, diar_segments), "pyannote"


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
                    language: str = None,
                    use_diarization: bool = False,
                    hf_token: str = None,
                    diarization_device: str = "cpu") -> dict:
    t0 = time.time()
    print(f"\n  📂  {audio_path}")
    audio, sr = load_audio(audio_path)
    duration  = len(audio) / sr
    print(f"  Duration: {int(duration//60)}m {int(duration%60)}s")

    chunks = transcribe_audio(audio, sr, model, processor, language=language)

    diarization_backend = "heuristic"
    if use_diarization:
        try:
            print("  🔊 Running diarization with pyannote...")
            chunks, diarization_backend = add_true_diarization(
                chunks,
                audio_path=audio_path,
                hf_token=hf_token,
                diarization_device=diarization_device,
            )
            print(f"  ✅ Diarization backend: {diarization_backend}")
        except Exception as e:
            print(f"  ⚠  True diarization failed: {e}")
            print("     Falling back to heuristic speaker hints...")
            chunks = add_speaker_hints(chunks)
            diarization_backend = "heuristic_fallback"
    else:
        chunks = add_speaker_hints(chunks)

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
        "diarization_enabled":  bool(use_diarization),
        "diarization_backend":  diarization_backend,
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
    parser.add_argument("--base_model", type=str, default="openai/whisper-tiny",
                        help="HF model ID for fallback/custom use (e.g., openai/whisper-small or muktan174/whisper-medium-ekacare-medical)")
    parser.add_argument("--diarization", action="store_true",
                        help="Enable true speaker diarization via pyannote-audio (requires HF token)")
    parser.add_argument("--hf_token", type=str, default=None,
                        help="Hugging Face token for pyannote diarization model access")
    parser.add_argument("--diarization_device", type=str, default="cpu",
                        choices=["cpu", "cuda"],
                        help="Device for diarization model")
    parser.add_argument("--adapter_base_model", type=str, default=None,
                        help="Optional base model override when --base_model points to a PEFT adapter repo")
    args = parser.parse_args()

    if not args.audio and not args.audio_dir:
        print("Usage: python src/06_inference.py --audio FILE.wav [--output out.txt]")
        return

    print(f"\n{'='*60}")
    print(f"  Whisper Medical ASR — Inference")
    print(f"{'='*60}")

    model, processor = load_model(
        use_final=args.use_final,
        base_model=args.base_model,
        adapter_base_model=args.adapter_base_model,
    )

    if args.audio:
        result = transcribe_file(args.audio, model, processor,
                                 language=args.language,
                                 use_diarization=args.diarization,
                                 hf_token=args.hf_token,
                                 diarization_device=args.diarization_device)
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
            r = transcribe_file(
                str(f), model, processor,
                language=args.language,
                use_diarization=args.diarization,
                hf_token=args.hf_token,
                diarization_device=args.diarization_device,
            )
            print_result(r)
            all_results.append(r)
        out = d / "batch_transcripts.json"
        with open(out, "w", encoding="utf-8") as fp:
            json.dump(all_results, fp, indent=2, ensure_ascii=False)
        print(f"\n  💾  Batch saved → {out}")


if __name__ == "__main__":
    main()