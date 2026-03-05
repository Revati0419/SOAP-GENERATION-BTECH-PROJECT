#!/usr/bin/env python3
"""
SOAP Note Generator using Open-Source LLM (Ollama)
Generates structured SOAP notes from mental health conversations in Marathi/Hindi
"""

import json
import os
import argparse
import requests
from pathlib import Path
from tqdm import tqdm
from typing import Dict, List, Optional

# Ollama API endpoint
OLLAMA_URL = "http://localhost:11434/api/generate"

# SOAP generation prompt template - English
SOAP_PROMPT_TEMPLATE = """You are a clinical documentation specialist. Generate a SOAP note from the following mental health conversation between a doctor and patient.

The conversation is in {language} ({dialect} dialect). The patient has a PHQ-8 score of {phq8_score} indicating {severity} depression severity.

### Conversation:
{conversation}

### Instructions:
Generate a structured SOAP note with the following sections:

**Subjective (S):** Patient's reported symptoms, feelings, concerns, history in their own words. Include:
- Chief complaint
- History of present illness
- Sleep, appetite, mood changes
- Suicidal ideation (if mentioned)
- Social/occupational functioning

**Objective (O):** Observable clinical findings mentioned or implied:
- Appearance, behavior, speech patterns
- Mood and affect observed
- Thought process/content
- Cognitive functioning
- PHQ-8 score: {phq8_score}

**Assessment (A):** Clinical impression:
- Primary diagnosis consideration
- Severity level: {severity}
- Risk assessment
- Contributing factors

**Plan (P):** Recommended next steps:
- Treatment recommendations
- Therapy/counseling needs
- Medication considerations (if applicable)
- Follow-up schedule
- Safety planning (if needed)

Generate the SOAP note in {output_language}. Be concise but thorough.

### SOAP Note:"""

# Better Marathi-specific prompt
SOAP_PROMPT_MARATHI = """तुम्ही एक वैद्यकीय दस्तऐवजीकरण तज्ञ आहात. खालील मानसिक आरोग्य संभाषणावरून SOAP नोट तयार करा.

रुग्णाचा PHQ-8 स्कोअर: {phq8_score} ({severity} तीव्रता)

### संभाषण:
{conversation}

### सूचना:
खालील विभागांसह मराठीत SOAP नोट तयार करा:

**व्यक्तिनिष्ठ (S - Subjective):**
- मुख्य तक्रार काय आहे
- सध्याच्या आजाराचा इतिहास
- झोप, भूक, मूड मधील बदल
- आत्महत्येचे विचार (असल्यास)
- सामाजिक/व्यावसायिक कार्य

**वस्तुनिष्ठ (O - Objective):**
- दिसणारे वर्तन आणि बोलण्याची पद्धत
- मूड आणि भावना
- विचार प्रक्रिया
- PHQ-8 स्कोअर: {phq8_score}

**मूल्यांकन (A - Assessment):**
- प्राथमिक निदान
- तीव्रता पातळी: {severity}
- जोखीम मूल्यांकन

**योजना (P - Plan):**
- उपचार शिफारसी
- थेरपी/समुपदेशन
- पाठपुरावा वेळापत्रक
- सुरक्षा नियोजन (आवश्यक असल्यास)

संपूर्ण SOAP नोट शुद्ध मराठीत लिहा. इंग्रजी शब्द वापरू नका.

### SOAP नोट:"""


def format_conversation(turns: List[Dict], max_turns: int = 50) -> str:
    """Format conversation turns for the prompt"""
    lines = []
    # Use first and last turns if too long
    if len(turns) > max_turns:
        selected = turns[:max_turns//2] + turns[-max_turns//2:]
    else:
        selected = turns
    
    for turn in selected:
        role = turn.get('role', 'Unknown')
        text = turn.get('text', '')
        lines.append(f"{role}: {text}")
    
    return "\n".join(lines)


def generate_soap_ollama(prompt: str, model: str = "gemma2:2b", 
                         temperature: float = 0.3) -> str:
    """Generate SOAP note using Ollama API"""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": 1024,  # Max tokens
                }
            },
            timeout=600  # Increased to 10 minutes for larger models on CPU
        )
        response.raise_for_status()
        result = response.json()
        return result.get('response', '').strip()
    except Exception as e:
        print(f"Error generating SOAP: {e}")
        return ""


