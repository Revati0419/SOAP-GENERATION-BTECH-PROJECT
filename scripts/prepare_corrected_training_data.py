#!/usr/bin/env python3
"""
Convert Gemini-corrected SOAP notes into training data
Prepares improved training examples from human-validated corrections
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List
from datetime import datetime


def load_original_soap_note(session_id: int, soap_dir: str) -> Dict:
    """Load original SOAP note file"""
    soap_path = Path(soap_dir)
    
    # Find file matching session ID
    matches = list(soap_path.glob(f"soap_{session_id}_*_v3.json"))
    
    if not matches:
        raise FileNotFoundError(f"No SOAP note found for session {session_id}")
    
    with open(matches[0], 'r', encoding='utf-8') as f:
        return json.load(f)


def load_conversation(session_id: int, dialect: str) -> str:
    """Load conversation from dialect file"""
    
    # Try multiple patterns
    patterns = [
        f"data/dialect_{dialect}/{session_id}_{dialect}.json",
        f"data/dialect_marathi/{session_id}_marathi.json",
        f"data/dialect_standard_pune/{session_id}_standard_pune.json",
    ]
    
    for pattern in patterns:
        path = Path(pattern)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Extract conversation
                if isinstance(data, list):
                    lines = [f"{item['speaker']}: {item['text']}" for item in data]
                elif isinstance(data, dict) and 'conversation' in data:
                    lines = [f"{item['speaker']}: {item['text']}" for item in data['conversation']]
                else:
                    lines = [str(data)]
                
                return "\n".join(lines)
    
    return f"[Conversation for session {session_id} not found]"


def create_corrected_training_example(review: Dict, soap_dir: str) -> Dict:
    """Create training example using corrected SOAP note"""
    
    session_id = review.get("session_id")
    
    # Load original SOAP note for context
    original_soap = load_original_soap_note(session_id, soap_dir)
    dialect = original_soap.get("dialect", "standard_pune")
    
    # Load conversation
    conversation = load_conversation(session_id, dialect)
    
    # Get corrected SOAP (or original if no corrections)
    if review.get("needs_correction", False):
        soap_marathi = review.get("corrected_soap_marathi", {})
        quality_note = f" (Gemini-corrected: {len(review.get('issues', []))} issues fixed)"
    else:
        soap_marathi = original_soap.get("soap_marathi", {})
        quality_note = " (Gemini-validated: no issues)"
    
    # Get entities and PHQ-8 info
    entities = original_soap.get("entities", {})
    phq8_score = original_soap.get("phq8_score", 0)
    severity = original_soap.get("severity", "minimal")
    
    # Format entities for prompt
    entity_text = ""
    if entities:
        entity_lines = []
        for entity_type, entity_list in entities.items():
            if entity_list:
                entity_lines.append(f"- {entity_type}: {', '.join(entity_list)}")
        if entity_lines:
            entity_text = "\n" + "\n".join(entity_lines)
    
    # Create prompt
    prompt = f"""Generate a SOAP note in Marathi for this therapy session.

**Conversation:**
{conversation}

**Extracted Entities:**{entity_text if entity_text else " None"}

**PHQ-8 Score:** {phq8_score} ({severity} depression)

Generate a professional SOAP note in Marathi:"""
    
    # Create response (corrected SOAP in structured format)
    response = f"""**Subjective (विषयनिष्ठ):**
{soap_marathi.get('subjective', 'N/A')}

**Objective (वस्तुनिष्ठ):**
{soap_marathi.get('objective', 'N/A')}

**Assessment (मूल्यांकन):**
{soap_marathi.get('assessment', 'N/A')}

