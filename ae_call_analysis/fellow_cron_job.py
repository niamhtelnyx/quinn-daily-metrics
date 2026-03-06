#!/usr/bin/env python3
"""
Production Cron Bridge: Modular Architecture Deployment
UPDATED: 2026-03-05 19:01 - Calls new modular main.py via V1_15MIN_WRAPPER.py
"""
import subprocess
import sys
import os

def main():
    print(f"[{os.popen('date').read().strip()}] 🚀 Deploying modular architecture with enhanced Salesforce...")
    
    try:
        # Set up proper environment for cron
        env = os.environ.copy()
        env['PATH'] = '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:' + env.get('PATH', '')
        
        # Load environment variables for cron context
        env_files = ['.env', '/Users/niamhcollins/clawd/.env.gog']
        for env_file in env_files:
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env[key] = value
        
        # Call the modular system via wrapper for 15-minute intervals
        cmd = """
        cd /Users/niamhcollins/clawd/ae_call_analysis
        python3 V1_15MIN_WRAPPER.py
        """
        
        result = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("✅ Modular architecture deployment successful")
            print(f"📄 Output: {result.stdout[-500:]}")  # Last 500 chars
        else:
            print(f"⚠️ System completed with warnings (code {result.returncode})")
            print(f"📄 Output: {result.stdout[-300:]}")
            if result.stderr:
                print(f"⚠️ Stderr: {result.stderr[-200:]}")
        
    except subprocess.TimeoutExpired:
        print("⏰ Timeout: System taking longer than 10 minutes - this may indicate hanging")
    except Exception as e:
        print(f"💥 Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()