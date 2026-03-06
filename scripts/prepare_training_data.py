#!/usr/bin/env python3
"""
prepare_training_data.py
-------------------------
Convert generated SOAP notes to JSONL format for QLoRA training.

Input: data/soap_notes/*.md (bilingual SOAP notes)
Output: 
  - data/training/train.jsonl (80% of data)
  - data/training/val.jsonl (20% for validation)

Format: Each line is a JSON object with 'prompt' and 'response' fields.

Example:
{
  "prompt": "Generate a clinical SOAP note from this conversation:\n[CONVERSATION]",
  "response": "## SUBJECTIVE\n[Patient reported symptoms...]\n..."
}

Usage:
  python scripts/prepare_training_data.py \
    --soap_dir data/soap_notes \
    --output_dir data/training \
    --train_split 0.8
"""

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_soap_note(filepath: Path) -> Dict:
    """
    Parse a bilingual SOAP note JSON file (v3 format).
    
    Extracts:
      - session_id
      - dialect
      - phq8_score
      - English SOAP sections
      - Marathi SOAP sections
      - conversation (if available)
    """
    try:
        # Load JSON file
        data = json.loads(filepath.read_text(encoding='utf-8'))
        
        session_id = str(data.get('session_id', ''))
        dialect = data.get('dialect', 'unknown')
        phq8 = int(data.get('phq8_score', 0))
        
        # Get SOAP notes
        english_soap = data.get('soap_english', '')
        marathi_soap = data.get('soap_marathi', '')
        
        # Load conversation from dialect file
        conversation = load_conversation(session_id, dialect)
        
        return {
            'session_id': session_id,
            'dialect': dialect,
            'phq8': phq8,
            'conversation': conversation,
            'english_soap': english_soap,
            'marathi_soap': marathi_soap,
            'filepath': str(filepath)
        }
    
    except Exception as e:
        logger.error(f"Failed to parse {filepath}: {e}")
        return None


def load_conversation(session_id: str, dialect: str) -> str:
    """Load conversation from dialect file."""
    try:
        # Try different filename patterns
        possible_files = [
            Path(f'data/dialect_marathi/{session_id}_marathi.json'),
            Path(f'data/dialect_marathi/{session_id}_{dialect}.json'),
            Path(f'data/translated/{session_id}_marathi.json'),
        ]
        
        dialect_file = None
        for f in possible_files:
            if f.exists():
                dialect_file = f
                break
        
        if not dialect_file:
            logger.debug(f"No conversation file found for session {session_id}")
            return ""
        
        data = json.loads(dialect_file.read_text(encoding='utf-8'))
        
        # Check if it's the new dialect format
        if 'dialects' in data and dialect in data['dialects']:
            turns = data['dialects'][dialect]
            conversation_turns = []
            for turn in turns:
                role = turn.get('role', 'Unknown')
                text_en = turn.get('text_en', '')
                conversation_turns.append(f"{role}: {text_en}")
            return "\n".join(conversation_turns)
        
        # Fallback: old format with 'turns' key
        if 'turns' in data:
            turns = []
            for turn in data['turns']:
                speaker = turn.get('speaker', 'Unknown')
                text = turn.get('value', '')
                turns.append(f"{speaker}: {text}")
            return "\n".join(turns)
        
        logger.debug(f"Unknown format in {dialect_file}")
        return ""
    
    except Exception as e:
        logger.warning(f"Could not load conversation for {session_id}: {e}")
        return ""


def create_training_example(parsed: Dict) -> Dict:
    """
    Create a training example in prompt/response format.
    
    Prompt: Conversation + task instruction
    Response: English SOAP note (we'll generate Marathi via translation model)
    """
    if not parsed or not parsed['conversation'] or not parsed['english_soap']:
        return None
    
    # Build prompt
    prompt = f"""You are a clinical psychologist. Generate a comprehensive SOAP note from this mental health interview conversation.

SOAP Format:
- SUBJECTIVE: Patient's reported symptoms, feelings, and concerns
- OBJECTIVE: Clinician's observations of appearance, behavior, mood, affect
- ASSESSMENT: Clinical diagnosis, PHQ-8 score, risk assessment
- PLAN: Treatment recommendations, medications, follow-up, safety planning

Conversation:
{parsed['conversation']}

PHQ-8 Score: {parsed['phq8']}

Generate the SOAP note:"""
    
    # Response is the English SOAP note
    response = parsed['english_soap']
    
    return {
        'prompt': prompt.strip(),
        'response': response.strip(),
        'metadata': {
            'session_id': parsed['session_id'],
            'dialect': parsed['dialect'],
            'phq8': parsed['phq8']
        }
    }


