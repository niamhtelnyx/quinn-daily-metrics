#!/usr/bin/env python3
"""
15-minute interval wrapper for call analysis
Runs the resilient system twice per cron cycle (every 15 minutes)
"""
import subprocess
import sys
import os
import time
from datetime import datetime

def run_resilient_system():
    """Run the resilient call analysis system once"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] 🛡️ Starting resilient call analysis...")
    
    try:
        env = os.environ.copy()
        env['PATH'] = '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:' + env.get('PATH', '')
        
        cmd = """
        cd /Users/niamhcollins/clawd/ae_call_analysis
        set -a  # Auto-export all variables
        source /Users/niamhcollins/clawd/.env.gog 2>/dev/null || true
        source .env 2>/dev/null || true
        set +a
        python3 V1_DATE_FULL_RESILIENT.py
        """
        
        result = subprocess.run(['bash', '-c', cmd], 
                              capture_output=True, text=True, timeout=300, env=env)
        
        if result.returncode == 0:
            print(f"[{timestamp}] ✅ Resilient system completed successfully")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"[{timestamp}] ❌ Resilient system failed (exit {result.returncode})")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
                
    except subprocess.TimeoutExpired:
        print(f"[{timestamp}] ⏱️ Resilient system timed out (5 min limit)")
        return False
    except Exception as e:
        print(f"[{timestamp}] 💥 Error: {e}")
        return False

def main():
    """Run resilient system twice with 15-minute interval"""
    print("🚀 15-MINUTE CALL ANALYSIS WRAPPER")
    print("=" * 50)
    
    # First run
    print("\n📅 FIRST RUN (Immediate)")
    success1 = run_resilient_system()
    
    # Wait 15 minutes for second run
    print(f"\n⏰ WAITING 15 MINUTES...")
    print(f"   Next run at: {datetime.fromtimestamp(time.time() + 900).strftime('%H:%M:%S')}")
    time.sleep(900)  # 15 minutes = 900 seconds
    
    # Second run
    print("\n📅 SECOND RUN (After 15 min delay)")
    success2 = run_resilient_system()
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 15-MINUTE CYCLE SUMMARY")
    print(f"{'='*50}")
    print(f"First run:  {'✅ SUCCESS' if success1 else '❌ FAILED'}")
    print(f"Second run: {'✅ SUCCESS' if success2 else '❌ FAILED'}")
    
    # Exit with success if at least one run succeeded
    sys.exit(0 if (success1 or success2) else 1)

if __name__ == "__main__":
    main()