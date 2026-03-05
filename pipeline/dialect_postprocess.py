"""
pipeline/dialect_postprocess.py
================================
Post-processes translated Marathi files to make them sound more natural
and colloquial by applying:

1. Dialect conversion  - formal Marathi → spoken colloquial Marathi
2. Filler injection    - natural speech fillers (अरे, बघ, ना, हं)
3. Clinical slang      - real patient expressions for symptoms
4. Gender adjustment   - verb endings based on patient gender

Run after translation to improve the colloquial style layer.
"""

import json
import re
import random
from pathlib import Path
from tqdm import tqdm

TRANSLATED_DIR = Path("data/translated")

# ─── 1. DIALECT CONVERSION RULES ──────────────────────────────────────────────
# Converts formal/literary Marathi to spoken colloquial Marathi
# Based on Mumbai/Pune colloquial speech patterns

DIALECT_RULES = [
    # Verb endings - present tense
    (r'करत आहे', 'करतोय'),
    (r'करत आहेत', 'करतायत'),
    (r'करत आहेस', 'करतोयस'),
    (r'करत नाही', 'करत नाय'),
    (r'येत आहे', 'येतोय'),
    (r'जात आहे', 'जातोय'),
    (r'बसत आहे', 'बसतोय'),
    (r'बोलत आहे', 'बोलतोय'),
    (r'ऐकत आहे', 'ऐकतोय'),
    (r'पाहत आहे', 'पाहतोय'),
    (r'वाटत आहे', 'वाटतंय'),
    (r'होत आहे', 'होतंय'),
    (r'राहत आहे', 'राहतोय'),
    (r'खात आहे', 'खातोय'),
    (r'पीत आहे', 'पितोय'),
    (r'झोपत आहे', 'झोपतोय'),
    
    # Past tense contractions
    (r'झाले आहे', 'झालंय'),
    (r'झाले', 'झालं'),
    (r'केले', 'केलं'),
    (r'गेले', 'गेलं'),
    (r'आले', 'आलं'),
    (r'बोलले', 'बोललं'),
    (r'सांगितले', 'सांगितलं'),
    (r'दिले', 'दिलं'),
    (r'घेतले', 'घेतलं'),
    (r'पाहिले', 'पाहिलं'),
    (r'ऐकले', 'ऐकलं'),
    (r'खाल्ले', 'खाल्लं'),
    (r'बसले', 'बसलं'),
    (r'उठले', 'उठलं'),
    
    # Common word contractions
    (r'काय आहे', 'काय आहे'),  # keep as is, but can add 'काय हाय' variant
    (r'नाही आहे', 'नाहीये'),
    (r'आहे का', 'आहे का'),
    (r'होते', 'होतं'),
    (r'असते', 'असतं'),
    (r'म्हणजे', 'म्हंजे'),
    (r'कारण', 'कारण'),
    (r'परंतु', 'पण'),
    (r'आणि', 'आणि'),  # sometimes 'अन्'
    (r'तुम्हाला', 'तुम्हाला'),  # formal, colloquial would be 'तुला'
    (r'तुमचे', 'तुझं'),
    (r'तुमची', 'तुझी'),
    (r'तुमच्या', 'तुझ्या'),
    (r'माझे', 'माझं'),
    (r'माझी', 'माझी'),
    (r'त्याचे', 'त्याचं'),
    (r'त्याची', 'त्याची'),
    (r'तिचे', 'तिचं'),
    (r'आमचे', 'आमचं'),
    
    # Question forms
    (r'का\?', 'का?'),
    (r'कसे आहात', 'कसं आहेस'),
    (r'कसे आहे', 'कसं आहे'),
    
    # Honorific reduction (formal → casual)
    (r'आपण', 'तू'),
    (r'आपल्याला', 'तुला'),
    
    # Common expressions
    (r'चांगले आहे', 'बरं आहे'),
    (r'खूप चांगले', 'एकदम भारी'),
    (r'ठीक आहे', 'ठीके'),
    (r'बरोबर आहे', 'बरोबर'),
    (r'समजले', 'समजलं'),
    (r'कळले', 'कळलं'),
]

def apply_dialect(text: str) -> str:
    """Apply colloquial dialect rules to formal Marathi text."""
    result = text
    for pattern, replacement in DIALECT_RULES:
        result = re.sub(pattern, replacement, result)
    return result


# ─── 2. CONVERSATIONAL FILLERS ────────────────────────────────────────────────
# Natural speech fillers that patients use

PATIENT_FILLERS = [
    'बघा', 'बघ', 'अरे', 'हां', 'ना', 'म्हणजे', 'खरं तर', 
    'असं वाटतं', 'काय सांगू', 'माहित नाही पण'
]

DOCTOR_FILLERS = [
    'बरं', 'हो', 'ठीक', 'समजलं', 'अच्छा'
]

def inject_fillers(text: str, role: str, probability: float = 0.15) -> str:
    """Occasionally inject conversational fillers at sentence boundaries."""
    if len(text) < 20:  # Don't add fillers to very short utterances
        return text
    
    if random.random() > probability:
        return text
    
    fillers = PATIENT_FILLERS if role == "Patient" else DOCTOR_FILLERS
    filler = random.choice(fillers)
    
    # Add filler at start or after first clause
    if random.random() > 0.5:
        return f"{filler}, {text}"
    else:
        # Insert after first comma or period
        match = re.search(r'([,।.])', text)
        if match:
            pos = match.end()
            return f"{text[:pos]} {filler}, {text[pos:].strip()}"
        return text


# ─── 3. CLINICAL SLANG PHRASES ────────────────────────────────────────────────
# Replace formal clinical translations with real patient expressions