def prepare_training_data(
    soap_dir: Path,
    output_dir: Path,
    train_split: float = 0.8,
    min_quality: bool = True
) -> Tuple[int, int]:
    """
    Convert all SOAP notes to training JSONL files.
    
    Returns: (num_train, num_val)
    """
    soap_dir = Path(soap_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all SOAP note files (v3 format is JSON)
    soap_files = list(soap_dir.glob('soap_*_v3.json'))
    logger.info(f"Found {len(soap_files)} SOAP note files (v3 JSON format)")
    
    if not soap_files:
        logger.error(f"No SOAP note files found in {soap_dir}")
        return 0, 0
    
    # Parse all SOAP notes
    examples = []
    for soap_file in soap_files:
        parsed = parse_soap_note(soap_file)
        if parsed:
            example = create_training_example(parsed)
            if example:
                # Quality filter
                if min_quality:
                    # Check minimum length
                    if len(example['prompt']) < 200 or len(example['response']) < 500:
                        logger.debug(f"Skipping {soap_file.name}: too short")
                        continue
                    
                    # Check has all SOAP sections
                    if not all(section in example['response'].upper() 
                              for section in ['SUBJECTIVE', 'OBJECTIVE', 'ASSESSMENT', 'PLAN']):
                        logger.debug(f"Skipping {soap_file.name}: missing sections")
                        continue
                
                examples.append(example)
    
    logger.info(f"Created {len(examples)} training examples")
    
    if not examples:
        logger.error("No valid training examples created")
        return 0, 0
    
    # For small datasets (< 10 examples), put all in training, create minimal validation
    if len(examples) < 10:
        logger.warning(f"Small dataset ({len(examples)} examples) - using all for training, duplicating 1 for validation")
        train_examples = examples
        val_examples = examples[:1]  # Duplicate first example for validation
    else:
        # Shuffle and split for larger datasets
        random.seed(42)
        random.shuffle(examples)
        
        split_idx = int(len(examples) * train_split)
        train_examples = examples[:split_idx]
        val_examples = examples[split_idx:]
    
    # Write JSONL files
    train_file = output_dir / 'train.jsonl'
    val_file = output_dir / 'val.jsonl'
    
    with open(train_file, 'w', encoding='utf-8') as f:
        for ex in train_examples:
            # Remove metadata for training (keep only prompt/response)
            training_ex = {'prompt': ex['prompt'], 'response': ex['response']}
            f.write(json.dumps(training_ex, ensure_ascii=False) + '\n')
    
    with open(val_file, 'w', encoding='utf-8') as f:
        for ex in val_examples:
            training_ex = {'prompt': ex['prompt'], 'response': ex['response']}
            f.write(json.dumps(training_ex, ensure_ascii=False) + '\n')
    
    logger.info(f"✅ Training data prepared:")
    logger.info(f"   - Train: {len(train_examples)} examples → {train_file}")
    logger.info(f"   - Val:   {len(val_examples)} examples → {val_file}")
    
    # Save metadata separately
    metadata_file = output_dir / 'metadata.json'
    metadata = {
        'total_examples': len(examples),
        'train_examples': len(train_examples),
        'val_examples': len(val_examples),
        'train_split': train_split,
        'source_files': [str(f) for f in soap_files[:10]],  # Sample
        'quality_filter': min_quality
    }
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    logger.info(f"   - Metadata: {metadata_file}")
    
    return len(train_examples), len(val_examples)


def main():
    parser = argparse.ArgumentParser(description='Prepare SOAP notes for QLoRA training')
    parser.add_argument('--soap_dir', type=Path, default=Path('data/soap_notes'),
                       help='Directory containing generated SOAP notes')
    parser.add_argument('--output_dir', type=Path, default=Path('data/training'),
                       help='Output directory for training JSONL files')
    parser.add_argument('--train_split', type=float, default=0.8,
                       help='Train/validation split ratio (default: 0.8)')
    parser.add_argument('--no_quality_filter', action='store_true',
                       help='Disable quality filtering (include all examples)')
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("SOAP Note Training Data Preparation")
    logger.info("=" * 60)
    
    num_train, num_val = prepare_training_data(
        soap_dir=args.soap_dir,
        output_dir=args.output_dir,
        train_split=args.train_split,
        min_quality=not args.no_quality_filter
    )
    
    if num_train > 0:
        logger.info(f"\n✅ Success! Ready for QLoRA training.")
        logger.info(f"\nNext steps:")
        logger.info(f"1. Test setup (dry-run):")
        logger.info(f"   python scripts/qlora_train.py \\")
        logger.info(f"     --model_name_or_path google/gemma-2b \\")
        logger.info(f"     --train_file {args.output_dir}/train.jsonl \\")
        logger.info(f"     --validation_file {args.output_dir}/val.jsonl \\")
        logger.info(f"     --output_dir outputs/qlora_test")
        logger.info(f"\n2. Full training:")
        logger.info(f"   python scripts/qlora_train.py \\")
        logger.info(f"     --model_name_or_path google/gemma-2b \\")
        logger.info(f"     --train_file {args.output_dir}/train.jsonl \\")
        logger.info(f"     --validation_file {args.output_dir}/val.jsonl \\")
        logger.info(f"     --output_dir outputs/qlora_v1 \\")
        logger.info(f"     --num_train_epochs 3 \\")
        logger.info(f"     --do_train")
    else:
        logger.error("❌ No training data created. Check SOAP notes directory.")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
