# backend_api.py (Place in ROOT folder)
from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import json
import time
import asyncio
import subprocess
import tempfile
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from collections import defaultdict

# Ensure the server can find your src and scripts folders
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.run_pipeline import SOAPPipeline
from src.generation import MultilingualSOAPGenerator
from src.clinic_db import ClinicRepository

app = FastAPI(title="Multilingual SOAP Generation API")

# Allow React to communicate with this Python server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize your pipeline exactly how you do in your script
config = {
    'llm_model': 'gemma2:2b', # Make sure this matches your Ollama model
    'use_ner': True,
    'use_rag': True,
    'use_translation': True,
    'translator_type': 'nllb',  # Use NLLB instead of gated IndicTrans2
    'device': 'cpu' 
}
pipeline = SOAPPipeline(config)

# Initialize new multilingual generator
multilingual_generator = MultilingualSOAPGenerator(config)

repo = ClinicRepository(Path("data/clinic.db"))


class TranscriptInput(BaseModel):
    """Raw transcript input"""
    conversation: str
    phq8_score: Optional[int] = 0
    severity: Optional[str] = "unknown"
    gender: Optional[str] = "unknown"
    target_lang: Optional[str] = None  # Auto-detect if not provided


class PatientCreate(BaseModel):
    full_name: str
    age: Optional[int] = None
    gender: Optional[str] = "unknown"
    phone: Optional[str] = None
    notes: Optional[str] = None


class SessionCreate(BaseModel):
    patient_id: int
    source_type: str = "transcript"
    transcript: Optional[str] = None
    target_lang: Optional[str] = "marathi"
    input_lang: Optional[str] = None
    phq8_score: Optional[int] = 0
    severity: Optional[str] = "unknown"
    gender: Optional[str] = "unknown"
    soap_english: Optional[Dict[str, Any]] = None
    soap_target: Optional[Dict[str, Any]] = None
    full_result: Optional[Dict[str, Any]] = None


def _build_session_from_transcript(
    transcript: str,
    filename: str,
    language: str,
    phq8_score: int,
    severity: str,
    gender: str,
    chunks: Optional[list] = None,
) -> dict:
    """Create session-like payload for generate_from_session from ASR output."""

    def infer_doctor_speaker(chunk_rows: list) -> Optional[str]:
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
            if row.get("chunk_id", 999999) <= 1:
                scores[speaker] += 0.5

        if scores:
            return max(scores, key=scores.get)

        for row in chunk_rows:
            sp = row.get("speaker")
            if sp:
                return str(sp)
        return None

    doctor_speaker = infer_doctor_speaker(chunks or [])

    turns = []
    if chunks:
        for idx, c in enumerate(chunks):
            text = (c.get("text") or "").strip()
            if not text:
                continue
            speaker = (c.get("speaker") or "").upper()
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

    if not turns and transcript:
        lines = [ln.strip() for ln in transcript.splitlines() if ln.strip()]
        for idx, line in enumerate(lines):
            role = "Doctor" if idx % 2 == 0 else "Patient"
            turns.append({"turn_id": idx + 1, "role": role, "text": line})

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

    if language == "english":
        session_data["text_en"] = transcript

    return session_data


def _sync_transcribe_audio(
    audio_bytes: bytes,
    filename: str,
    language: str,
    base_model: str,
    diarization: bool = False,
):
    project_root = Path(__file__).resolve().parent
    script_path = project_root / "scripts" / "custom_diarized_transcription.py"
    venv_python = project_root / ".venv" / "bin" / "python"

    if not script_path.exists():
        raise RuntimeError(f"Custom transcription script not found: {script_path}")

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

        cmd.extend(["--language", "english"])
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
            "language": "english",
            "base_model": base_model,
            "diarization_enabled": data.get("diarization_enabled", diarization),
            "diarization_backend": data.get("diarization_backend", "heuristic"),
        }


@app.post("/api/generate-from-transcript")
async def generate_from_transcript(input_data: TranscriptInput):
    try:
        # Force target_lang to marathi for your project requirement
        result = multilingual_generator.generate_from_transcript(
            conversation=input_data.conversation,
            phq8_score=input_data.phq8_score,
            severity=input_data.severity,
            gender=input_data.gender,
            target_lang="marathi" 
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/patients")
async def list_patients(query: Optional[str] = None, limit: int = 50):
    """List/search patients by name."""
    return {
        "patients": repo.list_patients(query=query, limit=limit),
        "query": query,
        "limit": limit,
    }


@app.post("/api/patients")
async def create_patient(patient: PatientCreate):
    """Create a new patient record."""
    if not patient.full_name or not patient.full_name.strip():
        raise HTTPException(status_code=400, detail="full_name is required")
    if patient.age is not None and (patient.age < 0 or patient.age > 130):
        raise HTTPException(status_code=400, detail="age must be between 0 and 130")
    created = repo.create_patient(patient.model_dump())
    return {"patient": created}


@app.get("/api/patients/{patient_id}")
async def get_patient(patient_id: int):
    patient = repo.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"patient": patient}


