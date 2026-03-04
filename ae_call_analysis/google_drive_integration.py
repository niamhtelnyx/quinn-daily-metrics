#!/usr/bin/env python3
"""
Google Drive Integration Module for AE Call Analysis
Fetches Google Meet recordings from Drive and processes them
"""

import subprocess
import json
import os
import re
from datetime import datetime, timedelta

def log_message(msg):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")

def run_gog_command(cmd):
    """Run gog CLI command and return output"""
    try:
        # Load gog environment
        env = os.environ.copy()
        env_file_path = '/Users/niamhcollins/clawd/.env.gog'
        
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#') and '=' in line:
                        key, value = line.strip().split('=', 1)
                        if key.startswith('export '):
                            key = key[7:]  # Remove 'export '
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

def get_google_drive_calls(days_back=0):
    """Get Google Meet recordings from Drive from today only (or recent days for testing)"""
    # Get target date for filtering 
    target_date = datetime.now() - timedelta(days=days_back)
    date_str = target_date.strftime('%Y-%m-%d')
    
    try:
        # Search for Google Meet recordings with Gemini notes
        output, error = run_gog_command('gog drive search "Copy of * - Notes by Gemini" --max 50')
        
        if error:
            return [], f"Drive search error: {error}"
        
        if not output or 'ID' not in output:
            return [], "No Google Meet recordings found"
        
        # Parse drive search output
        lines = output.strip().split('\n')
        calls = []
        
        for line in lines:
            if line.startswith('#') or 'ID' in line and 'NAME' in line:
                continue  # Skip header and pagination lines
                
            if not line.strip():
                continue  # Skip empty lines
                
            # More robust parsing - split on whitespace but handle filenames with spaces
            parts = line.split()
            if len(parts) >= 5:
                doc_id = parts[0]
                # Find the TYPE, SIZE, MODIFIED columns (last 3 parts)
                # Work backwards from the end
                modified_parts = parts[-2:]  # Last 2 parts are date and time
                modified_date = ' '.join(modified_parts)
                size = parts[-3]
                file_type = parts[-4] 
                
                # Everything between doc_id and TYPE is the filename
                filename_parts = parts[1:-4]
                filename = ' '.join(filename_parts)
                
                # Filter for target date calls and proper naming pattern
                # Check if modified_date starts with our target date
                if (modified_date.startswith(date_str) and 
                    'Copy of' in filename and 
                    'Notes by Gemini' in filename):
                    calls.append({
                        'id': doc_id,
                        'title': filename.replace(' file', ''),  # Clean up filename
                        'modified_date': modified_date
                    })
        
        return calls, f"Found {len(calls)} Google Drive calls from {date_str}"
        
    except Exception as e:
        return [], f"Error: {str(e)}"

def get_google_doc_content(doc_id):
    """Get content from a Google Doc"""
    try:
        output, error = run_gog_command(f'gog docs cat {doc_id}')
        
        if error:
            return None, f"Error reading doc: {error}"
        
        if not output or len(output.strip()) < 50:
            return None, "Document content too short or empty"
        
        return output.strip(), f"✅ Document content retrieved ({len(output)} chars)"
        
    except Exception as e:
        return None, f"Error: {str(e)}"

def parse_google_call_data(call_data):
    """Parse Google Meet call data to extract prospect name and AE"""
    title = call_data.get('title', '')
    
    # Parse title: "Copy of {prospect_email} and {AE}: 30-minute Meeting - {date/time} - Notes by Gemini"
    prospect_name = "Unknown"
    ae_name = "Unknown"
    
    try:
        # Extract prospect email and AE name from title
        if 'Copy of ' in title and ' and ' in title:
            # Remove "Copy of " prefix
            clean_title = title.replace('Copy of ', '')
            
            # Split on " and " to separate prospect and AE
            if ' and ' in clean_title:
                prospect_part = clean_title.split(' and ')[0].strip()
                ae_part = clean_title.split(' and ')[1].split(':')[0].strip()
                
                # Prospect part should be email, extract name
                if '@' in prospect_part:
                    # Use email as prospect identifier
                    prospect_name = prospect_part
                else:
                    prospect_name = prospect_part
                
                # AE name is straightforward
                ae_name = ae_part
        
        # If parsing failed, try to extract from title differently
        if prospect_name == "Unknown":
            # Look for email pattern in title
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', title)
            if email_match:
                prospect_name = email_match.group(1)
    
    except Exception as e:
        log_message(f"   ⚠️ Error parsing call title: {e}")
    
    return prospect_name, ae_name

