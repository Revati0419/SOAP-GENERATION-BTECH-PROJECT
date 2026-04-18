import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Optional

import librosa
import torch
from dotenv import load_dotenv
from huggingface_hub import list_repo_files, login
from pyannote.audio import Pipeline
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline


def _extract_annotation(diarization_result):
    if hasattr(diarization_result, "itertracks"):
        return diarization_result

    for attr in dir(diarization_result):
        if attr.startswith("__"):
            continue
        try:
            value = getattr(diarization_result, attr)
        except Exception:
            continue
        if hasattr(value, "itertracks"):
            return value
    return None


def _normalize_language(language: str) -> Optional[str]:
    # Current project mode: keep transcription input/output in English only.
    return "english"


def _clean_transcript_text(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""

    # Collapse very long single-character stretches: ummmmm -> ummm
    cleaned = re.sub(r"(.)\1{7,}", r"\1\1\1", cleaned)

    # Collapse repeated single words: जब जब जब ... / you you you ...
    cleaned = re.sub(r"\b([\w']+)(?:\s+\1){5,}\b", r"\1", cleaned, flags=re.IGNORECASE | re.UNICODE)

    # Collapse repeated short phrases: repeat that repeat that ...
    cleaned = re.sub(
        r"\b([\w']+(?:\s+[\w']+){1,3})(?:\s+\1){3,}\b",
        r"\1",
        cleaned,
        flags=re.IGNORECASE | re.UNICODE,
    )

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _is_hallucinated_or_low_info(text: str) -> bool:
    tokens = re.findall(r"[\w']+", (text or "").lower(), flags=re.UNICODE)
    if not tokens:
        return True

    if len(tokens) < 8:
        return False

    # Detect excessive token repetition runs
    max_run = 1
    current = 1
    for i in range(1, len(tokens)):
        if tokens[i] == tokens[i - 1]:
            current += 1
            max_run = max(max_run, current)
        else:
            current = 1

    unique_ratio = len(set(tokens)) / max(len(tokens), 1)
    return max_run >= 7 or unique_ratio < 0.2


def _build_whisper_pipeline(model_id: str, hf_token: str, dtype: torch.dtype, device_index: int):
    print("Loading Whisper model...")
    repo_files = []
    try:
        repo_files = list_repo_files(model_id, token=hf_token)
    except Exception:
        pass

    is_adapter_repo = (
        "adapter_config.json" in repo_files
        or "adapter_model.safetensors" in repo_files
        or "adapter_model.bin" in repo_files
    )

    if is_adapter_repo:
        adapter_base_model = os.getenv("ADAPTER_BASE_MODEL", "openai/whisper-medium")
        print(f"Detected adapter repo. Loading base model: {adapter_base_model}")
        try:
            from peft import PeftModel
        except Exception as e:
            raise RuntimeError(
                "Adapter repo detected but PEFT is missing. Install with: pip install peft"
            ) from e

        processor = AutoProcessor.from_pretrained(adapter_base_model, token=hf_token)
        base_model = AutoModelForSpeechSeq2Seq.from_pretrained(
            adapter_base_model,
            torch_dtype=dtype,
            low_cpu_mem_usage=True,
            token=hf_token,
        )
        model = PeftModel.from_pretrained(base_model, model_id, token=hf_token)
        if hasattr(model, "merge_and_unload"):
            model = model.merge_and_unload()

        return pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            device=device_index,
            dtype=dtype,
            chunk_length_s=30,
        )

    return pipeline(
        "automatic-speech-recognition",
        model=model_id,
        device=device_index,
        dtype=dtype,
        chunk_length_s=30,
    )


def _transcribe_full_audio(whisper_pipe, audio_path: str, language: Optional[str]) -> str:
    kwargs = {"task": "transcribe", "language": "english"}
    result = whisper_pipe(audio_path, generate_kwargs=kwargs)
    return _clean_transcript_text((result.get("text") or "").strip())


