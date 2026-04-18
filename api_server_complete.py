#!/usr/bin/env python3
"""
SOAP Generation API Server
- ALL models loaded in parallel at startup (no lazy loading)
- Response format matches frontend SoapNoteViewer expectations
"""

import sys
import time
import json
import asyncio
import subprocess
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent))

# ============================================================================
# GLOBALS — filled during parallel startup loading
# ============================================================================
translator   = None
ner_model    = None
rag_store    = None
pipeline     = None
multilingual_generator = None
qlora_path   = Path("outputs/qlora_v1")

# ============================================================================
# PARALLEL MODEL LOADERS
# ============================================================================

def _load_translator():
    global translator
    t0 = time.time()
    try:
        from src.translation import get_translator
        translator = get_translator(model_type='nllb', device='cpu')
        # Force model weights into memory RIGHT NOW (not on first call)
        translator.load_model()
        print(f"   ✅ [NLLB-200]   loaded in {time.time()-t0:.1f}s")
    except Exception as e:
        print(f"   ⚠️  [NLLB-200]   failed: {e}")

def _load_ner():
    global ner_model
    t0 = time.time()
    try:
        from src.ner import get_ner_model
        # rule_based = no 400MB HuggingFace download, just regex — fast & works great
        # swap to 'indic' if you have the model cached already
        ner_model = get_ner_model(model_type='rule_based', device='cpu')
        print(f"   ✅ [NER/rules]  loaded in {time.time()-t0:.1f}s")
    except Exception as e:
        print(f"   ⚠️  [NER]        failed: {e}")

def _load_rag():
    global rag_store
    t0 = time.time()
    try:
        from src.rag import ClinicalVectorStore, ClinicalTermDatabase
        rag_store = ClinicalVectorStore(persist_dir="chromadb_data")
        rag_store.load()
        print(f"   ✅ [ChromaDB]   loaded in {time.time()-t0:.1f}s")
    except Exception as e:
        print(f"   ⚠️  [ChromaDB]   failed: {e}")

def _verify_gemma():
    t0 = time.time()
    try:
        result = subprocess.run(
            ['ollama', 'list'], capture_output=True, text=True, timeout=5
        )
        if 'gemma2:2b' in result.stdout:
            print(f"   ✅ [Gemma 2B]   ready in {time.time()-t0:.1f}s")
        else:
            print("   ⚠️  [Gemma 2B]   NOT found — run: ollama pull gemma2:2b")
    except Exception as e:
        print(f"   ⚠️  [Gemma 2B]   Ollama check failed: {e}")

def _check_qlora():
    if qlora_path.exists():
        print(f"   ✅ [QLoRA]      found at {qlora_path}")
    else:
        print(f"   ℹ️  [QLoRA]      not present (optional)")

# ============================================================================
# STARTUP: load everything IN PARALLEL, then wire into generator
# ============================================================================

print("""
╔═══════════════════════════════════════════════════════════════╗
║     MULTILINGUAL SOAP — PARALLEL STARTUP                      ║
╚═══════════════════════════════════════════════════════════════╝
""")
print("🚀 Loading all models in parallel...\n")
startup_t0 = time.time()

with ThreadPoolExecutor(max_workers=4) as pool:
    futures = [
        pool.submit(_load_translator),
        pool.submit(_load_ner),
        pool.submit(_load_rag),
        pool.submit(_verify_gemma),
    ]
    for f in futures:
        f.result()          # wait for all, propagate any exceptions

_check_qlora()

# Wire models into pipeline / generator AFTER all threads done
config = {
    'llm_model':       'gemma2:2b',
    'use_ner':         ner_model  is not None,
    'use_rag':         rag_store  is not None,
    '_rag_store':      rag_store,           # ← RAG now reachable inside generator
    'use_translation': True,
    'translator_type': 'nllb',
    'device':          'cpu',
}

