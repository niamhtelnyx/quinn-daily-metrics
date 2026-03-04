#!/usr/bin/env python3
"""
Fix Salesforce event search to find "Meeting Booked: Telnyx // Voxtelesys" style events
"""

# Read current file
with open('V1_GOOGLE_DRIVE_ENHANCED.py', 'r') as f:
    content = f.read()

# Fix: Broaden Salesforce event search
old_query = """query = f"SELECT Id, Subject, Description FROM Event WHERE WhoId = '{contact_id}' AND Subject LIKE '%Telnyx Intro%' ORDER BY CreatedDate DESC LIMIT 5\""""

new_query = """query = f"SELECT Id, Subject, Description FROM Event WHERE WhoId = '{contact_id}' AND (Subject LIKE '%Telnyx%' OR Subject LIKE '%Meeting Booked%') ORDER BY CreatedDate DESC LIMIT 5\""""

# Apply fix
content = content.replace(old_query, new_query)

# Write back
with open('V1_GOOGLE_DRIVE_ENHANCED.py', 'w') as f:
    f.write(content)

print("✅ Fixed Salesforce event search:")
print("   OLD: Subject LIKE '%Telnyx Intro%'")  
print("   NEW: Subject LIKE '%Telnyx%' OR Subject LIKE '%Meeting Booked%'")
print("   Now it will find: 'Meeting Booked: Telnyx // Voxtelesys'")
