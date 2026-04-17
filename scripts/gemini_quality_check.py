#!/usr/bin/env python3
"""
Gemini Quality Check for SOAP Notes
Sends SOAP notes to Gemini for Marathi quality validation and corrections
"""

import os
import sys
import json
import google.generativeai as genai
from pathlib import Path
from typing import Dict, List, Optional
import argparse

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDKBfRPY8lhyG5zE_8s7j-rJ5Dl0QKXE_Y")
genai.configure(api_key=GEMINI_API_KEY)


def create_review_prompt(soap_note: Dict) -> str:
    """Create prompt for Gemini to review SOAP note Marathi quality"""
    
    session_id = soap_note.get("session_id", "Unknown")
    soap_english = soap_note.get("soap_english", {})
    soap_marathi = soap_note.get("soap_marathi", {})
    
    prompt = f"""You are an expert Marathi medical translator and clinical documentation specialist.

Review the following SOAP note translation from English to Marathi for a therapy session.

**Session ID**: {session_id}

**ENGLISH VERSION:**
Subjective: {soap_english.get('subjective', 'N/A')}
Objective: {soap_english.get('objective', 'N/A')}
Assessment: {soap_english.get('assessment', 'N/A')}
Plan: {soap_english.get('plan', 'N/A')}

**MARATHI TRANSLATION:**
Subjective: {soap_marathi.get('subjective', 'N/A')}
Objective: {soap_marathi.get('objective', 'N/A')}
Assessment: {soap_marathi.get('assessment', 'N/A')}
Plan: {soap_marathi.get('plan', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**YOUR TASK:**

1. **Check Translation Accuracy**: Does the Marathi version correctly convey the English meaning?
2. **Grammar & Fluency**: Is the Marathi grammatically correct and natural?
3. **Medical Terminology**: Are medical terms translated appropriately (or kept in English when standard)?
4. **Cultural Appropriateness**: Is the language suitable for a clinical context in Maharashtra?

**PROVIDE OUTPUT IN THIS JSON FORMAT:**

{{
  "session_id": "{session_id}",
  "overall_quality": "excellent|good|fair|poor",
  "needs_correction": true/false,
  "issues": [
    {{
      "section": "subjective|objective|assessment|plan",
      "issue_type": "translation|grammar|terminology|style",
      "original": "the problematic Marathi text",
      "correction": "the corrected Marathi text",
      "explanation": "brief explanation of why correction is needed"
    }}
  ],
  "corrected_soap_marathi": {{
    "subjective": "corrected Marathi text (or original if no issues)",
    "objective": "corrected Marathi text (or original if no issues)",
    "assessment": "corrected Marathi text (or original if no issues)",
    "plan": "corrected Marathi text (or original if no issues)"
  }},
  "reviewer_notes": "any additional comments or suggestions"
}}

**IMPORTANT**: 
- If translation is perfect, set needs_correction=false and issues=[]
- Keep corrected_soap_marathi even if no changes (copy original)
- Be specific about issues - include exact text that needs correction
"""
    
    return prompt


def review_with_gemini(soap_note: Dict, model_name: str = "gemini-2.0-flash-exp") -> Optional[Dict]:
    """Send SOAP note to Gemini for review"""
    
    try:
        model = genai.GenerativeModel(model_name)
        prompt = create_review_prompt(soap_note)
        
        print(f"  📤 Sending to Gemini for review...")
        
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,  # Low temperature for consistent reviews
                "max_output_tokens": 2048,
            }
        )
        
        # Extract JSON from response
        response_text = response.text.strip()
        
        # Try to extract JSON (handle markdown code blocks)
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        review_result = json.loads(response_text)
        return review_result
        
    except json.JSONDecodeError as e:
        print(f"  ❌ Failed to parse Gemini response as JSON: {e}")
        print(f"  Raw response: {response_text[:200]}...")
        return None
    except Exception as e:
        print(f"  ❌ Error during Gemini review: {e}")
        return None