from scripts.run_pipeline import SOAPPipeline
from src.generation import MultilingualSOAPGenerator

pipeline              = SOAPPipeline(config)
multilingual_generator = MultilingualSOAPGenerator(config)

# Inject pre-loaded objects — generator will NOT re-download anything
multilingual_generator._translator        = translator
multilingual_generator._translator_loaded = True
multilingual_generator._ner               = ner_model
multilingual_generator._ner_loaded        = True

# Also inject into pipeline
pipeline._translator = translator
pipeline._ner        = ner_model

print(f"\n✅ ALL MODELS READY in {time.time()-startup_t0:.1f}s total\n")
print(f"   Translation : {'NLLB-200'  if translator else '— (skip)'}")
print(f"   NER         : {'rule-based' if ner_model  else '— (skip)'}")
print(f"   RAG/ChromaDB: {'yes'        if rag_store  else '— (skip)'}")
print(f"   LLM         : Gemma 2B via Ollama")
print(f"   QLoRA       : {'yes' if qlora_path.exists() else '— (optional)'}\n")

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(title="Multilingual SOAP Generation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TranscriptInput(BaseModel):
    conversation: str
    phq8_score:   Optional[int] = 0
    severity:     Optional[str] = "unknown"
    gender:       Optional[str] = "unknown"
    target_lang:  Optional[str] = None


def _build_session_from_transcript(
    transcript: str,
    filename: str,
    language: str,
    phq8_score: int,
    severity: str,
    gender: str,
    chunks: Optional[list] = None,
) -> dict:
    """Create a session-like payload so audio transcripts can flow through generate_from_session path."""
    def infer_doctor_speaker(chunk_rows: list) -> Optional[str]:
        """
        Infer which diarization speaker is likely the clinician.
        Heuristics: more questions + clinical cue words.
        """
        if not chunk_rows:
            return None

        scores = defaultdict(float)
        clinical_cues = [
            "how are you", "since when", "do you", "are you", "any", "take", "tablet",
            "medicine", "follow up", "next visit", "dose", "symptoms", "diagnosis",
            "तुम्हाला", "तुम्ही", "औषध", "डॉक्टर", "लक्षण", "काय वाटते",
            "आपको", "दवा", "लक्षण", "कैसा", "कब से",
        ]
        patient_first_person = ["i ", " i'm", " मला", " माझ", "मुझे", " मैं", "mai "]

        for row in chunk_rows:
            speaker = str(row.get("speaker") or "").strip()
            if not speaker:
                continue
            text = (row.get("text") or "").lower()
            if not text:
                continue

            if "?" in text:
                scores[speaker] += 2.0

            for cue in clinical_cues:
                if cue in text:
                    scores[speaker] += 0.8

            for cue in patient_first_person:
                if cue in text:
                    scores[speaker] -= 0.4

            # Slight bias toward earlier speaker as doctor in clinical interviews
            if row.get("chunk_id", 999999) <= 1:
                scores[speaker] += 0.5

        if scores:
            return max(scores, key=scores.get)

        # fallback: first seen speaker
        for row in chunk_rows:
            sp = row.get("speaker")
            if sp:
                return str(sp)
        return None

    doctor_speaker = infer_doctor_speaker(chunks or [])

    # Build role-labeled turns (required by generate_from_session)
    turns = []
    if chunks:
        for idx, c in enumerate(chunks):
            text = (c.get("text") or "").strip()
            if not text:
                continue
            speaker = (c.get("speaker") or "").upper()
            # Role map from inferred clinician speaker, fallback A/B rule
            if doctor_speaker and (str(c.get("speaker")) == doctor_speaker):
                role = "Doctor"
            elif speaker == "A":
                role = "Doctor"
            else:
                role = "Patient"
            turns.append({
                "turn_id": idx + 1,
                "role": role,
                "text": text,
            })

    # Fallback if chunk metadata is missing
    if not turns and transcript:
        lines = [ln.strip() for ln in transcript.splitlines() if ln.strip()]
        for idx, line in enumerate(lines):
            role = "Doctor" if idx % 2 == 0 else "Patient"
            turns.append({
                "turn_id": idx + 1,
                "role": role,
                "text": line,
            })

    session_data = {
        "session_id": f"audio_{int(time.time())}",
        "text": transcript,
        "turns": turns,
        "phq8_score": phq8_score,
        "severity": severity,
        "gender": gender,
        "source": "whisper_audio",
        "audio_filename": filename,
        "asr_language": language,
    }

    # If audio is explicitly English, provide text_en for direct Phase-1 routing.
    if language == "english":
        session_data["text_en"] = transcript

    return session_data


# ============================================================================
# RESPONSE HELPER
# Fix: MultilingualSOAPNote.to_dict() returns {english, marathi, metadata}
# but SoapNoteViewer.jsx reads data.soap_english / data.soap_marathi
# ============================================================================

def _normalise_response(raw: dict, target_lang: str, elapsed: float) -> dict:
    """
    Always returns BILINGUAL output regardless of input language:

      soap_english        → English SOAP   (always present)
      soap_<target_lang>  → Target SOAP    (marathi / hindi / english)

    When target_lang == 'english', both keys contain the same English SOAP.
    to_dict() now emits soap_english + soap_<lang> directly — no legacy keys.
    """
    english_soap = raw.get('soap_english', {})
    target_soap  = raw.get(f'soap_{target_lang}', english_soap)
    meta         = raw.get('metadata', {})

    response = {
        "soap_english":         english_soap,
        f"soap_{target_lang}":  target_soap,
        "input_language":       meta.get('input_language'),
        "target_language":      target_lang,
        "session_id":           meta.get('session_id'),
        "metadata": {
            **meta,
            "processing_time":  f"{elapsed:.2f}s",
            "bilingual_output": True,
        },
        "entities": raw.get('entities'),
    }

    # If target is english, also set soap_marathi=null so frontend doesn't crash
    if target_lang == 'english':
        response['soap_marathi'] = None

    return response


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {
        "status": "ready",
        "models": {
            "translation": "NLLB-200"   if translator else None,
            "ner":         "rule-based" if ner_model  else None,
            "rag":         "ChromaDB"   if rag_store  else None,
            "llm":         "gemma2:2b",
            "qlora":       "available"  if qlora_path.exists() else None,
        },
    }


@app.get("/health")
async def health():
    return {
        "status":        "healthy",
        "models_loaded": True,
        "translator":    translator  is not None,
        "ner":           ner_model   is not None,
        "rag":           rag_store   is not None,
    }


@app.post("/api/generate-from-transcript")
async def generate_from_transcript(input_data: TranscriptInput):
    """Generate SOAP from a raw text transcript."""
    try:
        print(f"\n🚀 /generate-from-transcript  ({len(input_data.conversation)} chars)")
        target = input_data.target_lang or "marathi"

        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            _sync_generate_transcript,
            input_data.conversation,
            input_data.phq8_score,
            input_data.severity,
            input_data.gender,
            target,
        )
        print("   ✅ done\n")
        return result

    except Exception as e:
        print(f"   ❌ {e}\n")
        raise HTTPException(status_code=500, detail=str(e))


