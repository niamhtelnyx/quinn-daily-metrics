#!/usr/bin/env python3
"""
Test version of 15-minute wrapper with 30-second delay instead of 15 minutes
"""
import subprocess
import sys
import os
import time
from datetime import datetime

def run_resilient_system():
    """Run the resilient call analysis system once"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] 🛡️ Starting resilient call analysis (TEST)...")
    
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
                              capture_output=True, text=True, timeout=60, env=env)
        
        if result.returncode == 0:
            print(f"[{timestamp}] ✅ Resilient system completed successfully")
            # Truncate output for test
            output_lines = result.stdout.split('\n')[:10] 
            for line in output_lines:
                if line.strip():
                    print(f"   {line}")
            if len(result.stdout.split('\n')) > 10:
                print(f"   ... (output truncated)")
            return True
        else:
            print(f"[{timestamp}] ❌ Resilient system failed (exit {result.returncode})")
            if result.stderr:
                print(f"Error: {result.stderr[:200]}")
            return False
                
    except subprocess.TimeoutExpired:
        print(f"[{timestamp}] ⏱️ Resilient system timed out (1 min limit)")
        return False
    except Exception as e:
        print(f"[{timestamp}] 💥 Error: {e}")
        return False

def main():
    """Test 15-minute wrapper with 30-second delay"""
    print("🧪 TESTING 15-MINUTE WRAPPER (30-second intervals)")
    print("=" * 60)
    
    # First run
    print("\n📅 FIRST RUN (Immediate)")
    success1 = run_resilient_system()
    
    # Wait 30 seconds for second run (instead of 15 minutes)
    print(f"\n⏰ WAITING 30 SECONDS (simulating 15-minute delay)...")
    time.sleep(30)
    
    # Second run
    print("\n📅 SECOND RUN (After 30-sec delay)")
    success2 = run_resilient_system()
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST WRAPPER SUMMARY")
    print(f"{'='*60}")
    print(f"First run:  {'✅ SUCCESS' if success1 else '❌ FAILED'}")
    print(f"Second run: {'✅ SUCCESS' if success2 else '❌ FAILED'}")
    print(f"Overall:    {'✅ SUCCESS' if (success1 or success2) else '❌ FAILED'}")
    
    # Exit with success if at least one run succeeded
    sys.exit(0 if (success1 or success2) else 1)

if __name__ == "__main__":
    main()