def process_session(session_data: Dict, dialect: str = "standard_pune",
                    output_language: str = "both", model: str = "gemma2:2b") -> Dict:
    """Process a single session and generate SOAP note in English, Marathi, or both"""
    
    # Get conversation turns
    turns = session_data.get('dialects', {}).get(dialect, [])
    if not turns:
        # Fallback to first available dialect
        dialects = session_data.get('dialects', {})
        if dialects:
            dialect = list(dialects.keys())[0]
            turns = dialects[dialect]
    
    if not turns:
        return {"error": "No conversation turns found"}
    
    # Format conversation
    conversation = format_conversation(turns)
    
    # Get metadata
    phq8_score = session_data.get('phq8_score', 'Unknown')
    severity = session_data.get('severity', 'Unknown')
    
    # Determine language from dialect
    language_map = {
        "standard_pune": "Marathi",
        "mumbai": "Marathi",
        "vidarbha": "Marathi",
        "marathwada": "Marathi",
        "konkan": "Marathi",
        "standard_hindi": "Hindi",
        "mumbai_hindi": "Hindi",
        "bhojpuri": "Hindi",
    }
    language = language_map.get(dialect, "Marathi")
    
    # Initialize result
    soap_note = {
        'session_id': session_data.get('session_id'),
        'dialect': dialect,
        'phq8_score': phq8_score,
        'severity': severity,
    }
    
    # Determine which languages to generate
    if output_language.lower() == 'both':
        languages_to_generate = ['English', 'Marathi']
    else:
        languages_to_generate = [output_language]
    
    # Generate SOAP note for each language
    for out_lang in languages_to_generate:
        print(f"    Generating {out_lang} SOAP...")
        
        # Use language-specific prompt for better quality
        if out_lang.lower() == 'marathi':
            # Use Marathi-specific prompt for better output
            prompt = SOAP_PROMPT_MARATHI.format(
                phq8_score=phq8_score,
                severity=severity,
                conversation=conversation
            )
        else:
            # Use English prompt
            prompt = SOAP_PROMPT_TEMPLATE.format(
                language=language,
                dialect=dialect.replace("_", " ").title(),
                phq8_score=phq8_score,
                severity=severity,
                conversation=conversation,
                output_language=out_lang
            )
        
        # Generate SOAP note
        soap_text = generate_soap_ollama(prompt, model=model)
        
        # Parse SOAP sections
        parsed = parse_soap_sections(soap_text)
        
        # Store with language key
        lang_key = out_lang.lower()
        soap_note[f'soap_{lang_key}'] = {
            'subjective': parsed['subjective'],
            'objective': parsed['objective'],
            'assessment': parsed['assessment'],
            'plan': parsed['plan'],
            'raw_output': soap_text
        }
    
    return soap_note


def parse_soap_sections(text: str) -> Dict:
    """Parse SOAP note text into structured sections"""
    sections = {
        'subjective': '',
        'objective': '',
        'assessment': '',
        'plan': ''
    }
    
    # Simple parsing based on section headers
    current_section = None
    lines = text.split('\n')
    
    for line in lines:
        line_lower = line.lower().strip()
        
        if 'subjective' in line_lower or line_lower.startswith('s:') or line_lower.startswith('**s'):
            current_section = 'subjective'
            continue
        elif 'objective' in line_lower or line_lower.startswith('o:') or line_lower.startswith('**o'):
            current_section = 'objective'
            continue
        elif 'assessment' in line_lower or line_lower.startswith('a:') or line_lower.startswith('**a'):
            current_section = 'assessment'
            continue
        elif 'plan' in line_lower or line_lower.startswith('p:') or line_lower.startswith('**p'):
            current_section = 'plan'
            continue
        
        if current_section and line.strip():
            sections[current_section] += line.strip() + ' '
    
    # Clean up
    for key in sections:
        sections[key] = sections[key].strip()
    
    return sections


def main():
    parser = argparse.ArgumentParser(description="Generate SOAP notes from conversations")
    parser.add_argument('--input-dir', type=str, default='data/dialect_marathi',
                        help='Input directory with conversation files')
    parser.add_argument('--output-dir', type=str, default='data/soap_notes',
                        help='Output directory for SOAP notes')
    parser.add_argument('--dialect', type=str, default='standard_pune',
                        help='Dialect to use for generation')
    parser.add_argument('--output-language', type=str, default='both',
                        choices=['English', 'Marathi', 'Hindi', 'both'],
                        help='Language for SOAP note output (use "both" for English + Marathi)')
    parser.add_argument('--model', type=str, default='gemma2:2b',
                        help='Ollama model to use')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of files to process')
    parser.add_argument('--ids', type=str, default=None,
                        help='Comma-separated session IDs to process')
    parser.add_argument('--test', action='store_true',
                        help='Test mode: process only first file')
    
    args = parser.parse_args()
    
    # Setup paths
    project_root = Path(__file__).parent.parent
    input_dir = project_root / args.input_dir
    output_dir = project_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get input files
    input_files = sorted(input_dir.glob('*_marathi.json'))
    
    # Filter by IDs if specified
    if args.ids:
        target_ids = set(args.ids.split(','))
        input_files = [f for f in input_files if f.stem.split('_')[0] in target_ids]
    
    # Apply limit
    if args.test:
        input_files = input_files[:1]
    elif args.limit:
        input_files = input_files[:args.limit]
    
    print(f"\n{'='*60}")
    print(f"  SOAP NOTE GENERATION")
    print(f"  Model: {args.model}")
    print(f"  Dialect: {args.dialect}")
    print(f"  Output Language: {args.output_language}")
    print(f"  Files to process: {len(input_files)}")
    print(f"{'='*60}\n")
    
    # Check Ollama connection
    try:
        requests.get("http://localhost:11434/api/tags", timeout=5)
    except:
        print("ERROR: Ollama server not running. Start with: ollama serve")
        return
    
    # Process files
    for filepath in tqdm(input_files, desc="Generating SOAP notes"):
        session_id = filepath.stem.split('_')[0]
        output_file = output_dir / f"{session_id}_soap.json"
        
        # Skip if already exists
        if output_file.exists():
            continue
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # Generate SOAP note
            soap_note = process_session(
                session_data,
                dialect=args.dialect,
                output_language=args.output_language,
                model=args.model
            )
            
            # Save output
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(soap_note, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"\nError processing {filepath.name}: {e}")
    
    print(f"\n✅ SOAP notes saved to: {output_dir}")


if __name__ == "__main__":
    main()
