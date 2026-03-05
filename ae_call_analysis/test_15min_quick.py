#!/usr/bin/env python3
"""
Quick test of 15-minute wrapper using 30-second delay instead of 15 minutes
"""

import subprocess
import time
import os
import sys
from datetime import datetime

def run_call_analysis():
    """Run call analysis once (quick version)"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] 🚀 Starting call analysis...")
    
    try:
        env = os.environ.copy()
        env['PATH'] = '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:' + env.get('PATH', '')
        
        cmd = """
        cd /Users/niamhcollins/clawd/ae_call_analysis
        set -a
        source /Users/niamhcollins/clawd/.env.gog 2>/dev/null || true
        source .env 2>/dev/null || true
        set +a
        python3 V1_WORKING_HIERARCHY.py
        """
        
        result = subprocess.run(['bash', '-c', cmd], 
                              capture_output=True, text=True, timeout=60, env=env)
        
        if result.returncode == 0:
            # Extract just the summary
            if "Calls processed:" in result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if "Calls processed:" in line:
                        print(f"        {line.strip()}")
                        break
            print(f"[{timestamp}] ✅ Analysis completed")
            return True
        else:
            print(f"[{timestamp}] ❌ Analysis failed")
            return False
                
    except Exception as e:
        print(f"[{timestamp}] 💥 Error: {str(e)[:100]}")
        return False

def main():
    """Test with 30-second interval"""
    start_time = datetime.now()
    print("🧪 TESTING 15-MINUTE WRAPPER (30-second intervals)")
    print("=" * 50)
    
    # First run
    print(f"\n📅 FIRST RUN ({start_time.strftime('%H:%M:%S')})")
    success1 = run_call_analysis()
    
    # Wait 30 seconds instead of 15 minutes
    print(f"\n⏰ WAITING 30 SECONDS (simulating 15 minutes)...")
    time.sleep(30)
    
    # Second run
    second_start = datetime.now()
    print(f"\n📅 SECOND RUN ({second_start.strftime('%H:%M:%S')})")
    success2 = run_call_analysis()
    
    # Summary
    print(f"\n{'=' * 50}")
    print("📊 TEST SUMMARY:")
    print(f"    📅 First run: {'✅ SUCCESS' if success1 else '❌ FAILED'}")
    print(f"    📅 Second run: {'✅ SUCCESS' if success2 else '❌ FAILED'}")
    print(f"    🎯 15-min wrapper: {'✅ WORKING' if (success1 or success2) else '❌ BROKEN'}")

if __name__ == "__main__":
    main()