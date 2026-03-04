#!/usr/bin/env python3
"""
Debug the Telnyx // Voxtelesys parsing issue
"""
import subprocess
import json
import os

def load_env():
    """Load environment"""
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def get_google_doc_content(doc_id):
    """Get the actual content from the Google Doc"""
    try:
        # Set up environment for gog
        env = os.environ.copy()
        env['PATH'] = '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:' + env.get('PATH', '')
        
        # Source .env.gog and get doc content
        cmd = f"""
        source /Users/niamhcollins/clawd/.env.gog
        gog drive get {doc_id} --format text
        """
        
        result = subprocess.run(['bash', '-c', cmd], capture_output=True, text=True, env=env, timeout=30)
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"❌ Error getting doc content: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Exception getting doc content: {e}")
        return None

def debug_prospect_parsing(content):
    """Debug how the prospect name gets extracted"""
    print("🔍 DEBUGGING PROSPECT NAME EXTRACTION")
    print("=" * 60)
    
    if not content:
        print("❌ No content to parse")
        return
    
    print(f"📝 Content length: {len(content)} characters")
    print(f"📝 First 500 characters:")
    print("-" * 40)
    print(content[:500])
    print("-" * 40)
    
    # Look for common patterns
    patterns_to_check = [
        "Attendees:",
        "Meeting with:",
        "Participants:",
        "Present:",
        "Call with:",
        "Voxtelesys",
        "VoxTelecom",
        "@voxtelesys",
        "@voxtelecom"
    ]
    
    print("\n🔍 Searching for patterns:")
    for pattern in patterns_to_check:
        if pattern.lower() in content.lower():
            print(f"✅ Found: '{pattern}'")
            # Show context around the match
            idx = content.lower().find(pattern.lower())
            start = max(0, idx - 100)
            end = min(len(content), idx + 200)
            context = content[start:end].replace('\n', ' ')
            print(f"   Context: ...{context}...")
        else:
            print(f"❌ Not found: '{pattern}'")

if __name__ == "__main__":
    load_env()
    
    # The doc ID from the log
    doc_id = "1PkWoJnZe49W4SEVAIYoa6BvMs7f7gSSbdls3I5KusDg"
    
    print(f"📁 Getting content for Telnyx // Voxtelesys meeting: {doc_id}")
    content = get_google_doc_content(doc_id)
    
    if content:
        debug_prospect_parsing(content)
    else:
        print("❌ Could not retrieve document content")
