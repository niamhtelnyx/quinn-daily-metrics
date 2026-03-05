#!/usr/bin/env python3
"""
V1 Enhanced Call Intelligence - USEFUL SLACK MESSAGES
Actually extracts and formats meaningful meeting content for Slack
"""

import subprocess
import time
import sqlite3
import requests
import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv

def run_gog_command(command, timeout=30):
    """Run gog command with timeout"""
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return None
    except:
        return None

def extract_meeting_insights(content, meeting_name):
    """Extract useful information from meeting content"""
    if not content or len(content) < 100:
        return None
    
    insights = {
        'attendees': [],
        'key_topics': [],
        'next_steps': [],
        'company_mentioned': None,
        'meeting_type': 'Unknown'
    }
    
    # Extract attendees (simple pattern matching)
    attendee_patterns = [
        r'(?:Attendees?|Participants?)[:\s]*([^\n]+)',
        r'Present[:\s]*([^\n]+)',
        r'(?:with|and)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
    ]
    
    for pattern in attendee_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            if len(match.strip()) > 3 and len(match.strip()) < 100:
                insights['attendees'].append(match.strip())
    
    # Extract company from meeting name or content
    if 'Telnyx' in meeting_name:
        # Extract the other company
        parts = meeting_name.split('-')
        for part in parts:
            clean_part = part.strip()
            if clean_part and clean_part != 'Telnyx' and len(clean_part) > 2:
                insights['company_mentioned'] = clean_part
                break
    
    # Determine meeting type
    if any(word in meeting_name.lower() for word in ['intro', 'introduction']):
        insights['meeting_type'] = 'Introduction Call'
    elif any(word in meeting_name.lower() for word in ['demo', 'demonstration']):
        insights['meeting_type'] = 'Product Demo'
    elif any(word in meeting_name.lower() for word in ['sync', 'standup', 'check-in']):
        insights['meeting_type'] = 'Sync Meeting'
    elif any(word in meeting_name.lower() for word in ['partnership', 'partner']):
        insights['meeting_type'] = 'Partnership Discussion'
    
    # Extract key topics (look for bullet points or action items)
    topic_patterns = [
        r'(?:•|-)([^\n]+)',
        r'(?:discussed|talked about|covered)[:\s]*([^\n]+)',
        r'(?:Key points?|Topics?)[:\s]*([^\n]+)',
    ]
    
    for pattern in topic_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches[:3]:  # Limit to 3 topics
            clean_topic = match.strip()
            if len(clean_topic) > 10 and len(clean_topic) < 150:
                insights['key_topics'].append(clean_topic)
    
    # Extract next steps or action items
    next_step_patterns = [
        r'(?:Next steps?|Action items?|Follow[- ]up)[:\s]*([^\n]+)',
        r'(?:TODO|To do)[:\s]*([^\n]+)',
    ]
    
    for pattern in next_step_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches[:2]:  # Limit to 2 next steps
            clean_step = match.strip()
            if len(clean_step) > 5 and len(clean_step) < 150:
                insights['next_steps'].append(clean_step)
    
    return insights

def format_useful_slack_message(meeting_name, content_type, content, insights):
    """Format a genuinely useful Slack message"""
    
    # Start with basic info
    message_parts = [
        f"🔔 *{meeting_name}*",
        f"📄 *Source*: {content_type.title()} notes"
    ]
    
    # Add company if identified
    if insights and insights['company_mentioned']:
        message_parts.append(f"🏢 *Company*: {insights['company_mentioned']}")
    
    # Add meeting type
    if insights and insights['meeting_type'] != 'Unknown':
        message_parts.append(f"📋 *Type*: {insights['meeting_type']}")
    
    # Add attendees if found
    if insights and insights['attendees']:
        attendees_text = ", ".join(insights['attendees'][:3])  # Max 3 attendees
        message_parts.append(f"👥 *Attendees*: {attendees_text}")
    
    # Add key topics if found
    if insights and insights['key_topics']:
        message_parts.append("\n*📝 Key Topics:*")
        for i, topic in enumerate(insights['key_topics'][:3], 1):
            message_parts.append(f"• {topic}")
    
    # Add next steps if found
    if insights and insights['next_steps']:
        message_parts.append("\n*⚡ Next Steps:*")
        for i, step in enumerate(insights['next_steps'][:2], 1):
            message_parts.append(f"• {step}")
    
    # If no structured info found, show content preview
    if not insights or (not insights['key_topics'] and not insights['next_steps']):
        # Clean up the content preview
        clean_content = content.replace('/Users/niamhcollins/Library/Application Support/gogcli/drive-downloads/', '')
        clean_content = re.sub(r'[A-Za-z0-9_-]{30,}', '[file]', clean_content)  # Remove long IDs
        clean_content = clean_content[:200] + "..." if len(clean_content) > 200 else clean_content
        
        if clean_content.strip() and not clean_content.startswith('path'):
            message_parts.append(f"\n*💬 Summary:*\n{clean_content}")
    
    return "\n".join(message_parts)