def process_soap_notes(
    soap_dir: str,
    output_file: str,
    session_ids: Optional[List[int]] = None,
    max_reviews: int = None
):
    """Process SOAP notes and collect Gemini reviews"""
    
    soap_path = Path(soap_dir)
    reviews = []
    
    # Get all SOAP note files
    soap_files = sorted(soap_path.glob("soap_*_v3.json"))
    
    # Filter by session IDs if provided
    if session_ids:
        soap_files = [
            f for f in soap_files 
            if any(f"soap_{sid}_" in f.name for sid in session_ids)
        ]
    
    # Limit number of reviews
    if max_reviews:
        soap_files = soap_files[:max_reviews]
    
    print(f"\n📊 Found {len(soap_files)} SOAP notes to review\n")
    
    for i, soap_file in enumerate(soap_files, 1):
        print(f"[{i}/{len(soap_files)}] Reviewing {soap_file.name}")
        
        try:
            # Load SOAP note
            with open(soap_file, 'r', encoding='utf-8') as f:
                soap_note = json.load(f)
            
            # Get Gemini review
            review = review_with_gemini(soap_note)
            
            if review:
                reviews.append(review)
                
                # Display summary
                quality = review.get("overall_quality", "unknown")
                needs_correction = review.get("needs_correction", False)
                num_issues = len(review.get("issues", []))
                
                status = "✅" if not needs_correction else "⚠️"
                print(f"  {status} Quality: {quality} | Issues: {num_issues}")
                
                if needs_correction:
                    for issue in review.get("issues", []):
                        print(f"    • {issue['section']}: {issue['issue_type']}")
            else:
                print(f"  ❌ Review failed, skipping...")
            
            print()
            
        except Exception as e:
            print(f"  ❌ Error processing {soap_file.name}: {e}\n")
            continue
    
    # Save reviews
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Saved {len(reviews)} reviews to: {output_file}")
    
    # Print summary statistics
    needs_correction = sum(1 for r in reviews if r.get("needs_correction", False))
    total_issues = sum(len(r.get("issues", [])) for r in reviews)
    
    print(f"\n📈 SUMMARY:")
    print(f"   Total reviewed: {len(reviews)}")
    print(f"   Needs correction: {needs_correction} ({needs_correction/len(reviews)*100:.1f}%)")
    print(f"   Total issues found: {total_issues}")
    print(f"   Average issues per note: {total_issues/len(reviews):.1f}")
    
    # Quality distribution
    quality_dist = {}
    for r in reviews:
        q = r.get("overall_quality", "unknown")
        quality_dist[q] = quality_dist.get(q, 0) + 1
    
    print(f"\n   Quality Distribution:")
    for quality, count in sorted(quality_dist.items()):
        print(f"     {quality}: {count} ({count/len(reviews)*100:.1f}%)")


def main():
    parser = argparse.ArgumentParser(
        description="Send SOAP notes to Gemini for quality review and corrections"
    )
    parser.add_argument(
        "--soap_dir",
        type=str,
        default="data/soap_notes",
        help="Directory containing SOAP notes (default: data/soap_notes)"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="data/gemini_reviews/reviews.json",
        help="Output file for reviews (default: data/gemini_reviews/reviews.json)"
    )
    parser.add_argument(
        "--sessions",
        type=str,
        help="Comma-separated session IDs to review (e.g., '300,301,302')"
    )
    parser.add_argument(
        "--max_reviews",
        type=int,
        help="Maximum number of SOAP notes to review"
    )
    
    args = parser.parse_args()
    
    # Parse session IDs
    session_ids = None
    if args.sessions:
        session_ids = [int(sid.strip()) for sid in args.sessions.split(',')]
    
    print("\n" + "="*70)
    print("         GEMINI QUALITY CHECK - SOAP NOTES")
    print("="*70)
    
    process_soap_notes(
        soap_dir=args.soap_dir,
        output_file=args.output_file,
        session_ids=session_ids,
        max_reviews=args.max_reviews
    )
    
    print("\n✅ Quality check complete!")
    print(f"\nNext steps:")
    print(f"  1. Review the corrections in: {args.output_file}")
    print(f"  2. Run: python scripts/prepare_corrected_training_data.py")
    print(f"  3. Retrain with corrected data for improved model!")


if __name__ == "__main__":
    main()
