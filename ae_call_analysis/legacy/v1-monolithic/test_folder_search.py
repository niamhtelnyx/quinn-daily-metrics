#!/usr/bin/env python3
"""
Test folder-specific search functionality
"""

import os
import subprocess
import sys

def run_gog_command(cmd):
    """Run gog CLI command and return output"""
    try:
        result = subprocess.run(
            f'source /Users/niamhcollins/clawd/.env.gog && {cmd}',
            shell=True,
            capture_output=True,
            text=True,
            executable='/bin/bash'
        )
        
        if result.returncode != 0:
            return None, f"Command failed: {result.stderr}"
        
        return result.stdout, None
        
    except Exception as e:
        return None, f"Error running gog command: {str(e)}"

def test_folder_search():
    """Test the folder search functionality"""
    folder_id = "1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY"
    
    print("🧪 Testing Folder-Specific Search")
    print("=" * 40)
    print(f"📁 Target folder: {folder_id}")
    print()
    
    # Step 1: Get subfolders
    print("📂 Step 1: Finding subfolders...")
    subfolders_output, error = run_gog_command(f'gog drive ls --parent {folder_id} --max 50 --plain')
    
    if error:
        print(f"❌ Error: {error}")
        return
    
    subfolder_ids = [folder_id]  # Include main folder
    
    if subfolders_output and 'ID' in subfolders_output:
        lines = [line.strip() for line in subfolders_output.split('\n') if line.strip()]
        for line in lines[1:]:  # Skip header
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) >= 3:
                folder_id_part = parts[0]
                folder_name = parts[1]
                folder_type = parts[2]
                
                if 'folder' in folder_type:
                    subfolder_ids.append(folder_id_part)
                    print(f"   📂 Found: {folder_name}")
    
    print(f"✅ Found {len(subfolder_ids)} total folders to search")
    print()
    
    # Step 2: Search for Gemini notes in each folder
    print("🔍 Step 2: Searching for Gemini notes...")
    total_calls = []
    
    for i, current_folder_id in enumerate(subfolder_ids):
        print(f"   🔍 Searching folder {i+1}/{len(subfolder_ids)}: {current_folder_id}")
        
        output, error = run_gog_command(f'gog drive ls --parent {current_folder_id} --query "name contains \'Gemini\'" --max 20 --plain')
        
        if error:
            print(f"      ❌ Error: {error}")
            continue
        
        if not output or 'ID' not in output:
            print(f"      📭 No Gemini files found")
            continue
        
        lines = [line.strip() for line in output.split('\n') if line.strip()]
        folder_call_count = 0
        
        for line in lines[1:]:  # Skip header
            if not line or line.startswith('#'):
                continue
                
            parts = line.split('\t')
            if len(parts) >= 4:
                call_id = parts[0]
                name = parts[1]
                file_type = parts[2]
                
                if 'file' in file_type and 'gemini' in name.lower():
                    total_calls.append({
                        'id': call_id,
                        'title': name,
                        'folder': current_folder_id
                    })
                    folder_call_count += 1
                    print(f"      📄 {folder_call_count}. {name[:70]}...")
        
        print(f"      ✅ Found {folder_call_count} Gemini calls in this folder")
        print()
    
    print(f"🎉 TOTAL RESULTS: Found {len(total_calls)} Gemini call notes across all folders")
    print()
    
    if total_calls:
        print("📋 Summary of calls found:")
        for i, call in enumerate(total_calls[:5]):  # Show first 5
            print(f"   {i+1}. {call['title'][:80]}...")
        
        if len(total_calls) > 5:
            print(f"   ... and {len(total_calls) - 5} more calls")
    
    return len(total_calls)

if __name__ == "__main__":
    count = test_folder_search()
    if count > 0:
        print(f"\n✅ SUCCESS: Folder search working! Found {count} calls.")
        print("🚀 Ready to deploy folder-specific system")
    else:
        print(f"\n❌ FAILED: No calls found in folder structure")
        print("🔧 Check folder permissions and Gemini notes location")