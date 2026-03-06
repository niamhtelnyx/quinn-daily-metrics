#!/usr/bin/env python3
"""
AE Call Intelligence System - Main Orchestrator
Modular architecture with separate function modules
"""

import time
from dotenv import load_dotenv

# Import our modular functions
from config import *
from gog_functions import get_todays_folder_id, get_meeting_folders, extract_meeting_content
from content_parser import analyze_content_structure, select_best_content, extract_insights_from_content
from ai_analysis_enhanced import get_ai_insights_and_company_description
from sf_functions import lookup_salesforce_info
from slack_functions import create_and_post_slack_message
from database_functions import init_database, is_meeting_processed, save_processed_meeting, get_processing_stats

def process_single_meeting(meeting_info):
    """Process a single meeting through the complete pipeline"""
    meeting_name = meeting_info['name']
    meeting_folder_id = meeting_info['id']
    today_date = get_today_date()
    
    print(f"\n🎯 {meeting_name}")
    
    # Check if already processed
    if is_meeting_processed(meeting_name, today_date):
        print(f"  ⏭️ Already processed, skipping")
        return False
    
    # Step 1: Extract content from Google Drive
    raw_content, initial_type = extract_meeting_content(meeting_folder_id, meeting_name)
    if not raw_content:
        print(f"  ❌ No content extracted")
        return False
    
    # Step 2: Analyze content structure (parse tabs, etc.)
    if initial_type == 'gemini_notes':
        content_data = analyze_content_structure(raw_content)
        selected_content, content_type = select_best_content(content_data)
    else:
        # For chat files, use as-is
        content_data = {
            'full_content': raw_content,
            'summary': None,
            'transcript': None,
            'total_chars': len(raw_content),
            'has_transcript': False,
            'has_summary': False
        }
        selected_content = raw_content
        content_type = initial_type
    
    if not selected_content:
        print(f"  ❌ Content analysis failed")
        return False
    
    print(f"  📄 Content: {len(selected_content)} chars ({content_type})")
    
    # Step 3: Extract insights from content using AI analysis
    try:
        insights, company_description = get_ai_insights_and_company_description(selected_content, meeting_name)
        print(f"  🤖 AI Analysis: {len(insights['pain_points'])} pain points, {len(insights['products'])} products")
        print(f"  🏢 Company: {company_description[:60]}...")
    except Exception as e:
        print(f"  ⚠️ AI analysis failed, using fallback: {str(e)[:50]}")
        insights = extract_insights_from_content(selected_content)
        company_description = "technology company"
    
    # Add company description to insights for Slack formatting
    insights['company_description'] = company_description
    
    # Step 4: Lookup Salesforce information (optional)
    salesforce_info = None
    try:
        salesforce_info, _ = lookup_salesforce_info(meeting_name)
    except Exception as e:
        print(f"  ⚠️ Salesforce lookup error: {str(e)[:50]}")
    
    # Step 5: Create and post Slack message
    main_success, thread_success = create_and_post_slack_message(
        meeting_name, selected_content, content_type, insights, salesforce_info
    )
    
    if main_success:
        print(f"  📱 Posted to Slack (main + thread)")
    else:
        print(f"  ❌ Slack posting failed")
    
    # Step 6: Save to database
    save_processed_meeting(
        meeting_name, meeting_folder_id, content_data, content_type,
        salesforce_info, main_success, thread_success
    )
    
    return main_success

