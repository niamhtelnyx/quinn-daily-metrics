#!/usr/bin/env python3
"""
Quick test to isolate the hang and get 5:30 PM run working
"""
import subprocess
import os
import sys
from datetime import datetime

def log_message(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")

def run_gog_command_simple(cmd):
    """Simplified version with explicit environment"""
    try:
        env = os.environ.copy()
        env['GOG_ACCOUNT'] = 'niamh@telnyx.com'
        env['GOG_KEYRING_PASSWORD'] = 'clawdgog123'
        
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
            executable='/bin/bash'
        )
        
        if result.returncode != 0:
            return None, f"Command failed: {result.stderr}"
        
        return result.stdout, None
        
    except subprocess.TimeoutExpired:
        return None, "Command timed out (30s)"
    except Exception as e:
        return None, f"Error: {str(e)}"

if __name__ == "__main__":
    log_message("🧪 Quick fix test starting")
    
    # Test 1: Basic gog command
    cmd = 'gog --version'
    output, error = run_gog_command_simple(cmd)
    if error:
        log_message(f"❌ Basic gog failed: {error}")
        sys.exit(1)
    else:
        log_message(f"✅ Basic gog works: {output.strip()}")
    
    # Test 2: Drive folder listing
    cmd = 'gog drive ls --parent 1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY --max 5 --plain --account niamh@telnyx.com'
    output, error = run_gog_command_simple(cmd)
    if error:
        log_message(f"❌ Folder listing failed: {error}")
        sys.exit(1)
    else:
        log_message(f"✅ Folder listing works: {len(output)} chars")
        lines = output.strip().split('\n')
        log_message(f"✅ Found {len(lines)-1} items")
    
    log_message("🎉 All tests passed - environment is working")