def _sync_generate_transcript(conversation, phq8_score, severity, gender, target_lang):
    t0     = time.time()
    note   = multilingual_generator.generate_from_transcript(
        conversation=conversation,
        phq8_score=phq8_score,
        severity=severity,
        gender=gender,
        target_lang=target_lang,
    )
    return _normalise_response(note.to_dict(), target_lang, time.time() - t0)


@app.post("/api/generate-from-json")
async def generate_from_json(
    file:        UploadFile = File(...),
    target_lang: str        = Form("marathi"),
):
    """Generate SOAP from an uploaded session JSON file."""
    try:
        contents     = await file.read()
        session_data = json.loads(contents)
        print(f"\n🚀 /generate-from-json  ({file.filename})")

        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            _sync_generate_session,
            session_data,
            target_lang,
        )
        print("   ✅ done\n")
        return result

    except Exception as e:
        print(f"   ❌ {e}\n")
        raise HTTPException(status_code=500, detail=str(e))


def _sync_generate_session(session_data, target_lang):
    t0   = time.time()
    note = multilingual_generator.generate_from_session(
        session_data=session_data,
        dialect=None,
        target_lang=target_lang,
    )
    raw = note.to_dict()
    # attach session_id from source data if missing
    if not raw.get('metadata', {}).get('session_id'):
        raw.setdefault('metadata', {})['session_id'] = session_data.get('session_id')
    return _normalise_response(raw, target_lang, time.time() - t0)


