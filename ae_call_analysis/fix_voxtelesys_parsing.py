#!/usr/bin/env python3
"""
Fix the parsing issues for Voxtelesys case
"""

# Read the current file
with open('V1_GOOGLE_DRIVE_ENHANCED.py', 'r') as f:
    content = f.read()

# Fix 1: Add Austin Lazarus to AE list
old_ae_list = """    telnyx_aes = [
        'niamh collins', 'ryan simkins', 'tyron pretorius',
        'kai luo', 'rob messier', 'danilo', 'gulsah', 'luke', 'khalil', 'jagoda',
        'conor', 'mario', 'abdullah', 'edmond', 'brian'
    ]"""

new_ae_list = """    telnyx_aes = [
        'niamh collins', 'ryan simkins', 'tyron pretorius', 'austin lazarus',
        'kai luo', 'rob messier', 'danilo', 'gulsah', 'luke', 'khalil', 'jagoda',
        'conor', 'mario', 'abdullah', 'edmond', 'brian', 'chris cho'
    ]"""

# Fix 2: Add pattern for "Telnyx // Company"
old_patterns = """        title_patterns = [
            r'^Copy of ([^<>&|]+)\s*[<>&|]+\s*Telnyx',  # "Company <> Telnyx"
            r'^Copy of Telnyx\s*[<>&|]+\s*([^-]+)',      # "Telnyx <> Company"  
            r'^Copy of ([^/]+)\s*/\s*Telnyx',            # "Company / Telnyx"
            r'^Copy of (.+?)\s+and\s+\w+:',              # "Company and Person:"
            r'^Copy of (.+?)\s+-\s+.*Notes by Gemini',   # Extract before date
        ]"""

new_patterns = """        title_patterns = [
            r'^Copy of ([^<>&|]+)\s*[<>&|]+\s*Telnyx',  # "Company <> Telnyx"
            r'^Copy of Telnyx\s*[<>&|]+\s*([^-]+)',      # "Telnyx <> Company"  
            r'^Copy of Telnyx\s*//\s*([^-]+)',           # "Telnyx // Company" (NEW)
            r'^Copy of ([^/]+)\s*/\s*Telnyx',            # "Company / Telnyx"
            r'^Copy of (.+?)\s+and\s+\w+:',              # "Company and Person:"
            r'^Copy of (.+?)\s+-\s+.*Notes by Gemini',   # Extract before date
        ]"""

# Apply fixes
content = content.replace(old_ae_list, new_ae_list)
content = content.replace(old_patterns, new_patterns)

# Write back
with open('V1_GOOGLE_DRIVE_ENHANCED.py', 'w') as f:
    f.write(content)

print("✅ Applied fixes:")
print("   1. Added 'austin lazarus' and 'chris cho' to Telnyx AE list")  
print("   2. Added pattern for 'Telnyx // Company' format")
print("   3. Updated V1_GOOGLE_DRIVE_ENHANCED.py")
