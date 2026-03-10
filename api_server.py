# backend_api.py (Place in ROOT folder)
from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import sys
from pathlib import Path

# Ensure the server can find your src and scripts folders
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.run_pipeline import SOAPPipeline

app = FastAPI()

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
    'use_rag': False,
    'use_translation': False,
    'device': 'cpu' 
}
pipeline = SOAPPipeline(config)


@app.post("/api/generate-from-json")
async def generate_from_json(
    file: UploadFile = File(...),
    target_lang: str = Form("marathi")
):
    try:
        # 1. Read the uploaded JSON file
        contents = await file.read()
        session_data = json.loads(contents)

        print(f"🚀 Processing JSON file: {file.filename}")
        
        # 2. Call your pipeline (it uses 'standard_pune' by default)
        result = pipeline.process_session(
            session_data=session_data,
            dialect="standard_pune",
            target_lang=target_lang
        )

        return result
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)