def extract_meeting_insights(content, prospect_name, ae_name):
    """Extract key insights from Google Meet notes for processing"""
    
    # The content from Google Meet is already structured with:
    # - Summary section
    # - Details section  
    # - Suggested next steps
    
    insights = {
        'summary': '',
        'details': '',
        'next_steps': '',
        'full_content': content
    }
    
    try:
        # Split content into sections
        sections = content.split('\n\n')
        current_section = None
        
        for section in sections:
            section = section.strip()
            
            if section.lower().startswith('summary'):
                current_section = 'summary'
                insights['summary'] = section.replace('Summary', '').strip()
            elif section.lower().startswith('details'):
                current_section = 'details'
                insights['details'] = section.replace('Details', '').strip()
            elif 'suggested next steps' in section.lower() or 'next steps' in section.lower():
                current_section = 'next_steps'
                insights['next_steps'] = section
            elif current_section and section:
                # Continue building current section
                insights[current_section] += '\n\n' + section
    
    except Exception as e:
        log_message(f"   ⚠️ Error extracting insights: {e}")
        # Fall back to using full content as summary
        insights['summary'] = content[:1000] + "..." if len(content) > 1000 else content
    
    return insights

def format_google_drive_call_for_processing(call_data, content):
    """Format Google Drive call data for the existing AI analysis pipeline"""
    
    prospect_name, ae_name = parse_google_call_data(call_data)
    insights = extract_meeting_insights(content, prospect_name, ae_name)
    
    # Format in a way that's compatible with existing AI analysis
    formatted_call = {
        'id': call_data['id'],
        'title': call_data['title'], 
        'prospect_name': prospect_name,
        'ae_name': ae_name,
        'created_at': call_data.get('modified_date', ''),
        'source': 'google_drive',
        'content': content,
        'insights': insights,
        # Format transcript field for compatibility with existing system
        'transcript_summary': insights['summary'],
        'transcript_details': insights['details'],
        'next_steps': insights['next_steps'],
        'full_transcript': content  # Full content for AI analysis
    }
    
    return formatted_call

if __name__ == "__main__":
    # Test the Google Drive integration
    log_message("🔍 Testing Google Drive integration...")
    
    # Test with recent calls (last 3 days)
    calls = []
    for days_back in range(3):
        test_calls, status = get_google_drive_calls(days_back=days_back)
        log_message(f"📞 Drive Search (Day -{days_back}): {status}")
        if test_calls:
            calls = test_calls
            break
    
    if calls:
        test_call = calls[0]
        log_message(f"📄 Testing doc: {test_call['title']}")
        
        content, content_status = get_google_doc_content(test_call['id'])
        log_message(f"📝 Content: {content_status}")
        
        if content:
            formatted_call = format_google_drive_call_for_processing(test_call, content)
            log_message(f"✅ Formatted call for: {formatted_call['prospect_name']} with {formatted_call['ae_name']}")
            
            # Print sample of formatted data
            print(f"\nSample formatted call data:")
            print(f"ID: {formatted_call['id']}")
            print(f"Prospect: {formatted_call['prospect_name']}")
            print(f"AE: {formatted_call['ae_name']}")
            print(f"Summary: {formatted_call['transcript_summary'][:200]}...")
        else:
            log_message("❌ Could not retrieve document content")
    else:
        log_message("😴 No calls found for testing")