def find_meeting_content(meeting_folder_id, meeting_name):
    """Find and extract actual content from meeting folder"""
    contents_output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', meeting_folder_id,
        '--max', '10',
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not contents_output:
        return None, None, None
    
    lines = contents_output.strip().split('\n')
    
    for line in lines:
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2:
                file_id = parts[0]
                file_name = parts[1]
                
                # Look for Gemini notes or transcript
                if 'Notes by Gemini' in file_name or 'Chat.txt' in file_name:
                    # Download the actual content
                    content = run_gog_command([
                        'gog', 'drive', 'download',
                        file_id,
                        '--format', 'txt',
                        '--account', 'niamh@telnyx.com'
                    ])
                    
                    if content and len(content.strip()) > 50:
                        content_type = 'transcript' if 'Chat.txt' in file_name else 'gemini'
                        return file_id, content_type, content
    
    return None, None, None

def post_useful_slack_message(meeting_name, content_type, content):
    """Post actually useful message to Slack"""
    load_dotenv()
    
    slack_token = os.getenv('SLACK_BOT_TOKEN')
    if not slack_token:
        return False
    
    # Extract insights from content
    insights = extract_meeting_insights(content, meeting_name)
    
    # Format useful message
    message = format_useful_slack_message(meeting_name, content_type, content, insights)
    
    # Post to Slack
    try:
        headers = {
            'Authorization': f'Bearer {slack_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'channel': '#sales-calls',
            'text': message,
            'username': 'Call Intelligence',
            'icon_emoji': ':telephone_receiver:'
        }
        
        response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers=headers,
            data=json.dumps(data),
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('ok', False)
        else:
            return False
    
    except Exception as e:
        print(f"Slack error: {str(e)[:100]}")
        return False

def process_todays_meetings():
    """Process meetings with useful Slack messages"""
    load_dotenv()
    today = datetime.now().strftime("%Y-%m-%d")
    today_folder_id = "1ZM-jMW-E4su9gVbSAHcjjZHPhiR3A_9M"
    
    print(f"📅 Processing: {today}")
    
    # Database
    db_path = 'v1_useful_slack.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dedup_key TEXT UNIQUE,
            meeting_folder_id TEXT,
            event_name TEXT,
            content_type TEXT,
            slack_posted BOOLEAN,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    
    # Get meetings
    meeting_folders_output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', today_folder_id,
        '--max', '25',
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not meeting_folders_output:
        print("❌ No meetings found")
        conn.close()
        return {'processed': 0, 'posted': 0}
    
    # Parse folders
    meeting_folders = []
    lines = meeting_folders_output.strip().split('\n')
    for line in lines:
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 3 and parts[2] == 'folder':
                meeting_folders.append({
                    'id': parts[0],
                    'name': parts[1]
                })
    
    print(f"📋 Found: {len(meeting_folders)} meetings")
    
    # Process each meeting
    processed = 0
    posted = 0
    
    for meeting in meeting_folders:
        meeting_name = meeting['name']
        dedup_key = f"{meeting_name.lower().replace(' ', '_')}_{today}"
        
        # Skip if processed
        cursor.execute('SELECT id FROM processed_calls WHERE dedup_key = ?', (dedup_key,))
        if cursor.fetchone():
            continue
        
        print(f"\n🎯 {meeting_name}")
        
        # Get content
        file_id, content_type, content = find_meeting_content(meeting['id'], meeting_name)
        
        if content:
            print(f"  📄 Content: {len(content)} chars ({content_type})")
            
            # Post useful Slack message
            slack_success = post_useful_slack_message(meeting_name, content_type, content)
            
            if slack_success:
                print(f"  📱 Posted to Slack")
                posted += 1
            else:
                print(f"  ❌ Slack failed")
            
            # Save to database
            cursor.execute('''
                INSERT OR IGNORE INTO processed_calls 
                (dedup_key, meeting_folder_id, event_name, content_type, slack_posted) 
                VALUES (?, ?, ?, ?, ?)
            ''', (dedup_key, meeting['id'], meeting_name, content_type, slack_success))
            conn.commit()
            
            processed += 1
        else:
            print(f"  ❌ No content found")
        
        time.sleep(0.3)
    
    conn.close()
    
    print(f"\n📊 Summary: {processed} processed, {posted} posted to Slack")
    return {'processed': processed, 'posted': posted}

def main():
    print("🔔 V1 Enhanced Call Intelligence - USEFUL SLACK MESSAGES")
    print("=" * 60)
    
    try:
        result = process_todays_meetings()
        print(f"✅ Completed: {result}")
        return result
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {'processed': 0, 'posted': 0}

if __name__ == "__main__":
    main()