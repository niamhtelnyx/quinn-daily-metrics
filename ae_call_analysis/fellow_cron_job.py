#!/usr/bin/env python3
"""
Cron bridge: Calls the new V1_PRODUCTION_DATE.py system (Date Hierarchy)
DEPLOYED: 2026-03-05 - New date-based folder structure support
"""
import subprocess
import sys
import os

def main():
    print(f"[{os.popen('date').read().strip()}] 🚀 Calling V1_PRODUCTION_DATE.py system (Date Hierarchy)...")
    
    try:
        # Set up proper environment for cron
        env = os.environ.copy()
        env['PATH'] = '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:' + env.get('PATH', '')
        
        # DATE HIERARCHY: Process recent date folders with FULL pipeline 
        cmd = """
        cd /Users/niamhcollins/clawd/ae_call_analysis
        set -a  # Auto-export all variables
        source /Users/niamhcollins/clawd/.env.gog 2>/dev/null || true
        source .env 2>/dev/null || true
        set +a
        python3 V1_DATE_FULL.py
        """
        
        result = subprocess.run(['bash', '-c', cmd], 
                              capture_output=True, text=True, timeout=300, env=env)
        
        if result.returncode == 0:
            print("✅ V1 Date Hierarchy system completed successfully")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"❌ V1 Date Hierarchy system failed (exit {result.returncode})")
            if result.stderr:
                print(f"Error: {result.stderr}")
                
    except subprocess.TimeoutExpired:
        print("⏱️  V1 Date Hierarchy system timed out (5 min limit)")
    except Exception as e:
        print(f"💥 Bridge error: {e}")

if __name__ == "__main__":
    main()