CLINICAL_SLANG = {
    # Depression/mood
    'उदास वाटत': 'मन लागत नाही',
    'उदासीनता': 'मन उदास',
    'निराश वाटत': 'काहीच बरं वाटत नाही',
    'निराशा': 'मन खिन्न',
    'दुःखी': 'वाईट वाटतं',
    'आनंद नाही': 'मजा नाही',
    'आनंद वाटत नाही': 'काहीच मजा नाही',
    
    # Anxiety
    'चिंता वाटते': 'टेन्शन येतं',
    'चिंताग्रस्त': 'टेन्शन मध्ये',
    'काळजी वाटते': 'काळजी वाटतेय',
    'भीती वाटते': 'भीती वाटतेय',
    'घाबरलेले': 'घाबरलोय',
    
    # Sleep
    'झोप येत नाही': 'झोप लागत नाही',
    'निद्रानाश': 'झोप उडालीय',
    'झोपेची समस्या': 'झोपेचं टेन्शन',
    'रात्री जागे': 'रात्री जागं राहतो',
    
    # Physical symptoms
    'थकवा': 'दमायला होतं',
    'थकलेले': 'दमलोय',
    'ऊर्जा नाही': 'एनर्जी नाही',
    'डोकेदुखी': 'डोकं दुखतंय',
    'छातीत दुखते': 'छातीत धडधड होते',
    
    # Appetite
    'भूक नाही': 'खाण्याची इच्छा नाही',
    'भूक कमी': 'भूक लागत नाही',
    'जास्त खातो': 'खूप खातो',
    
    # Concentration
    'लक्ष केंद्रित करू शकत नाही': 'लक्ष लागत नाही',
    'एकाग्रता नाही': 'डोकं चालत नाही',
    
    # General
    'बरे वाटत नाही': 'बरं वाटत नाहीये',
    'त्रास होतो': 'त्रास होतोय',
    'समस्या आहे': 'प्रॉब्लेम आहे',
}

def apply_clinical_slang(text: str) -> str:
    """Replace formal clinical terms with colloquial patient expressions."""
    result = text
    for formal, slang in CLINICAL_SLANG.items():
        result = re.sub(re.escape(formal), slang, result, flags=re.IGNORECASE)
    return result


# ─── 4. GENDER-AWARE ADJUSTMENTS ──────────────────────────────────────────────
# Marathi verbs change based on speaker gender

GENDER_RULES_MALE = [
    (r'मी गेले', 'मी गेलो'),
    (r'मी आले', 'मी आलो'),
    (r'मी केले', 'मी केलं'),
    (r'मी बोलले', 'मी बोललो'),
    (r'मी पाहिले', 'मी पाहिलं'),
    (r'मी ऐकले', 'मी ऐकलं'),
    (r'मला वाटले', 'मला वाटलं'),
    (r'मी थकले', 'मी थकलो'),
    (r'मी झोपले', 'मी झोपलो'),
    (r'मी उठले', 'मी उठलो'),
    (r'मी खाल्ले', 'मी खाल्लं'),
    (r'मी बसले', 'मी बसलो'),
]

GENDER_RULES_FEMALE = [
    (r'मी गेलो', 'मी गेले'),
    (r'मी आलो', 'मी आले'),
    (r'मी बोललो', 'मी बोलले'),
    (r'मी थकलो', 'मी थकले'),
    (r'मी झोपलो', 'मी झोपले'),
    (r'मी उठलो', 'मी उठले'),
    (r'मी बसलो', 'मी बसले'),
]

def apply_gender(text: str, gender: int) -> str:
    """
    Adjust verb endings based on gender.
    gender: 0 = female, 1 = male (DAIC-WOZ convention)
    """
    rules = GENDER_RULES_MALE if gender == 1 else GENDER_RULES_FEMALE
    result = text
    for pattern, replacement in rules:
        result = re.sub(pattern, replacement, result)
    return result


# ─── MAIN POST-PROCESSOR ──────────────────────────────────────────────────────

def postprocess_session(data: dict) -> dict:
    """
    Apply all post-processing to a translated session.
    Only modifies the 'colloquial' style — formal and code_mixed stay as-is.
    """
    gender = data.get('gender', 1)  # default to male if not specified
    
    colloquial_turns = data['styles']['colloquial']
    
    for turn in colloquial_turns:
        text = turn['text']
        role = turn['role']
        
        # Apply all transformations
        text = apply_dialect(text)
        text = apply_clinical_slang(text)
        
        # Gender adjustment only for patient speech
        if role == 'Patient':
            text = apply_gender(text, gender)
            text = inject_fillers(text, role, probability=0.1)
        
        turn['text'] = text
    
    data['styles']['colloquial'] = colloquial_turns
    return data


def postprocess_all(translated_dir: Path = TRANSLATED_DIR, 
                    language: str = "marathi") -> int:
    """
    Post-process all translated files for the given language.
    Returns number of files processed.
    """
    pattern = f"*_{language}.json"
    files = sorted(translated_dir.glob(pattern))
    
    if not files:
        print(f"No {language} files found in {translated_dir}")
        return 0
    
    print(f"\n{'─'*60}")
    print(f"  Post-processing {len(files)} {language} files...")
    print(f"  Applying: dialect conversion, clinical slang, gender adjustment")
    print(f"{'─'*60}\n")
    
    processed = 0
    for f in tqdm(files, desc="Processing", unit="file"):
        with open(f, encoding='utf-8') as fp:
            data = json.load(fp)
        
        data = postprocess_session(data)
        
        with open(f, 'w', encoding='utf-8') as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        
        processed += 1
    
    print(f"\n✅ Post-processed {processed} files")
    return processed


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", default="marathi", choices=["marathi", "hindi"])
    args = parser.parse_args()
    
    postprocess_all(language=args.lang)
