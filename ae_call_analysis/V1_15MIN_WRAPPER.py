#!/usr/bin/env python3
"""
15-minute interval wrapper - runs twice with 15-min gap
Solves crontab update issues by simulating 15-min intervals within 30-min cron
"""

import subprocess
import time
import os
import sys
from datetime import datetime

def run_call_analysis():
    """Run the working hierarchy call analysis once"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] 🚀 Starting call analysis...")
    
    try:
        env = os.environ.copy()
        env['PATH'] = '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:' + env.get('PATH', '')
        
        cmd = """
        cd /Users/niamhcollins/clawd/ae_call_analysis
        set -a  # Auto-export all variables
        source /Users/niamhcollins/clawd/.env.gog 2>/dev/null || true
        source .env 2>/dev/null || true
        set +a
        python3 main.py
        """
        
        result = subprocess.run(['bash', '-c', cmd], 
                              capture_output=True, text=True, timeout=120, env=env)
        
        if result.returncode == 0:
            print(f"[{timestamp}] ✅ Analysis completed successfully")
            # Extract summary from output
            if "PROCESSING SUMMARY" in result.stdout:
                summary_start = result.stdout.find("PROCESSING SUMMARY")
                summary_part = result.stdout[summary_start:summary_start+500]
                print(summary_part)
            return True
        else:
            print(f"[{timestamp}] ❌ Analysis failed (exit {result.returncode})")
            if result.stderr:
                print(f"Error: {result.stderr[:200]}")
            return False
                
    except subprocess.TimeoutExpired:
        print(f"[{timestamp}] ⏱️ Analysis timed out (2 min limit)")
        return False
    except Exception as e:
        print(f"[{timestamp}] 💥 Error: {e}")
        return False

def main():
    """Run call analysis twice with 15-minute interval"""
    start_time = datetime.now()
    print("⚡ 15-MINUTE INTERVAL CALL ANALYSIS WRAPPER")
    print("=" * 60)
    print(f"Start time: {start_time}")
    
    # First run (immediate)
    print(f"\n📅 FIRST RUN ({start_time.strftime('%H:%M:%S')})")
    success1 = run_call_analysis()
    
    # Calculate next run time
    wait_seconds = 15 * 60  # 15 minutes
    next_run_time = datetime.fromtimestamp(time.time() + wait_seconds)
    
    print(f"\n⏰ WAITING 15 MINUTES...")
    print(f"   Next run scheduled: {next_run_time.strftime('%H:%M:%S')}")
    
    # Wait 15 minutes
    time.sleep(wait_seconds)
    
    # Second run
    second_start = datetime.now()
    print(f"\n📅 SECOND RUN ({second_start.strftime('%H:%M:%S')})")
    success2 = run_call_analysis()
    
    # Final summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n{'=' * 60}")
    print("📊 15-MINUTE WRAPPER SUMMARY:")
    print(f"{'=' * 60}")
    print(f"    ⏱️ Total duration: {duration/60:.1f} minutes")
    print(f"    📅 First run: {'✅ SUCCESS' if success1 else '❌ FAILED'}")
    print(f"    📅 Second run: {'✅ SUCCESS' if success2 else '❌ FAILED'}")
    print(f"    🎯 Overall: {'✅ SUCCESS' if (success1 or success2) else '❌ FAILED'}")
    
    # Exit with success if at least one run succeeded
    sys.exit(0 if (success1 or success2) else 1)

if __name__ == "__main__":
    main()