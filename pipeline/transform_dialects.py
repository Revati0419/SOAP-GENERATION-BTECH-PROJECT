"""
pipeline/transform_dialects.py
==============================
Transforms translated Marathi files to:
1. Simplified structure (no turn_id, start_time, stop_time)
2. 5 regional dialects: Standard Pune, Mumbai, Vidarbha, Marathwada, Konkan

Each dialect has unique:
- Verb endings
- Vocabulary
- Expressions
- Sentence patterns
"""

import json
import re
import random
from pathlib import Path
from tqdm import tqdm

TRANSLATED_DIR = Path("data/translated")
OUTPUT_DIR = Path("data/dialect_marathi")

# ═══════════════════════════════════════════════════════════════════════════════
# DIALECT TRANSFORMATION RULES
# ═══════════════════════════════════════════════════════════════════════════════

# ─── 1. STANDARD PUNE (Formal, literary) ──────────────────────────────────────
# This is the base - formal Marathi, no changes needed
PUNE_RULES = []  # Keep as-is (formal)

# ─── 2. MUMBAI MARATHI (Urban, Hindi/English mixed) ──────────────────────────
MUMBAI_RULES = [
    # Verb contractions
    (r'करत आहे', 'करतोय'),
    (r'करत आहेस', 'करतोयस'),
    (r'करत आहेत', 'करतायत'),
    (r'येत आहे', 'येतोय'),
    (r'जात आहे', 'जातोय'),
    (r'वाटत आहे', 'वाटतंय'),
    (r'होत आहे', 'होतंय'),
    (r'बसत आहे', 'बसतोय'),
    (r'राहत आहे', 'राहतोय'),
    
    # Past tense
    (r'झाले', 'झालं'),
    (r'केले', 'केलं'),
    (r'गेले', 'गेलं'),
    (r'आले', 'आलं'),
    (r'बोलले', 'बोललं'),
    (r'सांगितले', 'सांगितलं'),
    
    # Common words
    (r'नाही', 'नाय'),
    (r'आहे का', 'हाय का'),
    (r'चांगले', 'भारी'),
    (r'खूप चांगले', 'एकदम भारी'),
    (r'ठीक आहे', 'ठीके'),
    (r'तुम्हाला', 'तुला'),
    (r'तुमचे', 'तुझं'),
    (r'माझे', 'माझं'),
    (r'त्याचे', 'त्याचं'),
    
    # Add Hindi/English words
    (r'समजले', 'समजलं'),
    (r'होय', 'हां'),
    (r'कारण', 'क्युंकी'),
]

MUMBAI_FILLERS = ['यार', 'बॉस', 'भाई', 'अरे', 'चल', 'एक्चुअली', 'बेसिकली']

# ─── 3. VIDARBHA DIALECT (Nagpur area) ────────────────────────────────────────
VIDARBHA_RULES = [
    # Distinctive verb endings
    (r'नाही', 'नाय'),
    (r'आहे', 'हाय'),
    (r'होते', 'होतं'),
    (r'करत आहे', 'करतोय'),
    (r'वाटत नाही', 'वाटंना'),
    (r'येत नाही', 'येईना'),
    (r'जात नाही', 'जाईना'),
    (r'होत नाही', 'होईना'),
    (r'कळत नाही', 'कळंना'),
    (r'समजत नाही', 'समजंना'),
    (r'दिसत नाही', 'दिसंना'),
    (r'ऐकत नाही', 'ऐकंना'),
    
    # Unique Vidarbha words
    (r'काय', 'काऊन'),
    (r'कसे', 'कसं'),
    (r'असे', 'असं'),
    (r'तसे', 'तसं'),
    (r'चांगले', 'बरं'),
    (r'झाले', 'झालं'),
    (r'केले', 'केलं'),
    (r'गेले', 'गेलं'),
    
    # Pronouns
    (r'तुम्ही', 'तुमी'),
    (r'आम्ही', 'आमी'),
    (r'तुम्हाला', 'तुम्हाले'),
]

VIDARBHA_FILLERS = ['बग', 'व्हय', 'काऊन', 'अरे बाबा']

