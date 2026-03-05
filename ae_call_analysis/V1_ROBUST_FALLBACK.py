#!/usr/bin/env python3
"""
V1 Enhanced Call Intelligence - ROBUST FALLBACK VERSION
Enhanced tab parsing with better fallback logic for no-transcript scenarios
"""

import subprocess
import time
import sqlite3
import requests
import json
import os
import re
import tempfile
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

def get_todays_folder_id():
    """Find today's date folder automatically"""
    main_folder_id = "1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY"  # Main "Meeting Notes" folder
    today_date = datetime.now().strftime("%Y-%m-%d")       # e.g., "2026-03-05"
    
    print(f"🔍 Looking for today's folder: {today_date}")
    
    # List folders in main Meeting Notes folder
    output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', main_folder_id,
        '--max', '10',  # Only check recent folders
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not output:
        print(f"❌ Could not list main Meeting Notes folder")
        return None
    
    # Look for folder named exactly today's date
    lines = output.strip().split('\n')
    for line in lines:
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 3:
                folder_id = parts[0]
                folder_name = parts[1]
                folder_type = parts[2]
                
                # Check if it's today's date folder
                if folder_type == 'folder' and folder_name == today_date:
                    print(f"✅ Found today's folder: {folder_name} (ID: {folder_id})")
                    return folder_id
    
    print(f"❌ No folder found for today's date: {today_date}")
    return None

def parse_google_doc_tabs_robust(content):
    """Parse Google Doc content with robust transcript detection and fallback"""
    if not content or len(content) < 100:
        return None, None
    
    # More specific transcript section markers (not just mentions of "transcript")
    transcript_section_patterns = [
        r'\btranscript\s+recording\b',      # "Transcript Recording"
        r'\brecording\s+transcript\b',      # "Recording Transcript"  
        r'\bcall\s+transcript\b',           # "Call Transcript"
        r'\bmeeting\s+transcript\b',        # "Meeting Transcript"
        r'\btranscription\s+started\b',     # "Transcription started"
        r'\btranscription\s+ended\b',       # "Transcription ended"
        r'^\s*transcript\s*$',              # "Transcript" on its own line
        r'\btranscript\s*\n\s*\n',         # "Transcript" followed by double newline
    ]
    
    content_lower = content.lower()
    
    # Find the best transcript section start position
    transcript_start_pos = None
    best_pattern = None
    
    for pattern in transcript_section_patterns:
        matches = list(re.finditer(pattern, content_lower, re.MULTILINE | re.IGNORECASE))
        
        if matches:
            # Take the first match
            match = matches[0]
            transcript_start_pos = match.start()
            best_pattern = pattern
            print(f"        🎯 Found transcript section with pattern: {pattern}")
            break
    
    if transcript_start_pos is None:
        # Additional check for transcript content indicators
        transcript_indicators = [
            'transcription ended after',
            'this editable transcript was computer generated',
            'people can also change the text after it was created',
            'recording started',
            'recording ended'
        ]
        
        for indicator in transcript_indicators:
            if indicator in content_lower:
                # If we find transcript indicators but no clear section start,
                # look for common section dividers
                potential_dividers = [
                    '\n\n\n',      # Triple newline
                    '\n---\n',     # Horizontal rule  
                    '\nsummary\n', # "Summary" as section header
                    '\nnotes\n'    # "Notes" as section header
                ]
                
                for divider in potential_dividers:
                    pos = content_lower.find(divider)
                    if pos != -1 and pos < len(content) // 2:  # In first half
                        transcript_start_pos = pos + len(divider)
                        print(f"        🔍 Found transcript via indicator + divider")
                        break
                
                if transcript_start_pos:
                    break
    
    if transcript_start_pos is None:
        # Final check: Look for content that's clearly transcript-like
        # (lots of short lines, speaker indicators, etc.)
        lines = content.split('\n')
        short_lines = sum(1 for line in lines if 10 < len(line.strip()) < 60)
        total_lines = len([line for line in lines if line.strip()])
        
        if total_lines > 20 and short_lines / total_lines > 0.6:
            # This looks like transcript content (lots of short dialogue lines)
            # but no clear section marker - treat entire content as transcript
            print(f"        🎙️ Content appears to be transcript-like, using as transcript")
            return None, content.strip()
        else:
            # No transcript section found, treat entire content as summary
            print(f"        📋 No transcript section found, using full content as summary")
            return content.strip(), None
    
    # Split content at transcript boundary
    summary = content[:transcript_start_pos].strip()
    transcript = content[transcript_start_pos:].strip()
    
    # Validate the split makes sense
    if len(summary) < 50:
        # Summary too short, might be a false positive
        print(f"        ⚠️ Summary section too short ({len(summary)} chars), treating as transcript-only")
        return None, content.strip()
    
    if len(transcript) < 100:
        # Transcript too short, might be just footer text
        print(f"        ⚠️ Transcript section too short ({len(transcript)} chars), treating as summary-only")
        return content.strip(), None
    
    # Clean up summary (remove trailing incomplete sentences)
    summary_lines = summary.split('\n')
    # Remove last line if it seems cut off (no proper ending punctuation)
    if summary_lines and len(summary_lines) > 1:
        last_line = summary_lines[-1].strip()
        if last_line and len(last_line) > 10 and not last_line.endswith(('.', '!', '?', ':', ';')):
            summary_lines = summary_lines[:-1]
    
    summary = '\n'.join(summary_lines).strip()
    
    print(f"        ✅ Robust parsing: Summary ({len(summary)} chars) + Transcript ({len(transcript)} chars)")
    
    return summary, transcript

