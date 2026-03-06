"""
Manual Review Interface for SOAP Notes
---------------------------------------
Easy-to-use interface for reviewing sampled SOAP notes
"""

import json
from pathlib import Path

class SOAPReviewer:
    def __init__(self, soap_dir='data/soap_notes'):
        self.soap_dir = Path(soap_dir)
        self.review_log = []
    
    def load_review_list(self):
        """Load the generated review list"""
        review_file = self.soap_dir / 'review_list.json'
        if not review_file.exists():
            print("❌ No review list found. Run validate_soap_notes.py first!")
            return None
        
        with open(review_file, 'r') as f:
            return json.load(f)
    
    def display_soap(self, session_id):
        """Display a SOAP note in readable format"""
        soap_file = self.soap_dir / f'{session_id}_soap.json'
        
        if not soap_file.exists():
            print(f"❌ SOAP note for session {session_id} not found!")
            return None
        
        with open(soap_file, 'r', encoding='utf-8') as f:
            soap = json.load(f)
        
        print("\n" + "=" * 80)
        print(f"SESSION {session_id} | PHQ-8: {soap['phq8_score']}/24 | {soap['severity']}")
        print("=" * 80)
        
        # Show original conversation snippet
        transcript_file = Path('data/dialect_marathi') / f'{session_id}_standard_pune_marathi.json'
        if transcript_file.exists():
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcript = json.load(f)
            
            print("\n📝 ORIGINAL CONVERSATION (First 5 exchanges):")
            print("-" * 80)
            for i, turn in enumerate(transcript['transcript'][:10], 1):  # First 10 turns = ~5 exchanges
                speaker = "🩺 Clinician" if turn['speaker'] == 'Ellie' else "👤 Patient"
                text = turn['value'][:100] + "..." if len(turn['value']) > 100 else turn['value']
                print(f"{speaker}: {text}")
            print()
        
        # Show English SOAP
        print("\n🇬🇧 ENGLISH SOAP NOTE:")
        print("-" * 80)
        for section in ['subjective', 'objective', 'assessment', 'plan']:
            content = soap['soap_english'].get(section, 'N/A')
            print(f"\n📋 {section.upper()}:")
            print(content)
        
        # Show Marathi SOAP
        print("\n\n🇮🇳 मराठी SOAP NOTE:")
        print("-" * 80)
        sections_marathi = {
            'subjective': 'विषय',
            'objective': 'उद्देश', 
            'assessment': 'मूल्यांकन',
            'plan': 'योजना'
        }
        for eng_section, mr_section in sections_marathi.items():
            content = soap['soap_marathi'].get(eng_section, 'N/A')
            print(f"\n📋 {mr_section} ({eng_section.upper()}):")
            print(content)
        
        return soap
    
    def review_session(self, session_id):
        """Interactive review for one session"""
        soap = self.display_soap(session_id)
        if not soap:
            return
        
        print("\n\n" + "=" * 80)
        print("REVIEW CHECKLIST:")
        print("=" * 80)
        
        questions = [
            ("English completeness (all 4 sections present?)", ['y', 'n']),
            ("English language quality (grammar, coherence?)", ['good', 'ok', 'poor']),
            ("English clinical accuracy (matches conversation?)", ['y', 'n', 'partial']),
            ("Marathi translation quality (natural, readable?)", ['good', 'ok', 'poor']),
            ("Marathi completeness (all 4 sections present?)", ['y', 'n']),
            ("Overall SOAP quality", ['excellent', 'good', 'acceptable', 'poor']),
        ]
        
        responses = {}
        print("\nPlease review and answer (or type 'skip' to skip):\n")
        
        for i, (question, options) in enumerate(questions, 1):
            while True:
                response = input(f"{i}. {question} [{'/'.join(options)}]: ").strip().lower()
                if response == 'skip':
                    return 'skipped'
                if response in options:
                    responses[question] = response
                    break
                print(f"   Invalid input. Please enter one of: {', '.join(options)}")
        
        # Optional comments
        comments = input("\nAdditional comments (optional): ").strip()
        if comments:
            responses['comments'] = comments
        
        # Flag for issues
        has_issues = (
            responses.get("English completeness (all 4 sections present?)") == 'n' or
            responses.get("English clinical accuracy (matches conversation?)") in ['n', 'partial'] or
            responses.get("Overall SOAP quality") in ['poor']
        )
        
        review = {
            'session_id': session_id,
            'phq8_score': soap['phq8_score'],
            'severity': soap['severity'],
            'responses': responses,
            'flagged': has_issues
        }
        
        self.review_log.append(review)
        
        if has_issues:
            print("\n⚠️  This session has been FLAGGED for issues")
        else:
            print("\n✅ Review recorded")
        
        return review
    
    def batch_review(self, session_ids):
        """Review multiple sessions"""
        print("\n" + "=" * 80)
        print(f"BATCH REVIEW: {len(session_ids)} sessions")
        print("=" * 80)
        print("Commands: [n]ext, [s]kip, [q]uit, [b]ack\n")
        
        i = 0
        while i < len(session_ids):
            session_id = session_ids[i]
            
            result = self.review_session(session_id)
            
            print(f"\n\nProgress: {i+1}/{len(session_ids)}")
            command = input("Command [n/s/q/b]: ").strip().lower()
            
            if command in ['n', '']:
                i += 1
            elif command == 's':
                i += 1
            elif command == 'b' and i > 0:
                i -= 1
            elif command == 'q':
                print("\n🛑 Stopping review...")
                break
        
        # Save review log
        self.save_review_log()
    
    def save_review_log(self):
        """Save review results"""
        log_file = self.soap_dir / 'manual_review_log.json'
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({
                'total_reviewed': len(self.review_log),
                'flagged': sum(1 for r in self.review_log if r['flagged']),
                'reviews': self.review_log
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Saved review log to: {log_file}")
        
        # Print summary
        print("\n" + "=" * 80)
        print("REVIEW SUMMARY")
        print("=" * 80)
        print(f"Total reviewed: {len(self.review_log)}")
        print(f"Flagged: {sum(1 for r in self.review_log if r['flagged'])}")
        
        # Quality breakdown
        quality_counts = {}
        for review in self.review_log:
            quality = review['responses'].get('Overall SOAP quality', 'unknown')
            quality_counts[quality] = quality_counts.get(quality, 0) + 1
        
        print("\nQuality Distribution:")
        for quality, count in sorted(quality_counts.items()):
            print(f"  {quality:12s}: {count:2d} ({count/len(self.review_log)*100:.1f}%)")
    
    def run(self):
        """Main review workflow"""
        review_data = self.load_review_list()
        if not review_data:
            return
        
        print("\n" + "=" * 80)
        print("SOAP NOTES MANUAL REVIEW INTERFACE")
        print("=" * 80)
        
        print("\nAvailable review sets:")
        print("1. Priority review (combined: stratified + edge cases + issues)")
        print("2. Stratified sample only (balanced across severity)")
        print("3. Edge cases only (high priority)")
        print("4. Sessions with automated issues")
        print("5. Custom session IDs")
        
        choice = input("\nSelect review set [1-5]: ").strip()
        
        if choice == '1':
            session_ids = review_data['priority_review']
        elif choice == '2':
            session_ids = review_data['stratified_sample']
        elif choice == '3':
            session_ids = review_data['edge_cases']
        elif choice == '4':
            session_ids = review_data['issues']
        elif choice == '5':
            custom = input("Enter session IDs (comma-separated): ").strip()
            session_ids = [int(x.strip()) for x in custom.split(',')]
        else:
            print("Invalid choice!")
            return
        
        print(f"\n✅ Selected {len(session_ids)} sessions for review\n")
        
        self.batch_review(session_ids)


if __name__ == '__main__':
    reviewer = SOAPReviewer()
    reviewer.run()