def main():
    parser = argparse.ArgumentParser(description="Custom diarized transcription for API/frontend integration")
    parser.add_argument("--audio", required=True, help="Input audio file path")
    parser.add_argument("--output", default="diarized_transcript.txt", help="Output file path (.json or .txt)")
    parser.add_argument("--language", default="english", help="Transcription language (fixed to english)")
    parser.add_argument("--base_model", default="muktan174/whisper-medium-ekacare-medical", help="HF model or adapter repo id")
    parser.add_argument("--diarization", action="store_true", help="Enable pyannote speaker diarization")
    args = parser.parse_args()

    started = time.time()
    load_dotenv()
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        raise RuntimeError("HF_TOKEN is not set. Add it to your .env before running this script.")

    login(token=hf_token)

    language = _normalize_language(args.language)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device_index = 0 if torch.cuda.is_available() else -1
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    whisper_pipe = _build_whisper_pipeline(args.base_model, hf_token, dtype, device_index)

    print("Loading audio for segmenting...")
    audio_data, sr = librosa.load(args.audio, sr=16000)
    duration_s = len(audio_data) / max(sr, 1)

    chunks = []
    transcript_lines = []
    diarization_backend = "none"

    if args.diarization:
        print("Loading Diarization model...")
        diarization_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=hf_token,
        ).to(device)

        print("Analyzing speakers (Diarization)...")
        diarization_result = diarization_pipeline(args.audio)
        annotation = _extract_annotation(diarization_result)

        if annotation is not None:
            diarization_backend = "pyannote"
            print("\n--- TRANSCRIPTION START ---\n")
            chunk_id = 1
            for turn, _, speaker in annotation.itertracks(yield_label=True):
                start, end = float(turn.start), float(turn.end)
                if end - start < 0.5:
                    continue

                audio_chunk = audio_data[int(start * sr):int(end * sr)]
                if len(audio_chunk) == 0:
                    continue

                kwargs = {"task": "transcribe", "language": "english"}

                segment_text = (
                    whisper_pipe(
                        {"sampling_rate": sr, "raw": audio_chunk},
                        generate_kwargs=kwargs,
                        return_timestamps=True,
                    ).get("text")
                    or ""
                ).strip()
                segment_text = _clean_transcript_text(segment_text)

                if not segment_text or _is_hallucinated_or_low_info(segment_text):
                    continue

                line = f"[{start:6.2f}s - {end:6.2f}s] {speaker}: {segment_text}"
                print(line)
                transcript_lines.append(line)
                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "start": round(start, 3),
                        "end": round(end, 3),
                        "speaker": str(speaker),
                        "text": segment_text,
                    }
                )
                chunk_id += 1

    if not chunks:
        print("Diarization disabled/unavailable. Running full-audio transcription...")
        full_text = _transcribe_full_audio(whisper_pipe, args.audio, language)
        full_text = full_text.strip()
        if full_text and not _is_hallucinated_or_low_info(full_text):
            transcript_lines = [f"[  0.00s - {duration_s:6.2f}s] SPEAKER_00: {full_text}"]
            chunks = [
                {
                    "chunk_id": 1,
                    "start": 0.0,
                    "end": round(duration_s, 3),
                    "speaker": "SPEAKER_00",
                    "text": full_text,
                }
            ]

    plain_transcript = "\n".join((c.get("text") or "").strip() for c in chunks if (c.get("text") or "").strip())
    formatted_transcript = "\n".join(transcript_lines)
    processing_s = time.time() - started

    payload = {
        "transcript": plain_transcript,
        "transcript_formatted": formatted_transcript,
        "chunks": chunks,
        "n_chunks": len(chunks),
        "duration_s": round(duration_s, 3),
        "processing_s": round(processing_s, 3),
        "rtf": round(processing_s / max(duration_s, 1e-6), 4),
    "language": "english",
        "base_model": args.base_model,
        "diarization_enabled": bool(args.diarization),
        "diarization_backend": diarization_backend,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.suffix.lower() == ".json":
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        output_path.write_text(formatted_transcript or plain_transcript, encoding="utf-8")

    print(f"\n🚀 Success! Output written to '{output_path}'")


if __name__ == "__main__":
    main()
