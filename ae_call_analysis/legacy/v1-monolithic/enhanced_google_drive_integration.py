#!/usr/bin/env python3
"""
Enhanced Google Drive Integration Module
More flexible parsing that extracts attendee info from document content
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

def get_google_drive_calls(days_back=0, include_all_gemini=True):
    """Get Google Meet recordings from Drive - more flexible search"""
    # Get target date for filtering 
    target_date = datetime.now() - timedelta(days=days_back)
    date_str = target_date.strftime('%Y-%m-%d')
    
    try:
        # More flexible search pattern to catch all Gemini notes
        if include_all_gemini:
            # Search for any document with "Notes by Gemini" or just "Gemini" 
            search_patterns = [
                '"Notes by Gemini"',
                '"- Notes by Gemini"', 
                'Gemini'
            ]
        else:
            # Original strict pattern
            search_patterns = ['"Copy of * - Notes by Gemini"']
        
        all_calls = []
        
        for pattern in search_patterns:
            output, error = run_gog_command(f'gog drive search {pattern} --max 50')
            
            if error:
                continue  # Try next pattern
            
            if not output or 'ID' not in output:
                continue
            
            # Parse drive search output
            lines = output.strip().split('\n')
            
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
                    modified_parts = parts[-2:]  # Last 2 parts are date and time
                    modified_date = ' '.join(modified_parts)
                    
                    # Everything between doc_id and TYPE is the filename
                    filename_parts = parts[1:-4]
                    filename = ' '.join(filename_parts)
                    
                    # More flexible filtering - any file with "Gemini" or meeting-like names
                    is_gemini_call = any([
                        'gemini' in filename.lower(),
                        'notes by gemini' in filename.lower(),
                        'meeting' in filename.lower() and any(char in filename for char in ['@', '&', '<>', 'and']),
                        # Also catch files that just have names and dates
                        bool(re.search(r'\d{4}/\d{2}/\d{2}', filename))
                    ])
                    
                    # Filter for target date and Gemini-related content
                    if (modified_date.startswith(date_str) and is_gemini_call):
                        # Avoid duplicates
                        if not any(call['id'] == doc_id for call in all_calls):
                            all_calls.append({
                                'id': doc_id,
                                'title': filename.replace(' file', ''),  # Clean up filename
                                'modified_date': modified_date
                            })
        
        return all_calls, f"Found {len(all_calls)} Google Drive calls from {date_str} (flexible search)"
        
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

def extract_attendees_from_content(content):
    """Extract attendee information from Gemini document content"""
    attendees = {
        'prospect_emails': [],
        'prospect_names': [],
        'ae_names': [],
        'all_attendees': []
    }
    
    try:
        # Extract emails from content
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, content, re.IGNORECASE)
        
        # Remove duplicates and common non-prospect emails
        filtered_emails = []
        exclude_domains = ['telnyx.com', 'fellow.app', 'zoom.us', 'google.com']
        
        for email in emails:
            if email.lower() not in [e.lower() for e in filtered_emails]:
                if not any(domain in email.lower() for domain in exclude_domains):
                    filtered_emails.append(email)
        
        attendees['prospect_emails'] = filtered_emails
        
        # Extract names from Summary and Details sections
        # Look for patterns like "John Smith of Company" or "Jane Doe from ABC Corp"
        name_patterns = [
            r'(\w+\s+\w+)\s+of\s+([A-Z][A-Za-z\s]+)',           # "John Smith of Company"
            r'(\w+\s+\w+)\s+from\s+([A-Z][A-Za-z\s]+)',         # "Jane Doe from ABC"  
            r'(\w+\s+\w+)\s+at\s+([A-Z][A-Za-z\s]+)',           # "Bob Wilson at TechCorp"
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s+(?:and|,))',      # "Ryan Simkins and" or "Sarah Johnson,"
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:initiated|confirmed|explained|noted|stated)', # "John Doe stated"
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    name = match[0].strip()
                else:
                    name = match.strip()
                
                if name and len(name.split()) == 2:  # First and last name
                    # Check if this looks like a Telnyx employee (AE)
                    telnyx_indicators = ['tel next', 'telnyx', 'account executive', 'solutions engineer']
                    context_around_name = content[max(0, content.find(name)-100):content.find(name)+200].lower()
                    
                    if any(indicator in context_around_name for indicator in telnyx_indicators):
                        if name not in attendees['ae_names']:
                            attendees['ae_names'].append(name)
                    else:
                        if name not in attendees['prospect_names']:
                            attendees['prospect_names'].append(name)
                    
                    if name not in attendees['all_attendees']:
                        attendees['all_attendees'].append(name)
        
        # Also extract from title if available
        title_match = content.split('\n')[0] if content else ""
        title_email = re.findall(email_pattern, title_match)
        for email in title_email:
            if email not in attendees['prospect_emails']:
                attendees['prospect_emails'].append(email)
        
        return attendees
        
    except Exception as e:
        log_message(f"   ⚠️ Error extracting attendees: {e}")
        return attendees

def parse_enhanced_google_call_data(call_data, content):
    """Enhanced parsing using document content instead of just filename"""
    
    # Extract attendees from document content
    attendees = extract_attendees_from_content(content)
    
    # Determine prospect (prioritize email, fall back to first prospect name)
    prospect_identifier = ""
    prospect_email = ""
    
    if attendees['prospect_emails']:
        prospect_email = attendees['prospect_emails'][0]  # Use first email
        prospect_identifier = prospect_email
    elif attendees['prospect_names']:
        prospect_identifier = attendees['prospect_names'][0]  # Use first prospect name
    
    # If still no prospect found, try filename parsing as fallback
    if not prospect_identifier:
        title = call_data.get('title', '')
        # Try to extract from title
        email_in_title = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', title)
        if email_in_title:
            prospect_email = email_in_title[0]
            prospect_identifier = prospect_email
        else:
            # Last resort - use filename
            prospect_identifier = title.split(' ')[0] if title else "Unknown"
    
    # Determine AE (use first AE found, or extract from content)
    ae_name = attendees['ae_names'][0] if attendees['ae_names'] else "Unknown"
    
    # If no AE found in content, try filename patterns
    if ae_name == "Unknown":
        title = call_data.get('title', '')
        # Look for patterns like "Name and AE:" or "email and AE:"
        ae_patterns = [
            r'and\s+([A-Z][a-z]+):',           # "and Ryan:"
            r'and\s+([A-Z][a-z]+)\s',          # "and Rob "
            r'<>\s+([A-Z][a-z]+)',             # "<> Ryan"
        ]
        
        for pattern in ae_patterns:
            match = re.search(pattern, title)
            if match:
                ae_name = match.group(1)
                break
    
    return prospect_identifier, prospect_email, ae_name, attendees

def format_enhanced_google_drive_call(call_data, content):
    """Enhanced formatting with flexible attendee extraction"""
    
    prospect_identifier, prospect_email, ae_name, attendees = parse_enhanced_google_call_data(call_data, content)
    
    # Extract meeting insights from content
    insights = extract_meeting_insights(content, prospect_identifier, ae_name)
    
    # Enhanced formatted call data
    formatted_call = {
        'id': call_data['id'],
        'title': call_data['title'], 
        'prospect_name': prospect_identifier,
        'prospect_email': prospect_email,
        'ae_name': ae_name,
        'created_at': call_data.get('modified_date', ''),
        'source': 'google_drive',
        'content': content,
        'insights': insights,
        'attendees': attendees,  # Full attendee data for debugging
        # Format transcript field for compatibility with existing system
        'transcript_summary': insights['summary'],
        'transcript_details': insights['details'],
        'next_steps': insights['next_steps'],
        'full_transcript': content  # Full content for AI analysis
    }
    
    return formatted_call

def extract_meeting_insights(content, prospect_name, ae_name):
    """Extract key insights from Google Meet notes for processing"""
    
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

if __name__ == "__main__":
    # Test the enhanced Google Drive integration
    log_message("🔍 Testing Enhanced Google Drive integration...")
    
    calls, status = get_google_drive_calls(include_all_gemini=True)
    log_message(f"📞 Drive Search: {status}")
    
    if calls:
        test_call = calls[0]
        log_message(f"📄 Testing doc: {test_call['title']}")
        
        content, content_status = get_google_doc_content(test_call['id'])
        log_message(f"📝 Content: {content_status}")
        
        if content:
            formatted_call = format_enhanced_google_drive_call(test_call, content)
            log_message(f"✅ Enhanced parsing results:")
            log_message(f"   Prospect: {formatted_call['prospect_name']}")
            log_message(f"   Email: {formatted_call['prospect_email']}")
            log_message(f"   AE: {formatted_call['ae_name']}")
            log_message(f"   All attendees found: {formatted_call['attendees']['all_attendees']}")
            log_message(f"   All emails found: {formatted_call['attendees']['prospect_emails']}")
        else:
            log_message("❌ Could not retrieve document content")
    else:
        log_message("😴 No calls found for testing")