@app.post("/api/generate-from-json-legacy")
async def generate_from_json_legacy(
    file:        UploadFile = File(...),
    target_lang: str        = Form("marathi"),
):
    """Legacy pipeline endpoint (backward-compat)."""
    try:
        contents     = await file.read()
        session_data = json.loads(contents)
        result       = pipeline.process_session(
            session_data=session_data,
            dialect="standard_pune",
            target_lang=target_lang,
        )
        if "soap_english" not in result:
            raise ValueError("Pipeline did not return 'soap_english'")
        return result
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/transcribe-audio")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("marathi"),
    base_model: str = Form("openai/whisper-small"),
    diarization: bool = Form(False),
):
    """Transcribe uploaded audio (mp3/wav/m4a/flac/ogg) using Whisper pipeline."""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        ext = Path(file.filename).suffix.lower()
        allowed = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}
        if ext not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format: {ext}. Use one of {sorted(allowed)}",
            )

        if language not in {"marathi", "english", "auto"}:
            raise HTTPException(
                status_code=400,
                detail="Invalid language. Use marathi, english, or auto.",
            )

        print(f"\n🎙️  /transcribe-audio  ({file.filename})")
        contents = await file.read()

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            _sync_transcribe_audio,
            contents,
            file.filename,
            language,
            base_model,
            diarization,
        )
        print("   ✅ transcription done\n")
        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"   ❌ {e}\n")
        raise HTTPException(status_code=500, detail=str(e))


def _sync_transcribe_audio(
    audio_bytes: bytes,
    filename: str,
    language: str,
    base_model: str,
    diarization: bool = False,
):
    project_root = Path(__file__).resolve().parent
    whisper_root = project_root / "whisper_asr_pipeline"
    script_path = whisper_root / "src" / "06_inference.py"
    venv_python = whisper_root / ".venv_whisper" / "bin" / "python"

    if not script_path.exists():
        raise RuntimeError(f"Whisper inference script not found: {script_path}")

    python_exec = str(venv_python if venv_python.exists() else Path(sys.executable))

    with tempfile.TemporaryDirectory(prefix="whisper_upload_") as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        input_ext = Path(filename).suffix or ".wav"
        input_path = tmp_dir_path / f"input{input_ext}"
        output_path = tmp_dir_path / "transcript.json"

        input_path.write_bytes(audio_bytes)

        cmd = [
            python_exec,
            str(script_path),
            "--audio",
            str(input_path),
            "--output",
            str(output_path),
            "--base_model",
            base_model,
        ]

        if language in {"marathi", "english"}:
            cmd.extend(["--language", language])

        if diarization:
            cmd.append("--diarization")

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=60 * 30,
        )

        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            stdout = (proc.stdout or "").strip()
            raise RuntimeError(
                "Whisper transcription failed.\n"
                f"STDERR:\n{stderr[-2000:]}\n"
                f"STDOUT:\n{stdout[-2000:]}"
            )

        if not output_path.exists():
            raise RuntimeError("Transcription finished but output JSON was not created")

        data = json.loads(output_path.read_text(encoding="utf-8"))
        return {
            "audio_filename": filename,
            "transcript": data.get("transcript", ""),
            "transcript_formatted": data.get("transcript_formatted", ""),
            "chunks": data.get("chunks", []),
            "n_chunks": data.get("n_chunks", 0),
            "duration_s": data.get("duration_s"),
            "processing_s": data.get("processing_s"),
            "rtf": data.get("rtf"),
            "language": language,
            "base_model": base_model,
            "diarization_enabled": data.get("diarization_enabled", diarization),
            "diarization_backend": data.get("diarization_backend", "heuristic"),
        }


