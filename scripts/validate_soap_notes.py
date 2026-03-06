"""
SOAP Note Quality Validation Script
------------------------------------
Automated quality checks + intelligent sampling for manual review
"""

import json
import os
import random
from pathlib import Path
from collections import defaultdict
import statistics

class SOAPValidator:
    def __init__(self, soap_dir='data/soap_notes'):
        self.soap_dir = Path(soap_dir)
        self.issues = defaultdict(list)
        self.metrics = defaultdict(list)
        
    def load_all_soaps(self):
        """Load all generated SOAP notes"""
        soaps = []
        for file in self.soap_dir.glob('*_soap.json'):
            if 'readable' not in file.name:
                with open(file, 'r', encoding='utf-8') as f:
                    soaps.append(json.load(f))
        return soaps
    
    def check_completeness(self, soap):
        """Check if all SOAP sections are present and non-empty"""
        session_id = soap['session_id']
        issues = []
        
        # Check English sections
        for section in ['subjective', 'objective', 'assessment', 'plan']:
            content = soap['soap_english'].get(section, '')
            if not content or len(content) < 50:  # Minimum 50 chars
                issues.append(f"English {section} too short ({len(content)} chars)")
        
        # Check Marathi sections
        for section in ['subjective', 'objective', 'assessment', 'plan']:
            content = soap['soap_marathi'].get(section, '')
            if not content or len(content) < 50:
                issues.append(f"Marathi {section} too short ({len(content)} chars)")
        
        return issues
    
    def check_language_quality(self, soap):
        """Check for obvious translation/generation issues"""
        issues = []
        
        # Check for English words in Marathi (should be minimal)
        marathi_text = ' '.join([
            soap['soap_marathi'].get(s, '') 
            for s in ['subjective', 'objective', 'assessment', 'plan']
        ])
        
        # Count English characters vs Devanagari
        english_chars = sum(1 for c in marathi_text if ord(c) < 128)
        total_chars = len(marathi_text)
        
        if total_chars > 0:
            english_ratio = english_chars / total_chars
            if english_ratio > 0.3:  # More than 30% English in "Marathi"
                issues.append(f"Marathi text has {english_ratio:.1%} English characters")
        
        return issues
    
    def check_consistency(self, soap):
        """Check logical consistency in SOAP note"""
        issues = []
        
        # PHQ-8 severity mapping
        phq8_score = soap.get('phq8_score', 0)
        severity_map = {
            range(0, 5): 'minimal',
            range(5, 10): 'mild', 
            range(10, 15): 'moderate',
            range(15, 25): 'moderately severe'
        }
        
        expected_severity = None
        for score_range, severity in severity_map.items():
            if phq8_score in score_range:
                expected_severity = severity
                break
        
        # Check if assessment mentions appropriate severity
        assessment = soap['soap_english'].get('assessment', '').lower()
        if expected_severity and expected_severity not in assessment:
            issues.append(f"Assessment doesn't mention severity level (PHQ-8: {phq8_score})")
        
        return issues
    
    def calculate_metrics(self, soap):
        """Calculate quality metrics for each SOAP"""
        metrics = {}
        
        # Length metrics
        for lang in ['english', 'marathi']:
            key = f'soap_{lang}'
            total_length = sum(
                len(soap[key].get(s, '')) 
                for s in ['subjective', 'objective', 'assessment', 'plan']
            )
            metrics[f'{lang}_total_length'] = total_length
        
        # Section balance (should have reasonable distribution)
        en_lengths = [
            len(soap['soap_english'].get(s, ''))
            for s in ['subjective', 'objective', 'assessment', 'plan']
        ]
        metrics['section_balance'] = statistics.stdev(en_lengths) if len(en_lengths) > 1 else 0
        
        return metrics
    
    def stratified_sample(self, soaps, n_per_stratum=3):
        """Create stratified sample based on PHQ-8 scores"""
        strata = defaultdict(list)
        
        for soap in soaps:
            score = soap.get('phq8_score', 0)
            if score < 5:
                strata['minimal'].append(soap)
            elif score < 10:
                strata['mild'].append(soap)
            elif score < 15:
                strata['moderate'].append(soap)
            else:
                strata['severe'].append(soap)
        
        sample = []
        for stratum, items in strata.items():
            n_sample = min(n_per_stratum, len(items))
            sample.extend(random.sample(items, n_sample))
        
        return sample
    
    def edge_case_sample(self, soaps):
        """Identify edge cases that need manual review"""
        edge_cases = []
        
        for soap in soaps:
            # Very high PHQ-8 scores (critical)
            if soap.get('phq8_score', 0) >= 20:
                edge_cases.append(('high_severity', soap))
            
            # Very short SOAP notes (potential incompleteness)
            total_length = sum(
                len(soap['soap_english'].get(s, ''))
                for s in ['subjective', 'objective', 'assessment', 'plan']
            )
            if total_length < 500:
                edge_cases.append(('too_short', soap))
            
            # Very long SOAP notes (potential hallucination)
            if total_length > 3000:
                edge_cases.append(('too_long', soap))
        
        return edge_cases
    
    def validate_all(self):
        """Run complete validation pipeline"""
        print("=" * 80)
        print("SOAP NOTES QUALITY VALIDATION")
        print("=" * 80)
        
        soaps = self.load_all_soaps()
        print(f"\n📊 Loaded {len(soaps)} SOAP notes\n")
        
        # Run automated checks
        all_issues = []
        for soap in soaps:
            session_id = soap['session_id']
            issues = []
            
            issues.extend(self.check_completeness(soap))
            issues.extend(self.check_language_quality(soap))
            issues.extend(self.check_consistency(soap))
            
            if issues:
                all_issues.append((session_id, issues))
            
            # Collect metrics
            metrics = self.calculate_metrics(soap)
            for key, value in metrics.items():
                self.metrics[key].append(value)
        
        # Report issues
        print("🔍 AUTOMATED QUALITY CHECKS:")
        print("-" * 80)
        if all_issues:
            print(f"❌ Found issues in {len(all_issues)} sessions:\n")
            for session_id, issues in all_issues[:10]:  # Show first 10
                print(f"Session {session_id}:")
                for issue in issues:
                    print(f"  • {issue}")
                print()
        else:
            print("✅ No critical issues found!\n")
        
        # Report metrics
        print("\n📈 QUALITY METRICS:")
        print("-" * 80)
        for metric, values in self.metrics.items():
            if values:
                print(f"{metric:30s}: μ={statistics.mean(values):6.1f}, "
                      f"σ={statistics.stdev(values):6.1f}, "
                      f"range=[{min(values):.0f}, {max(values):.0f}]")
        
        # Generate sampling recommendations
        print("\n\n🎯 RECOMMENDED MANUAL REVIEW SAMPLES:")
        print("=" * 80)
        
        # Stratified sample
        print("\n1️⃣ STRATIFIED RANDOM SAMPLE (by severity):")
        print("-" * 80)
        stratified = self.stratified_sample(soaps, n_per_stratum=3)
        for soap in sorted(stratified, key=lambda x: x['phq8_score']):
            print(f"Session {soap['session_id']:3d} | "
                  f"PHQ-8: {soap['phq8_score']:2d}/24 | "
                  f"Severity: {soap['severity']:20s} | "
                  f"Gender: {soap['gender']}")
        
        # Edge cases
        print("\n\n2️⃣ EDGE CASES (high priority review):")
        print("-" * 80)
        edge_cases = self.edge_case_sample(soaps)
        for reason, soap in edge_cases[:10]:  # Show first 10
            print(f"Session {soap['session_id']:3d} | "
                  f"Reason: {reason:15s} | "
                  f"PHQ-8: {soap['phq8_score']:2d}/24")
        
        # Sessions with issues
        if all_issues:
            print("\n\n3️⃣ SESSIONS WITH AUTOMATED ISSUES:")
            print("-" * 80)
            for session_id, issues in all_issues[:10]:
                print(f"Session {session_id:3d} | Issues: {len(issues)}")
        
        # Generate review checklist
        print("\n\n📋 MANUAL REVIEW CHECKLIST:")
        print("=" * 80)
        review_list = set([s['session_id'] for s in stratified])
        review_list.update([soap['session_id'] for _, soap in edge_cases[:5]])
        review_list.update([sid for sid, _ in all_issues[:5]])
        
        print(f"Total sessions to review: {len(review_list)} ({len(review_list)/len(soaps)*100:.1f}%)")
        print(f"\nSession IDs: {sorted(review_list)[:20]}")
        
        # Save review list
        review_file = self.soap_dir / 'review_list.json'
        with open(review_file, 'w') as f:
            json.dump({
                'stratified_sample': [s['session_id'] for s in stratified],
                'edge_cases': [soap['session_id'] for _, soap in edge_cases],
                'issues': [sid for sid, _ in all_issues],
                'priority_review': sorted(review_list)
            }, f, indent=2)
        
        print(f"\n💾 Saved review list to: {review_file}")
        
        return {
            'total_soaps': len(soaps),
            'issues_found': len(all_issues),
            'review_required': len(review_list),
            'metrics': self.metrics
        }


if __name__ == '__main__':
    validator = SOAPValidator()
    results = validator.validate_all()
    
    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
    print(f"✅ Processed: {results['total_soaps']} SOAP notes")
    print(f"⚠️  Issues found: {results['issues_found']}")
    print(f"📝 Manual review needed: {results['review_required']} sessions")
    print(f"   (That's {results['review_required']/results['total_soaps']*100:.1f}% of total)")
