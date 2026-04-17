# backend_api.py (Place in ROOT folder)
from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import json
import sys
from pathlib import Path
from typing import Optional

# Ensure the server can find your src and scripts folders
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.run_pipeline import SOAPPipeline
from src.generation import MultilingualSOAPGenerator

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


class TranscriptInput(BaseModel):
    """Raw transcript input"""
    conversation: str
    phq8_score: Optional[int] = 0
    severity: Optional[str] = "unknown"
    gender: Optional[str] = "unknown"
    target_lang: Optional[str] = None  # Auto-detect if not provided


@app.post("/api/generate-from-transcript")
async def generate_from_transcript(input_data: TranscriptInput):
    """
    NEW ENDPOINT: Generate SOAP from raw transcript in any language
    
    Accepts: Marathi, Hindi, English, or mixed language transcript
    Returns: SOAP note in English + Input Language
    
    Example:
    {
        "conversation": "डॉक्टर: तुम्हाला कसे वाटते?\nरुग्ण: मला झोप येत नाही...",
        "phq8_score": 15,
        "severity": "moderate",
        "gender": "female",
        "target_lang": "marathi"
    }
    """
    try:
        print(f"🚀 Processing transcript (length: {len(input_data.conversation)} chars)")
        
        # Generate using new multilingual generator
        result = multilingual_generator.generate_from_transcript(
            conversation=input_data.conversation,
            phq8_score=input_data.phq8_score,
            severity=input_data.severity,
            gender=input_data.gender,
            target_lang=input_data.target_lang
        )
        
        return result.to_dict()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)