#!/usr/bin/env python3
"""
Debug why content extraction returns None for Voxtelesys doc
"""
import os
import subprocess

def debug_google_doc_content():
    doc_id = "1PkWoJnZe49W4SEVAIYoa6BvMs7f7gSSbdls3I5KusDg"  # Voxtelesys doc
    
    print("🔍 DEBUGGING CONTENT EXTRACTION FAILURE")
    print(f"Doc ID: {doc_id}")
    print("-" * 60)
    
    # Test 1: Can we get doc metadata?
    print("1️⃣ Testing doc metadata access...")
    try:
        cmd = f"gog drive get {doc_id}"
        result = subprocess.run(['bash', '-c', f'source /Users/niamhcollins/clawd/.env.gog && {cmd}'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Can access doc metadata")
        else:
            print(f"❌ Metadata access failed: {result.stderr}")
            return
    except Exception as e:
        print(f"❌ Exception getting metadata: {e}")
        return
    
    # Test 2: Can we download the doc?
    print("\n2️⃣ Testing content download...")
    try:
        cmd = f"gog drive download {doc_id}"
        result = subprocess.run(['bash', '-c', f'source /Users/niamhcollins/clawd/.env.gog && {cmd}'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ Can download doc")
            print(f"   Output: {result.stdout}")
        else:
            print(f"❌ Download failed: {result.stderr}")
            return
    except Exception as e:
        print(f"❌ Exception downloading: {e}")
        return
    
    # Test 3: Check how V1 Enhanced tries to get content
    print("\n3️⃣ Testing V1 Enhanced method...")
    # Look at the actual function in V1_GOOGLE_DRIVE_ENHANCED.py
    print("   Looking at get_google_doc_content function...")

if __name__ == "__main__":
    debug_google_doc_content()