@app.post("/api/generate-from-audio")
async def generate_from_audio(
    file: UploadFile = File(...),
    target_lang: str = Form("marathi"),
    language: str = Form("marathi"),
    base_model: str = Form("openai/whisper-small"),
    diarization: bool = Form(False),
    phq8_score: int = Form(0),
    severity: str = Form("unknown"),
    gender: str = Form("unknown"),
):
    """One-shot pipeline: audio -> Whisper transcript -> SOAP generation via session flow."""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        ext = Path(file.filename).suffix.lower()
        allowed = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}
        if ext not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format: {ext}. Use one of {sorted(allowed)}",
            )

        if language not in {"marathi", "english", "auto"}:
            raise HTTPException(
                status_code=400,
                detail="Invalid language. Use marathi, english, or auto.",
            )

        print(f"\n🎯 /generate-from-audio  ({file.filename})")
        contents = await file.read()

        loop = asyncio.get_event_loop()
        asr_result = await loop.run_in_executor(
            None,
            _sync_transcribe_audio,
            contents,
            file.filename,
            language,
            base_model,
            diarization,
        )

        transcript = (asr_result.get("transcript") or "").strip()
        if not transcript:
            raise HTTPException(status_code=500, detail="Whisper returned an empty transcript")

        session_data = _build_session_from_transcript(
            transcript=transcript,
            filename=file.filename,
            language=language,
            phq8_score=phq8_score,
            severity=severity,
            gender=gender,
            chunks=asr_result.get("chunks", []),
        )

        soap_result = await loop.run_in_executor(
            None,
            _sync_generate_session,
            session_data,
            target_lang,
        )

        # Retry with direct transcript path if parser produced empty sections.
        soap_en = soap_result.get("soap_english") or {}
        has_content = any((soap_en.get(k) or "").strip() for k in ["subjective", "objective", "assessment", "plan"])
        if not has_content:
            print("   ⚠️ empty SOAP from session path, retrying via transcript path...")
            soap_result = await loop.run_in_executor(
                None,
                _sync_generate_transcript,
                transcript,
                phq8_score,
                severity,
                gender,
                target_lang,
            )

        # Keep existing frontend contract while exposing ASR metadata for optional UI usage.
        soap_result["asr"] = {
            "audio_filename": asr_result.get("audio_filename"),
            "transcript": asr_result.get("transcript"),
            "transcript_formatted": asr_result.get("transcript_formatted"),
            "n_chunks": asr_result.get("n_chunks"),
            "duration_s": asr_result.get("duration_s"),
            "processing_s": asr_result.get("processing_s"),
            "rtf": asr_result.get("rtf"),
            "language": asr_result.get("language"),
            "base_model": asr_result.get("base_model"),
            "diarization_enabled": asr_result.get("diarization_enabled", diarization),
            "diarization_backend": asr_result.get("diarization_backend", "heuristic"),
        }
        print("   ✅ audio -> transcript -> soap done\n")
        return soap_result

    except HTTPException:
        raise
    except Exception as e:
        print(f"   ❌ {e}\n")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🌐  http://0.0.0.0:8000   (API)")
    print("📖  http://localhost:8000/docs  (Swagger)")
    print("🏥  http://localhost:8000/health")
    print("🎯  http://localhost:5174  (Frontend)")
    print("=" * 60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