**Plan (योजना):**
{soap_marathi.get('plan', 'N/A')}"""
    
    return {
        "session_id": session_id,
        "prompt": prompt,
        "response": response,
        "quality": review.get("overall_quality", "unknown"),
        "corrected": review.get("needs_correction", False),
        "num_issues_fixed": len(review.get("issues", [])),
        "quality_note": quality_note.strip()
    }


def prepare_corrected_training_data(
    reviews_file: str,
    soap_dir: str,
    output_dir: str,
    train_split: float = 0.8,
    only_corrected: bool = False
):
    """Prepare training data from Gemini-reviewed SOAP notes"""
    
    print("\n" + "="*70)
    print("         PREPARE CORRECTED TRAINING DATA")
    print("="*70)
    
    # Load reviews
    print(f"\n📂 Loading reviews from: {reviews_file}")
    with open(reviews_file, 'r', encoding='utf-8') as f:
        reviews = json.load(f)
    
    print(f"   Found {len(reviews)} reviews")
    
    # Filter if only_corrected
    if only_corrected:
        reviews = [r for r in reviews if r.get("needs_correction", False)]
        print(f"   Filtering to {len(reviews)} corrected notes only")
    
    # Create training examples
    print(f"\n🔄 Creating training examples...")
    training_examples = []
    failed = 0
    
    for i, review in enumerate(reviews, 1):
        session_id = review.get("session_id")
        print(f"  [{i}/{len(reviews)}] Processing session {session_id}...", end=" ")
        
        try:
            example = create_corrected_training_example(review, soap_dir)
            training_examples.append(example)
            print(f"✅ {example['quality_note']}")
        except Exception as e:
            print(f"❌ Failed: {e}")
            failed += 1
    
    if not training_examples:
        print(f"\n❌ No training examples created!")
        return
    
    print(f"\n✅ Created {len(training_examples)} training examples ({failed} failed)")
    
    # Split into train and validation
    num_train = max(1, int(len(training_examples) * train_split))
    train_examples = training_examples[:num_train]
    val_examples = training_examples[num_train:]
    
    # Handle edge case: if only 1 example, use it for both
    if len(training_examples) == 1:
        train_examples = training_examples
        val_examples = training_examples
    
    print(f"\n📊 Split: {len(train_examples)} train, {len(val_examples)} validation")
    
    # Save training data
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    train_file = output_path / "train_corrected.jsonl"
    val_file = output_path / "val_corrected.jsonl"
    
    # Write JSONL files
    with open(train_file, 'w', encoding='utf-8') as f:
        for example in train_examples:
            # Keep only prompt and response for training
            training_item = {
                "prompt": example["prompt"],
                "response": example["response"]
            }
            f.write(json.dumps(training_item, ensure_ascii=False) + "\n")
    
    with open(val_file, 'w', encoding='utf-8') as f:
        for example in val_examples:
            training_item = {
                "prompt": example["prompt"],
                "response": example["response"]
            }
            f.write(json.dumps(training_item, ensure_ascii=False) + "\n")
    
    # Save metadata
    metadata = {
        "created_at": datetime.now().isoformat(),
        "total_examples": len(training_examples),
        "train_examples": len(train_examples),
        "val_examples": len(val_examples),
        "train_split": train_split,
        "only_corrected": only_corrected,
        "reviews_source": reviews_file,
        "quality_distribution": {},
        "correction_stats": {
            "corrected": sum(1 for e in training_examples if e["corrected"]),
            "validated": sum(1 for e in training_examples if not e["corrected"]),
            "total_issues_fixed": sum(e["num_issues_fixed"] for e in training_examples)
        }
    }
    
    # Count quality distribution
    for example in training_examples:
        quality = example["quality"]
        metadata["quality_distribution"][quality] = \
            metadata["quality_distribution"].get(quality, 0) + 1
    
    metadata_file = output_path / "metadata_corrected.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved training data:")
    print(f"   • Train: {train_file} ({len(train_examples)} examples)")
    print(f"   • Val: {val_file} ({len(val_examples)} examples)")
    print(f"   • Metadata: {metadata_file}")
    
    print(f"\n📈 QUALITY STATS:")
    print(f"   Corrected: {metadata['correction_stats']['corrected']}")
    print(f"   Validated (no issues): {metadata['correction_stats']['validated']}")
    print(f"   Total issues fixed: {metadata['correction_stats']['total_issues_fixed']}")
    
    print(f"\n   Quality distribution:")
    for quality, count in metadata["quality_distribution"].items():
        pct = count / len(training_examples) * 100
        print(f"     {quality}: {count} ({pct:.1f}%)")
    
    print(f"\n✅ Ready to train with corrected data!")
    print(f"\n   Run:")
    print(f"   python scripts/qlora_train.py \\")
    print(f"     --train_file {train_file} \\")
    print(f"     --validation_file {val_file} \\")
    print(f"     --output_dir outputs/qlora_v1_corrected \\")
    print(f"     --do_train")


def main():
    parser = argparse.ArgumentParser(
        description="Prepare training data from Gemini-corrected SOAP notes"
    )
    parser.add_argument(
        "--reviews_file",
        type=str,
        default="data/gemini_reviews/reviews.json",
        help="JSON file with Gemini reviews (default: data/gemini_reviews/reviews.json)"
    )
    parser.add_argument(
        "--soap_dir",
        type=str,
        default="data/soap_notes",
        help="Directory containing original SOAP notes (default: data/soap_notes)"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="data/training",
        help="Output directory for training data (default: data/training)"
    )
    parser.add_argument(
        "--train_split",
        type=float,
        default=0.8,
        help="Train/validation split ratio (default: 0.8)"
    )
    parser.add_argument(
        "--only_corrected",
        action="store_true",
        help="Only use corrected notes (exclude validated ones with no issues)"
    )
    
    args = parser.parse_args()
    
    prepare_corrected_training_data(
        reviews_file=args.reviews_file,
        soap_dir=args.soap_dir,
        output_dir=args.output_dir,
        train_split=args.train_split,
        only_corrected=args.only_corrected
    )


if __name__ == "__main__":
    main()
