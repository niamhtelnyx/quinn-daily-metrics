#!/usr/bin/env python3
"""
Test the extract_event_name_from_google_title function
"""
import re

def extract_event_name_from_google_title(title):
    """Extract event name from: Copy of {event name} - {time} - Notes by Gemini"""
    pattern = r'^Copy of (.+?) - \d{4}/\d{2}/\d{2} .+ - Notes by Gemini'
    match = re.search(pattern, title)
    if match:
        return match.group(1).strip()
    return None

# Test with Voxtelesys title
title = "Copy of Telnyx // Voxtelesys - 2026/03/04 10:29 PST - Notes by Gemini"

print("🔍 TESTING EXTRACT FUNCTION")
print(f"Title: {title}")

event_name = extract_event_name_from_google_title(title)
print(f"Extracted: '{event_name}'")

if event_name:
    subject = "Meeting Booked: " + event_name
    print(f"SF Subject: '{subject}'")
    print(f"Should find: 'Meeting Booked: Telnyx // Voxtelesys' ✅")
else:
    print("❌ Failed to extract event name")
