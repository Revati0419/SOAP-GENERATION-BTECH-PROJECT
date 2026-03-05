#!/usr/bin/env python3
"""
SOAP Note Generator v2 - Hybrid Approach
1. Generate high-quality English SOAP using LLM
2. Translate to Marathi using Google Translate API (better quality)

This gives much better Marathi output than direct Marathi generation.
"""

import json
import os
import argparse
import requests
import time
from pathlib import Path
from tqdm import tqdm
from typing import Dict, List, Optional

# Ollama API endpoint
OLLAMA_URL = "http://localhost:11434/api/generate"

# Clinical SOAP prompt - optimized for mental health
SOAP_PROMPT = """You are an experienced psychiatrist creating a clinical SOAP note from a mental health interview.

Patient Information:
- PHQ-8 Depression Score: {phq8_score}/24
- Severity Classification: {severity}
- Gender: {gender}

Interview Transcript:
{conversation}

Generate a detailed SOAP note following this exact format:

**SUBJECTIVE:**
- Chief Complaint: [Main reason for visit]
- History of Present Illness: [Current symptoms, onset, duration, triggers]
- Mood & Affect: [Patient's described emotional state]
- Sleep Pattern: [Quality, duration, disturbances]
- Appetite: [Changes, weight fluctuation]
- Energy Level: [Fatigue, motivation]
- Concentration: [Focus, memory issues]
- Social Functioning: [Relationships, work, daily activities]
- Suicidal/Self-harm Ideation: [Present/Absent, if present - plan, intent]
- Substance Use: [Alcohol, drugs, medications]

**OBJECTIVE:**
- Appearance: [Grooming, hygiene, dress]
- Behavior: [Psychomotor activity, eye contact, cooperation]
- Speech: [Rate, rhythm, volume, coherence]
- Mood: [Patient's stated mood]
- Affect: [Observed emotional expression - range, congruence]
- Thought Process: [Logical, organized, tangential, circumstantial]
- Thought Content: [Delusions, obsessions, phobias]
- Perception: [Hallucinations - auditory, visual]
- Cognition: [Orientation, attention, memory]
- Insight & Judgment: [Awareness of illness, decision-making]
- PHQ-8 Score: {phq8_score} ({severity})

**ASSESSMENT:**
- Primary Diagnosis: [DSM-5 diagnosis with code if applicable]
- Differential Diagnoses: [Other considerations]
- Severity: {severity}
- Risk Assessment: [Suicide risk - low/moderate/high, protective factors]
- Contributing Factors: [Psychosocial stressors, medical conditions]

**PLAN:**
- Psychotherapy: [Type - CBT, DBT, supportive; frequency]
- Pharmacotherapy: [Medications if indicated]
- Safety Plan: [If needed - crisis contacts, coping strategies]
- Lifestyle Modifications: [Sleep hygiene, exercise, social support]
- Follow-up: [Next appointment timing]
- Referrals: [If needed - specialist, support groups]

Be specific and clinically accurate based on the interview content."""


def format_conversation(turns: List[Dict], max_turns: int = 60) -> str:
    """Format conversation turns for the prompt"""
    lines = []
    if len(turns) > max_turns:
        # Take first half and last half for context
        selected = turns[:max_turns//2] + turns[-max_turns//2:]
    else:
        selected = turns
    
    for turn in selected:
        role = turn.get('role', 'Unknown')
        text = turn.get('text', '') or turn.get('text_en', '')
        if text:
            lines.append(f"{role}: {text}")
    
    return "\n".join(lines)


def generate_with_ollama(prompt: str, model: str = "gemma2:2b", 
                         temperature: float = 0.3, timeout: int = 180) -> str:
    """Generate text using Ollama API"""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": 1500,
                }
            },
            timeout=timeout
        )
        response.raise_for_status()
        result = response.json()
        return result.get('response', '').strip()
    except requests.exceptions.Timeout:
        print(f"  ⚠️ Timeout after {timeout}s")
        return ""
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return ""


