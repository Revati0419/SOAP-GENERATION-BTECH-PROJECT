#!/usr/bin/env python3
"""
monitor_soap_generation.py
---------------------------
Monitor progress of SOAP note generation batch job.

Usage:
  python scripts/monitor_soap_generation.py
"""

import time
from pathlib import Path
import json

def monitor_progress():
    soap_dir = Path('data/soap_notes')
    total_sessions = 182  # Sessions 311-492
    start_session = 311
    end_session = 492
    
    print("\n" + "="*70)
    print("  SOAP GENERATION PROGRESS MONITOR")
    print("="*70 + "\n")
    
    while True:
        # Count generated files
        v3_files = list(soap_dir.glob('soap_*_v3.json'))
        total_generated = len(v3_files)
        
        # Find latest session
        session_ids = []
        for f in v3_files:
            try:
                sid = int(f.stem.split('_')[1])
                session_ids.append(sid)
            except:
                pass
        
        latest_session = max(session_ids) if session_ids else 0
        remaining = end_session - latest_session
        progress_pct = (total_generated / total_sessions) * 100
        
        # Estimate time remaining
        if total_generated > 11:  # We started with 11
            sessions_done = total_generated - 11
            time_per_session = 120  # ~2 minutes
            time_remaining = remaining * time_per_session
            hours = time_remaining // 3600
            minutes = (time_remaining % 3600) // 60
            eta = f"{int(hours)}h {int(minutes)}m"
        else:
            eta = "Calculating..."
        
        # Clear screen and display
        print("\033[H\033[J", end="")  # Clear terminal
        print("="*70)
        print("  SOAP GENERATION PROGRESS")
        print("="*70)
        print(f"\n📊 Total Generated: {total_generated}/{total_sessions} sessions")
        print(f"📈 Progress: [{'█' * int(progress_pct/2)}{' ' * (50-int(progress_pct/2))}] {progress_pct:.1f}%")
        print(f"\n🔢 Latest Session: {latest_session}")
        print(f"⏳ Remaining: {remaining} sessions")
        print(f"⏱️  ETA: {eta}")
        print(f"\n💾 Output: data/soap_notes/")
        print(f"📝 Log: soap_generation.log")
        print("\n" + "="*70)
        print("\nPress Ctrl+C to exit monitor (generation continues in background)")
        print("="*70)
        
        time.sleep(30)  # Update every 30 seconds


if __name__ == '__main__':
    try:
        monitor_progress()
    except KeyboardInterrupt:
        print("\n\n✅ Monitor stopped. Generation continues in background.")
        print("   Check progress: tail -f soap_generation.log")
        print("   Or run this monitor again: python scripts/monitor_soap_generation.py\n")