# ─── 4. MARATHWADA DIALECT (Aurangabad area) ──────────────────────────────────
MARATHWADA_RULES = [
    # Verb patterns
    (r'नाही', 'नाय'),
    (r'आहे', 'हाय'),
    (r'होते', 'व्हतं'),
    (r'करत आहे', 'करतुया'),
    (r'येत आहे', 'येतुया'),
    (r'जात आहे', 'जातुया'),
    (r'वाटत आहे', 'वाटतंय'),
    
    # Past tense
    (r'झाले', 'झालं'),
    (r'केले', 'केलं'),
    (r'गेले', 'गेलं'),
    (r'आले', 'आलं'),
    
    # Unique words
    (r'काय', 'काय'),
    (r'कसे आहात', 'कसं हाय'),
    (r'कसे आहे', 'कसं हाय'),
    (r'चांगले', 'बरं'),
    (r'खूप', 'फार'),
    (r'आता', 'आता'),
    (r'मग', 'मंग'),
    
    # Pronouns
    (r'तुम्ही', 'तुमी'),
    (r'तुम्हाला', 'तुमास्नी'),
    (r'आम्हाला', 'आमास्नी'),
]

MARATHWADA_FILLERS = ['व्हय', 'बर का', 'मंग', 'अस्सं']

# ─── 5. KONKAN DIALECT (Coastal) ──────────────────────────────────────────────
KONKAN_RULES = [
    # Distinctive patterns
    (r'नाही', 'ना'),
    (r'आहे', 'आसा'),
    (r'होते', 'होतां'),
    (r'करत आहे', 'करता'),
    (r'वाटत नाही', 'दिसना'),
    (r'येत नाही', 'येना'),
    (r'समजत नाही', 'कळना'),
    
    # Verb forms
    (r'झाले', 'जालां'),
    (r'केले', 'केलां'),
    (r'गेले', 'गेलां'),
    (r'आले', 'आयलां'),
    (r'बोलले', 'बोल्लां'),
    
    # Unique Konkani-influenced words
    (r'काय', 'कितें'),
    (r'कसे', 'कशें'),
    (r'होय', 'व्हय'),
    (r'चांगले', 'बरें'),
    (r'आता', 'आतां'),
    
    # Pronouns
    (r'मी', 'हांव'),
    (r'तू', 'तूं'),
    (r'तुम्ही', 'तुमी'),
    (r'आम्ही', 'आमी'),
    (r'माझे', 'माजें'),
    (r'तुमचे', 'तुमचें'),
]

KONKAN_FILLERS = ['रे', 'गा', 'बाबा', 'अगो']

# ═══════════════════════════════════════════════════════════════════════════════
# DIALECT APPLICATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def apply_rules(text: str, rules: list) -> str:
    """Apply regex transformation rules to text."""
    result = text
    for pattern, replacement in rules:
        result = re.sub(pattern, replacement, result)
    return result

def add_filler(text: str, fillers: list, probability: float = 0.15) -> str:
    """Occasionally add regional fillers to make speech natural."""
    if len(text) < 15 or random.random() > probability:
        return text
    
    filler = random.choice(fillers)
    
    # Add at start, middle, or end
    pos = random.choice(['start', 'end'])
    if pos == 'start':
        return f"{filler}, {text}"
    else:
        return f"{text} {filler}"

def transform_to_dialect(text: str, dialect: str, role: str) -> str:
    """Transform formal Marathi text to specified dialect."""
    
    if dialect == 'standard_pune':
        # Keep formal, no changes
        return text
    
    elif dialect == 'mumbai':
        result = apply_rules(text, MUMBAI_RULES)
        if role == 'Patient':
            result = add_filler(result, MUMBAI_FILLERS, 0.12)
        return result
    
    elif dialect == 'vidarbha':
        result = apply_rules(text, VIDARBHA_RULES)
        if role == 'Patient':
            result = add_filler(result, VIDARBHA_FILLERS, 0.10)
        return result
    
    elif dialect == 'marathwada':
        result = apply_rules(text, MARATHWADA_RULES)
        if role == 'Patient':
            result = add_filler(result, MARATHWADA_FILLERS, 0.10)
        return result
    
    elif dialect == 'konkan':
        result = apply_rules(text, KONKAN_RULES)
        if role == 'Patient':
            result = add_filler(result, KONKAN_FILLERS, 0.10)
        return result
    
    return text

