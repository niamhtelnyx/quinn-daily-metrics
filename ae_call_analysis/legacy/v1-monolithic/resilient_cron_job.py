#!/usr/bin/env python3
"""
Resilient cron job with hang detection and auto-restart
Replaces fellow_cron_job.py with better reliability
"""

import subprocess
import time
import signal
import os
import sys
from datetime import datetime

def setup_environment():
    """Set up environment variables for subprocess"""
    env = os.environ.copy()
    
    # Load .env file manually
    env_file = '/Users/niamhcollins/clawd/ae_call_analysis/.env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env[key] = value
    
    # Load .env.gog file
    gog_env_file = '/Users/niamhcollins/clawd/.env.gog'
    if os.path.exists(gog_env_file):
        with open(gog_env_file, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env[key] = value
    
    return env

def run_with_hang_detection(timeout=300):
    """Run the resilient system with hang detection"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] 🚀 Starting resilient call analysis system")
    
    env = setup_environment()
    
    # Change to the correct directory
    os.chdir('/Users/niamhcollins/clawd/ae_call_analysis')
    
    try:
        # Run the resilient version with timeout
        result = subprocess.run([
            sys.executable,  # Use current Python interpreter
            'V1_DATE_FULL_RESILIENT.py'
        ], 
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env
        )
        
        if result.returncode == 0:
            print(f"[{timestamp}] ✅ Completed successfully")
            print(result.stdout)
            return True
        else:
            print(f"[{timestamp}] ❌ Process failed with return code {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"[{timestamp}] ⏰ TIMEOUT: Process hung after {timeout}s - killing")
        return False
    except Exception as e:
        print(f"[{timestamp}] ❌ ERROR: {str(e)}")
        return False

def main():
    """Main cron job function"""
    log_file = '/Users/niamhcollins/clawd/ae_call_analysis/logs/resilient_cron.log'
    
    # Ensure logs directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Run with hang detection (5 minute timeout)
    success = run_with_hang_detection(timeout=300)
    
    # Log result
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "SUCCESS" if success else "FAILED"
    
    with open(log_file, 'a') as f:
        f.write(f"[{timestamp}] {status}\n")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()