def translate_to_marathi(text: str, retries: int = 3, delay: float = 0.3) -> str:
    """Translate English text to Marathi using Google Translate API"""
    if not text:
        return ""
    
    # Split into chunks if too long (API limit ~5000 chars)
    max_chunk = 4500
    if len(text) > max_chunk:
        chunks = []
        current = ""
        for line in text.split('\n'):
            if len(current) + len(line) > max_chunk:
                if current:
                    chunks.append(current)
                current = line
            else:
                current += '\n' + line if current else line
        if current:
            chunks.append(current)
        
        # Translate each chunk
        translated_chunks = []
        for chunk in chunks:
            translated = _google_translate(chunk, 'mr', retries, delay)
            translated_chunks.append(translated)
            time.sleep(delay)
        
        return '\n'.join(translated_chunks)
    
    return _google_translate(text, 'mr', retries, delay)


def _google_translate(text: str, target_lang: str, retries: int = 3, delay: float = 0.3) -> str:
    """Direct Google Translate API call"""
    for attempt in range(retries):
        try:
            params = {
                'client': 'gtx',
                'sl': 'en',
                'tl': target_lang,
                'dt': 't',
                'q': text
            }
            response = requests.get(
                'https://translate.googleapis.com/translate_a/single',
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            translated = ''.join([part[0] for part in result[0] if part[0]])
            return translated
            
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
            else:
                print(f"  ⚠️ Translation failed: {e}")
                return text
    
    return text


def parse_soap_sections(text: str, language: str = "english") -> Dict:
    """Parse SOAP note text into structured sections (supports English and Marathi)"""
    sections = {
        'subjective': '',
        'objective': '',
        'assessment': '',
        'plan': ''
    }
    
    current_section = None
    lines = text.split('\n')
    
    # Section headers in different languages
    section_markers = {
        'subjective': ['subjective', 'विषय', 'व्यक्तिनिष्ठ', 's:'],
        'objective': ['objective', 'उद्देश', 'वस्तुनिष्ठ', 'o:'],
        'assessment': ['assessment', 'मूल्यांकन', 'a:'],
        'plan': ['plan', 'योजना', 'p:']
    }
    
    for line in lines:
        line_lower = line.lower().strip()
        line_stripped = line.strip()
        
        # Check for section headers
        section_found = None
        for section, markers in section_markers.items():
            for marker in markers:
                if marker in line_lower or line_stripped.startswith(marker):
                    section_found = section
                    break
            if section_found:
                break
        
        if section_found:
            current_section = section_found
            continue
        
        if current_section and line.strip():
            sections[current_section] += line.strip() + '\n'
    
    # Clean up
    for key in sections:
        sections[key] = sections[key].strip()
    
    return sections


def process_session(session_data: Dict, dialect: str = "standard_pune",
                    model: str = "gemma2:2b", translate: bool = True) -> Dict:
    """
    Process a single session:
    1. Generate English SOAP (better quality)
    2. Translate to Marathi (optional)
    """
    
    # Get conversation turns
    turns = session_data.get('dialects', {}).get(dialect, [])
    if not turns:
        dialects = session_data.get('dialects', {})
        if dialects:
            dialect = list(dialects.keys())[0]
            turns = dialects[dialect]
    
    if not turns:
        return {"error": "No conversation turns found"}
    
    # Use English text for better LLM understanding
    conversation = format_conversation(turns)
    
    # Get metadata
    phq8_score = session_data.get('phq8_score', 'Unknown')
    severity = session_data.get('severity', 'Unknown')
    gender = session_data.get('gender', 'Unknown')
    
    # Build prompt
    prompt = SOAP_PROMPT.format(
        phq8_score=phq8_score,
        severity=severity,
        gender=gender,
        conversation=conversation
    )
    
    # Step 1: Generate English SOAP
    print(f"    📝 Generating English SOAP...")
    english_soap_text = generate_with_ollama(prompt, model=model)
    english_sections = parse_soap_sections(english_soap_text)
    
    result = {
        'session_id': session_data.get('session_id'),
        'dialect': dialect,
        'phq8_score': phq8_score,
        'severity': severity,
        'gender': gender,
        'soap_english': {
            'subjective': english_sections['subjective'],
            'objective': english_sections['objective'],
            'assessment': english_sections['assessment'],
            'plan': english_sections['plan'],
            'raw': english_soap_text
        }
    }
    
    # Step 2: Translate to Marathi (better quality than direct generation)
    if translate and english_soap_text:
        print(f"    🔄 Translating to Marathi...")
        marathi_soap_text = translate_to_marathi(english_soap_text)
        marathi_sections = parse_soap_sections(marathi_soap_text)
        
        result['soap_marathi'] = {
            'subjective': marathi_sections['subjective'],
            'objective': marathi_sections['objective'],
            'assessment': marathi_sections['assessment'],
            'plan': marathi_sections['plan'],
            'raw': marathi_soap_text
        }
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Generate SOAP notes (v2 - Hybrid)")
    parser.add_argument('--input-dir', type=str, default='data/dialect_marathi',
                        help='Input directory with conversation files')
    parser.add_argument('--output-dir', type=str, default='data/soap_notes',
                        help='Output directory for SOAP notes')
    parser.add_argument('--dialect', type=str, default='standard_pune',
                        help='Dialect to use')
    parser.add_argument('--model', type=str, default='gemma2:2b',
                        help='Ollama model to use')
    parser.add_argument('--no-translate', action='store_true',
                        help='Skip Marathi translation')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of files')
    parser.add_argument('--ids', type=str, default=None,
                        help='Comma-separated session IDs')
    parser.add_argument('--test', action='store_true',
                        help='Test mode: process only first file')
    parser.add_argument('--skip-existing', action='store_true', default=True,
                        help='Skip already processed files')
    
    args = parser.parse_args()
    
    # Setup paths
    project_root = Path(__file__).parent.parent
    input_dir = project_root / args.input_dir
    output_dir = project_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get input files
    input_files = sorted(input_dir.glob('*_marathi.json'))
    
    # Filter by IDs
    if args.ids:
        target_ids = set(args.ids.split(','))
        input_files = [f for f in input_files if f.stem.split('_')[0] in target_ids]
    
    # Apply limit
    if args.test:
        input_files = input_files[:1]
    elif args.limit:
        input_files = input_files[:args.limit]
    
    print(f"\n{'='*60}")
    print(f"  SOAP NOTE GENERATION v2 (Hybrid)")
    print(f"  Model: {args.model}")
    print(f"  Method: English SOAP → Translate to Marathi")
    print(f"  Files to process: {len(input_files)}")
    print(f"{'='*60}\n")
    
    # Check Ollama
    try:
        requests.get("http://localhost:11434/api/tags", timeout=5)
    except:
        print("❌ Ollama server not running. Start with: ollama serve")
        return
    
    # Process files
    success_count = 0
    for filepath in tqdm(input_files, desc="Generating SOAP notes"):
        session_id = filepath.stem.split('_')[0]
        output_file = output_dir / f"{session_id}_soap.json"
        
        # Skip existing
        if args.skip_existing and output_file.exists():
            continue
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # Generate SOAP
            soap_note = process_session(
                session_data,
                dialect=args.dialect,
                model=args.model,
                translate=not args.no_translate
            )
            
            # Save
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(soap_note, f, ensure_ascii=False, indent=2)
            
            success_count += 1
            
        except Exception as e:
            print(f"\n❌ Error processing {filepath.name}: {e}")
    
    print(f"\n✅ Generated {success_count} SOAP notes")
    print(f"📁 Output: {output_dir}")


if __name__ == "__main__":
    main()