@app.get("/api/patients/{patient_id}/sessions")
async def list_patient_sessions(patient_id: int, limit: int = 100):
    patient = repo.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "patient": patient,
        "sessions": repo.list_sessions_for_patient(patient_id=patient_id, limit=limit),
    }


@app.post("/api/sessions")
async def create_session(session: SessionCreate):
    payload = session.model_dump()
    
    # Ensure we extract the 'soap_marathi' dictionary for the database
    if payload.get("full_result"):
        full = payload["full_result"]
        # Pull the marathi 10-section dictionary
        payload["soap_target"] = full.get("soap_marathi")
        payload["soap_english"] = full.get("soap_english")
        payload["target_lang"] = "marathi"

    try:
        created = repo.create_session(payload)
        return {"session": created}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/sessions")
async def list_recent_sessions(limit: int = 100):
    return {"sessions": repo.list_recent_sessions(limit=limit), "limit": limit}


@app.get("/api/stats")
async def get_stats():
    stats = repo.get_stats()
    stats["timestamp"] = time.time()
    return stats


@app.post("/api/generate-from-json")
async def generate_from_json(
    file: UploadFile = File(...),
    target_lang: str = Form("marathi")
):
    """
    UPDATED: Generate SOAP from structured JSON file
    Now uses multilingual generator for better language handling
    """
    try:
        # 1. Read the uploaded JSON file
        contents = await file.read()
        session_data = json.loads(contents)

        print(f"🚀 Processing JSON file: {file.filename}")
        
        # 2. Use new multilingual generator
        result = multilingual_generator.generate_from_session(
            session_data=session_data,
            dialect=None,  # Auto-detect
            target_lang=target_lang
        )

        return result.to_dict()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-from-json-legacy")
async def generate_from_json_legacy(
    file: UploadFile = File(...),
    target_lang: str = Form("marathi")
):
    """
    LEGACY ENDPOINT: Old pipeline for backward compatibility
    """
    try:
        # 1. Read the uploaded JSON file
        contents = await file.read()
        session_data = json.loads(contents)

        print(f"🚀 Processing JSON file (legacy): {file.filename}")
        
        # 2. Call your pipeline (it uses 'standard_pune' by default)
        result = pipeline.process_session(
            session_data=session_data,
            dialect="standard_pune",
            target_lang=target_lang
        )

        if "soap_english" not in result:
            raise ValueError("Pipeline did not return 'soap_english' in the result")

        return result
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}


@app.post("/api/transcribe-audio")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("english"),
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

        if language not in {"english"}:
            raise HTTPException(
                status_code=400,
                detail="Invalid language. Only english is supported currently.",
            )

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
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Audio transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-from-audio")
async def generate_from_audio(
    file: UploadFile = File(...),
    target_lang: str = Form("marathi"),
    language: str = Form("english"),
    base_model: str = Form("openai/whisper-small"),
    diarization: bool = Form(False),
    phq8_score: int = Form(0),
    severity: str = Form("unknown"),
    gender: str = Form("unknown"),
):
    """One-shot flow: audio -> transcription -> SOAP generation."""
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

        if language not in {"english"}:
            raise HTTPException(
                status_code=400,
                detail="Invalid language. Only english is supported currently.",
            )

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

        note = multilingual_generator.generate_from_session(
            session_data=session_data,
            dialect=None,
            target_lang=target_lang,
        )
        soap_result = note.to_dict()

        soap_en = soap_result.get("soap_english") or {}
        has_content = any((soap_en.get(k) or "").strip() for k in ["subjective", "objective", "assessment", "plan"])
        if not has_content:
            note = multilingual_generator.generate_from_transcript(
                conversation=transcript,
                phq8_score=phq8_score,
                severity=severity,
                gender=gender,
                target_lang=target_lang,
            )
            soap_result = note.to_dict()

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
        return soap_result
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Audio->SOAP error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)