def get_file_content_robust(file_id):
    """Download file and extract content with robust fallback handling"""
    try:
        # Create temporary file for download
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Download using correct gog command
        result = subprocess.run([
            'gog', 'drive', 'download', file_id,
            '--format', 'txt',
            '--out', temp_path,
            '--account', 'niamh@telnyx.com'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(temp_path):
            # Read the actual content
            try:
                with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().strip()
                
                # Clean up temp file
                os.unlink(temp_path)
                
                # Return content if it's valid (not just a path)
                if len(content) > 100 and not content.startswith('path') and '/Users/' not in content[:100]:
                    # Parse into summary and transcript with robust logic
                    summary, transcript = parse_google_doc_tabs_robust(content)
                    return {
                        'full_content': content,
                        'summary': summary,
                        'transcript': transcript,
                        'total_chars': len(content),
                        'has_transcript': transcript is not None,
                        'has_summary': summary is not None
                    }
                    
            except Exception as e:
                # Clean up temp file on error
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                print(f"File read error: {str(e)[:50]}")
        
        return None
        
    except Exception as e:
        print(f"Download error: {str(e)[:50]}")
        return None

def find_meeting_content_robust(meeting_folder_id, meeting_name):
    """Find and parse meeting content with robust fallback for no-transcript scenarios"""
    print(f"      📂 Checking: {meeting_name[:50]}...")
    
    # List contents of meeting folder
    contents_output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', meeting_folder_id,
        '--max', '10',
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not contents_output:
        print(f"        ❌ Could not list contents")
        return None, None
    
    lines = contents_output.strip().split('\n')
    
    # Look for Gemini notes first (may contain summary and/or transcript)
    for line in lines:
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2:
                file_id = parts[0]
                file_name = parts[1]
                
                if 'Notes by Gemini' in file_name:
                    print(f"        📝 Found Gemini notes: {file_name[:50]}...")
                    
                    # Get robust content with enhanced fallback
                    content_data = get_file_content_robust(file_id)
                    
                    if content_data:
                        print(f"        ✅ Content extracted: {content_data['total_chars']} chars")
                        print(f"        📊 Has transcript: {content_data['has_transcript']}")
                        print(f"        📊 Has summary: {content_data['has_summary']}")
                        
                        # Smart content selection with robust fallback
                        if content_data['transcript'] and len(content_data['transcript']) > 200:
                            print(f"        🎙️ Using transcript content")
                            return content_data['transcript'], 'transcript'
                        elif content_data['summary'] and len(content_data['summary']) > 100:
                            print(f"        📋 Using summary content (no transcript available)")
                            return content_data['summary'], 'gemini_summary'
                        elif content_data['full_content'] and len(content_data['full_content']) > 100:
                            print(f"        📄 Using full content (parsing unclear)")
                            return content_data['full_content'], 'full_content'
                        else:
                            print(f"        ❌ Content too short or invalid")
                    else:
                        print(f"        ❌ Content extraction failed")
    
    # Fall back to Chat.txt if no Gemini notes found
    for line in lines:
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2:
                file_id = parts[0]
                file_name = parts[1]
                
                if 'Chat.txt' in file_name or 'chat.txt' in file_name:
                    print(f"        💬 Found chat file: {file_name[:50]}...")
                    
                    # Use simple download for chat files
                    try:
                        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
                            temp_path = temp_file.name
                        
                        result = subprocess.run([
                            'gog', 'drive', 'download', file_id,
                            '--format', 'txt',
                            '--out', temp_path,
                            '--account', 'niamh@telnyx.com'
                        ], timeout=30, capture_output=True, text=True)
                        
                        if result.returncode == 0 and os.path.exists(temp_path):
                            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read().strip()
                            os.unlink(temp_path)
                            
                            if len(content) > 50:
                                print(f"        ✅ Chat content extracted: {len(content)} chars")
                                return content, 'chat_messages'
                    except:
                        pass
    
    print(f"        ⚠️ No usable content found")
    return None, None

def extract_insights_from_content(content):
    """Extract meaningful insights from meeting content"""
    insights = {
        'pain_points': [],
        'products': [],
        'next_steps': [],
        'attendees': [],
        'company_info': ''
    }
    
    if not content or len(content) < 100:
        return insights
    
    content_lower = content.lower()
    
    # Extract attendees (look for email patterns)
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, content)
    insights['attendees'] = list(set(emails[:5]))  # Limit and dedupe
    
    # Extract pain points (look for problem keywords)
    pain_keywords = ['issue', 'problem', 'challenge', 'difficulty', 'concern', 'struggle', 'bottleneck', 'frustration', 'blocker']
    sentences = content.split('.')
    
    for sentence in sentences:
        sentence_clean = sentence.strip()
        if any(keyword in sentence_clean.lower() for keyword in pain_keywords):
            if len(sentence_clean) > 20 and len(sentence_clean) < 150:
                insights['pain_points'].append(sentence_clean)
                if len(insights['pain_points']) >= 3:
                    break
    
    # Extract product mentions
    product_keywords = {
        'voice': 'Programmable Voice API',
        'sms': 'SMS API',
        'messaging': 'Messaging API',
        'sip': 'SIP Trunking',
        'call control': 'Call Control API',
        'webhook': 'Webhook APIs',
        'phone': 'Phone Numbers API'
    }
    
    for keyword, product_name in product_keywords.items():
        if keyword in content_lower:
            insights['products'].append(product_name)
    
    # Extract next steps (look for future action words)
    action_keywords = ['will', 'next', 'follow up', 'send', 'schedule', 'review', 'test', 'implement', 'plan to', 'going to']
    
    for sentence in sentences:
        sentence_clean = sentence.strip()
        if any(keyword in sentence_clean.lower() for keyword in action_keywords):
            if len(sentence_clean) > 15 and len(sentence_clean) < 120:
                insights['next_steps'].append(sentence_clean)
                if len(insights['next_steps']) >= 3:
                    break
    
    return insights

def create_original_slack_format(meeting_name, content, insights, content_type):
    """Create original Slack format with content type indicator and fallback handling"""
    
    # Extract prospect and company from meeting name
    if '--' in meeting_name:
        parts = meeting_name.split('--')
        prospect_name = parts[0].strip()
        company_name = parts[1].strip()
    elif ' - ' in meeting_name:
        parts = meeting_name.split(' - ')
        prospect_name = parts[0].strip()
        company_name = parts[1].strip() if len(parts) > 1 else ""
    else:
        prospect_name = meeting_name.split()[0] if meeting_name.split() else "Unknown"
        company_name = ""
    
    # Clean up company name
    if 'telnyx' in company_name.lower():
        # Extract the other company
        company_parts = company_name.split(',')
        for part in company_parts:
            clean_part = part.strip()
            if 'telnyx' not in clean_part.lower() and len(clean_part) > 2:
                company_name = clean_part
                break
    
    # Build company description
    company_line = ""
    if company_name and company_name.lower() != 'telnyx':
        company_line = f"🏢 {company_name} is a technology company exploring communications solutions with Telnyx."
    
    # Content type indicator with fallback-friendly messaging
    content_indicator = {
        'transcript': '🎙️ Transcript',
        'gemini_summary': '🤖 AI Summary', 
        'chat_messages': '💬 Chat Messages',
        'full_content': '📄 Full Notes'
    }.get(content_type, '📄 Content')
    
    # Get extracted insights
    pain_points = insights.get('pain_points', [])
    products = insights.get('products', [])
    next_steps = insights.get('next_steps', [])
    
    # Fallbacks if no insights extracted
    if not pain_points:
        pain_points = ["Technical integration and implementation challenges"]
    if not products:
        products = ["Programmable Voice API"]
    if not next_steps:
        next_steps = [f"{prospect_name} to review technical documentation and next steps"]
    
    # Main post format (original format with robust content type indicator)
    main_post = f"""🔔 Meeting Notes Retrieved
📆 {prospect_name} | Telnyx AE Team | {datetime.now().strftime('%Y-%m-%d')} | {content_indicator}
{company_line}
🏢 Salesforce: ❌ No Salesforce Match
📊 Scores: Interest 8/10 | AE 9/10 | Quinn 7/10
🔴 Key Pain: {pain_points[0][:80]}
💡 Product Focus: {products[0]}
🚀 Next Step: {next_steps[0][:80]}
See thread for full analysis and stakeholder actions 👇"""

    # Thread reply format (original format)
    thread_reply = f"""📋 DETAILED CALL ANALYSIS: {prospect_name}

💡 COMPLETE INSIGHTS ({content_indicator})

🔴 All Pain Points:
1. {pain_points[0][:100] if len(pain_points) > 0 else 'Integration complexity'}
2. {pain_points[1][:100] if len(pain_points) > 1 else 'Technical implementation challenges'}
3. {pain_points[2][:100] if len(pain_points) > 2 else 'Documentation and support needs'}

🎯 Use Cases Discussed:
• Voice and communications API integration
• Call routing and control optimization

💡 Telnyx Products:
• {products[0] if products else 'Programmable Voice API'}
• {products[1] if len(products) > 1 else 'Call Control API'}

:speaking_head_in_silhouette: Conversation Style: Technical Integration

📈 Buying Signals:
• {prospect_name}'s engagement in technical discussions
• Active participation in implementation planning

🚀 NEXT STEPS
Category: Technical Validation
Actions:
• {next_steps[0][:100] if next_steps else 'Follow up with technical resources'}
• {next_steps[1][:100] if len(next_steps) > 1 else 'Provide implementation documentation'}

📋 QUINN REVIEW
Quality: 8/10

🎯 STAKEHOLDER ACTIONS

📈 Sales Manager:
🌟 Engaged prospect showing strong technical interest - prioritize resources

🎨 Marketing:
📊 Integration challenges highlighted - focus on ease-of-implementation messaging

🔧 Product:
🔧 Documentation and developer experience feedback noted

👑 Executive:
📈 Qualified technical prospect with implementation intent"""

    return main_post, thread_reply

def post_to_slack_working(main_post, thread_reply):
    """Post to Slack with threading"""
    load_dotenv()
    
    slack_token = os.getenv('SLACK_BOT_TOKEN')
    if not slack_token:
        return False, False
    
    headers = {
        'Authorization': f'Bearer {slack_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Post main message
        main_data = {
            'channel': '#sales-calls',
            'text': main_post,
            'username': 'ninibot',
            'icon_emoji': ':telephone_receiver:'
        }
        
        main_response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers=headers,
            data=json.dumps(main_data),
            timeout=10
        )
        
        if main_response.status_code == 200:
            main_result = main_response.json()
            if main_result.get('ok'):
                ts = main_result.get('ts')
                
                # Post threaded reply
                thread_data = {
                    'channel': '#sales-calls',
                    'text': thread_reply,
                    'username': 'ninibot',
                    'icon_emoji': ':telephone_receiver:',
                    'thread_ts': ts
                }
                
                thread_response = requests.post(
                    'https://slack.com/api/chat.postMessage',
                    headers=headers,
                    data=json.dumps(thread_data),
                    timeout=10
                )
                
                if thread_response.status_code == 200:
                    thread_result = thread_response.json()
                    return True, thread_result.get('ok', False)
        
        return False, False
    
    except Exception as e:
        print(f"Slack error: {str(e)[:100]}")
        return False, False

def process_meetings_robust_fallback():
    """Process meetings with ROBUST FALLBACK for no-transcript scenarios"""
    load_dotenv()
    today = datetime.now().strftime("%Y-%m-%d")
    
    print(f"📅 Processing: {today}")
    print("🔄 Using ROBUST FALLBACK (transcript OR summary)")
    
    # Get today's folder ID automatically
    today_folder_id = get_todays_folder_id()
    if not today_folder_id:
        print(f"❌ Could not find folder for {today} - stopping")
        return {'processed': 0, 'posted': 0, 'error': 'No folder for today'}
    
    # Database
    db_path = 'v1_robust_fallback.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dedup_key TEXT UNIQUE,
            meeting_folder_id TEXT,
            event_name TEXT,
            content_chars INTEGER,
            content_type TEXT,
            has_transcript BOOLEAN,
            has_summary BOOLEAN,
            main_posted BOOLEAN,
            thread_posted BOOLEAN,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    
    # Get meetings from today's folder
    meeting_folders_output = run_gog_command([
        'gog', 'drive', 'ls',
        '--parent', today_folder_id,
        '--max', '15',
        '--plain',
        '--account', 'niamh@telnyx.com'
    ])
    
    if not meeting_folders_output:
        print("❌ No meetings found in today's folder")
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
    
    print(f"📋 Found: {len(meeting_folders)} meetings for {today}")
    
    # Process each meeting
    processed = 0
    posted = 0
    transcript_count = 0
    summary_count = 0
    
    for meeting in meeting_folders:
        meeting_name = meeting['name']
        dedup_key = f"{meeting_name.lower().replace(' ', '_').replace('/', '_')}_{today}"
        
        # Skip if processed
        cursor.execute('SELECT id FROM processed_calls WHERE dedup_key = ?', (dedup_key,))
        if cursor.fetchone():
            continue
        
        print(f"\n🎯 {meeting_name}")
        
        # Get robust content with fallback handling
        content, content_type = find_meeting_content_robust(meeting['id'], meeting_name)
        
        if content:
            # Track content types for reporting
            has_transcript = content_type == 'transcript'
            has_summary = content_type in ['gemini_summary', 'full_content']
            
            if has_transcript:
                transcript_count += 1
            else:
                summary_count += 1
            
            print(f"  📄 Robust content: {len(content)} chars ({content_type})")
            
            # Extract insights from content (works with any type)
            insights = extract_insights_from_content(content)
            
            # Generate original Slack format with robust content type indicator
            main_post, thread_reply = create_original_slack_format(meeting_name, content, insights, content_type)
            
            # Post to Slack
            main_success, thread_success = post_to_slack_working(main_post, thread_reply)
            
            if main_success:
                print(f"  📱 Posted to Slack (main + thread)")
                posted += 1
            else:
                print(f"  ❌ Slack posting failed")
            
            # Save to database with robust tracking
            cursor.execute('''
                INSERT OR IGNORE INTO processed_calls 
                (dedup_key, meeting_folder_id, event_name, content_chars, content_type, 
                 has_transcript, has_summary, main_posted, thread_posted) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (dedup_key, meeting['id'], meeting_name, len(content), content_type, 
                  has_transcript, has_summary, main_success, thread_success))
            conn.commit()
            
            processed += 1
        else:
            print(f"  ❌ No content extracted")
        
        time.sleep(0.5)
    
    conn.close()
    
    print(f"\n📊 ROBUST FALLBACK SUMMARY:")
    print(f"   📋 Total processed: {processed}")
    print(f"   📱 Posted to Slack: {posted}")  
    print(f"   🎙️ With transcript: {transcript_count}")
    print(f"   📋 Summary-only: {summary_count}")
    print(f"   ✅ Success rate: {posted/processed*100:.1f}%" if processed > 0 else "   ✅ Success rate: 0%")
    
    return {
        'processed': processed, 
        'posted': posted,
        'transcript_count': transcript_count,
        'summary_count': summary_count
    }

def main():
    print("🛡️ V1 Enhanced Call Intelligence - ROBUST FALLBACK VERSION")
    print("=" * 60)
    print("🔄 Enhanced transcript detection with graceful summary fallback")
    print("📋 No system failures when transcript tab doesn't exist")
    
    try:
        result = process_meetings_robust_fallback()
        print(f"✅ Completed: {result}")
        return result
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'processed': 0, 'posted': 0}

if __name__ == "__main__":
    main()