def process_todays_meetings():
    """Main processing function - orchestrates the entire pipeline"""
    load_dotenv()
    today = get_today_date()
    
    print(f"🚀 AE Call Intelligence - Modular System")
    print(f"=" * 60)
    print(f"📅 Processing: {today}")
    print(f"🔧 Using modular architecture with robust fallback")
    
    # Initialize database
    init_database()
    
    # Step 1: Get today's folder with timeout protection
    print(f"🔍 Attempting to discover today's folder...")
    today_folder_id = get_todays_folder_id()
    if not today_folder_id:
        print(f"❌ Could not find folder for {today} - Google Drive API may be hanging")
        print(f"   This is often caused by network issues or Google API rate limits")
        return {'processed': 0, 'posted': 0, 'error': 'Google Drive timeout - folder discovery failed'}
    
    # Step 2: Get meeting folders
    meeting_folders = get_meeting_folders(today_folder_id)
    if not meeting_folders:
        print("❌ No meetings found in today's folder")
        return {'processed': 0, 'posted': 0}
    
    print(f"📋 Found: {len(meeting_folders)} meetings for {today}")
    
    # Step 3: Process each meeting
    processed = 0
    posted = 0
    
    for meeting_info in meeting_folders:
        try:
            success = process_single_meeting(meeting_info)
            processed += 1
            if success:
                posted += 1
                
        except Exception as e:
            print(f"  💥 Processing error: {str(e)[:100]}")
            import traceback
            traceback.print_exc()
        
        # Small delay between meetings
        time.sleep(0.5)
    
    # Step 4: Get final statistics
    stats = get_processing_stats()
    
    print(f"\n📊 MODULAR SYSTEM SUMMARY:")
    print(f"   📋 Total processed: {processed}")
    print(f"   📱 Posted to Slack: {posted}")
    print(f"   🎙️ With transcript: {stats['transcript_count']}")
    print(f"   📋 Summary-only: {stats['summary_count']}")
    print(f"   🏢 Salesforce matches: {stats['salesforce_matches']}")
    print(f"   ✅ Success rate: {stats['success_rate']:.1f}%")
    
    return {
        'processed': processed,
        'posted': posted,
        'transcript_count': stats['transcript_count'],
        'summary_count': stats['summary_count'],
        'salesforce_matches': stats['salesforce_matches'],
        'success_rate': stats['success_rate']
    }

def run_health_check():
    """Run a quick health check of all modules"""
    print("🔍 Running system health check...")
    
    issues = []
    
    # Check Google Drive access
    try:
        from gog_functions import run_gog_command
        result = run_gog_command(['gog', '--version'], timeout=5)
        if result:
            print("  ✅ Google Drive (gog) access working")
        else:
            issues.append("❌ gog CLI not working")
    except Exception as e:
        issues.append(f"❌ Google Drive error: {str(e)[:50]}")
    
    # Check Salesforce access  
    try:
        from sf_functions import get_salesforce_token
        token = get_salesforce_token()
        if token:
            print("  ✅ Salesforce access working")
        else:
            issues.append("⚠️ Salesforce credentials missing (optional)")
    except Exception as e:
        issues.append(f"⚠️ Salesforce error: {str(e)[:50]}")
    
    # Check Slack access
    try:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        slack_token = os.getenv('SLACK_BOT_TOKEN')
        if slack_token:
            print("  ✅ Slack token found")
        else:
            issues.append("❌ Slack token missing")
    except Exception as e:
        issues.append(f"❌ Slack error: {str(e)[:50]}")
    
    # Check database
    try:
        from database_functions import init_database
        init_database()
        print("  ✅ Database access working")
    except Exception as e:
        issues.append(f"❌ Database error: {str(e)[:50]}")
    
    if issues:
        print("\n⚠️ Issues found:")
        for issue in issues:
            print(f"  {issue}")
        return False
    else:
        print("\n✅ All systems healthy!")
        return True

def main():
    """Main entry point"""
    try:
        # Run health check first
        healthy = run_health_check()
        
        if not healthy:
            print("\n⚠️ System health issues detected, but continuing...")
        
        # Run main processing
        result = process_todays_meetings()
        print(f"\n✅ Completed: {result}")
        return result
        
    except Exception as e:
        print(f"❌ System error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'processed': 0, 'posted': 0, 'error': str(e)}

if __name__ == "__main__":
    main()