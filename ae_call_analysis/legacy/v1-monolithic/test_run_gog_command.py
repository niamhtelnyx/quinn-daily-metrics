#!/usr/bin/env python3
"""
Test the exact run_gog_command function that V1 Enhanced uses
"""
import subprocess
import os

def run_gog_command(cmd):
    """Run gog CLI command and return output (exact copy from V1_GOOGLE_DRIVE_ENHANCED.py)"""
    try:
        env = os.environ.copy()
        env_file_path = '/Users/niamhcollins/clawd/.env.gog'
        
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#') and '=' in line:
                        key, value = line.strip().split('=', 1)
                        if key.startswith('export '):
                            key = key[7:]
                        env[key] = value.strip('"')
        
        result = subprocess.run(
            f'source /Users/niamhcollins/clawd/.env.gog && {cmd}',
            shell=True,
            capture_output=True,
            text=True,
            env=env,
            executable='/bin/bash'
        )
        
        if result.returncode != 0:
            return None, f"Command failed: {result.stderr}"
        
        return result.stdout, None
        
    except Exception as e:
        return None, f"Error running gog command: {str(e)}"

def test_content_extraction():
    doc_id = "1PkWoJnZe49W4SEVAIYoa6BvMs7f7gSSbdls3I5KusDg"
    
    print("🔍 Testing run_gog_command with docs cat...")
    output, error = run_gog_command(f'gog docs cat {doc_id}')
    
    if error:
        print(f"❌ Error: {error}")
    else:
        if output:
            content_length = len(output.strip())
            print(f"✅ Success: Got {content_length} characters")
            print(f"📝 First 200 chars: {output[:200]}")
            
            # Check if content has the key info we need
            if "Kevin Burke" in output:
                print("✅ Contains 'Kevin Burke'")
            else:
                print("❌ Missing 'Kevin Burke'")
                
            if "Austin Lazarus" in output:
                print("✅ Contains 'Austin Lazarus'")
            else:
                print("❌ Missing 'Austin Lazarus'")
                
            if "Voxtelesys" in output:
                print("✅ Contains 'Voxtelesys'")
            else:
                print("❌ Missing 'Voxtelesys'")
        else:
            print("❌ No output returned")

if __name__ == "__main__":
    test_content_extraction()