# ═══════════════════════════════════════════════════════════════════════════════
# FILE TRANSFORMATION
# ═══════════════════════════════════════════════════════════════════════════════

DIALECTS = ['standard_pune', 'mumbai', 'vidarbha', 'marathwada', 'konkan']

def transform_session(data: dict) -> dict:
    """
    Transform a translated session to simplified format with 5 dialects.
    
    Input: Current format with styles.formal_translated, etc.
    Output: New format with dialects.standard_pune, mumbai, vidarbha, etc.
    """
    
    # Get the formal translation as base
    formal_turns = data['styles']['formal_translated']
    
    # Build simplified output
    output = {
        'session_id': data['session_id'],
        'phq8_score': data.get('phq8_score'),
        'severity': data.get('severity'),
        'gender': 'female' if data.get('gender') == 0 else 'male',
        'split': data.get('split'),
        'total_turns': len(formal_turns),
        'dialects': {}
    }
    
    # Generate each dialect
    for dialect in DIALECTS:
        dialect_turns = []
        
        for turn in formal_turns:
            # Simplified turn - only essential fields
            simplified_turn = {
                'role': turn['role'],
                'text_en': turn['text_en'],
                'text': transform_to_dialect(turn['text'], dialect, turn['role'])
            }
            dialect_turns.append(simplified_turn)
        
        output['dialects'][dialect] = dialect_turns
    
    return output


def transform_all_files(input_dir: Path = TRANSLATED_DIR,
                        output_dir: Path = OUTPUT_DIR) -> int:
    """
    Transform all Marathi translated files to new format with 5 dialects.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    files = sorted(input_dir.glob("*_marathi.json"))
    
    if not files:
        print(f"No Marathi files found in {input_dir}")
        return 0
    
    print(f"\n{'═'*60}")
    print(f"  TRANSFORMING {len(files)} FILES")
    print(f"  Adding 5 dialects: {', '.join(DIALECTS)}")
    print(f"  Simplifying structure (removing turn_id, timestamps)")
    print(f"  Output: {output_dir}")
    print(f"{'═'*60}\n")
    
    processed = 0
    
    for f in tqdm(files, desc="Transforming", unit="file"):
        with open(f, encoding='utf-8') as fp:
            data = json.load(fp)
        
        # Transform to new format
        transformed = transform_session(data)
        
        # Save to output directory
        out_path = output_dir / f.name
        with open(out_path, 'w', encoding='utf-8') as fp:
            json.dump(transformed, fp, ensure_ascii=False, indent=2)
        
        processed += 1
    
    print(f"\n{'═'*60}")
    print(f"  ✅ Transformed {processed} files")
    print(f"  📁 Output: {output_dir}")
    print(f"{'═'*60}\n")
    
    return processed


def show_sample(session_id: int = 304):
    """Show a sample of all 5 dialects for comparison."""
    
    output_file = OUTPUT_DIR / f"{session_id}_marathi.json"
    
    if not output_file.exists():
        print(f"File not found: {output_file}")
        return
    
    with open(output_file, encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"\n{'═'*70}")
    print(f"  SESSION {session_id} - ALL 5 DIALECTS COMPARISON")
    print(f"  PHQ8: {data['phq8_score']} ({data['severity']}), Gender: {data['gender']}")
    print(f"{'═'*70}\n")
    
    # Find a meaningful turn
    for i, turn in enumerate(data['dialects']['standard_pune']):
        if turn['role'] == 'Patient' and len(turn['text']) > 30:
            print(f"Turn {i} (Patient):")
            print(f"  English: {turn['text_en'][:80]}...")
            print()
            
            for dialect in DIALECTS:
                text = data['dialects'][dialect][i]['text']
                print(f"  {dialect.upper():15} {text[:70]}...")
            print()
            
            if i > 20:
                break


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=None,
                        help="Show sample for session ID")
    parser.add_argument("--transform", action="store_true",
                        help="Transform all files")
    args = parser.parse_args()
    
    if args.transform:
        transform_all_files()
    
    if args.sample:
        show_sample(args.sample)
    
    if not args.transform and not args.sample:
        # Default: transform all
        transform_all_files()
