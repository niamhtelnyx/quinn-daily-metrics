#!/usr/bin/env python3
"""
Test the integrated AI analysis + company description + Slack formatting
"""

from ai_analysis_enhanced import get_ai_insights_and_company_description
from slack_functions import create_slack_message
from content_parser import parse_meeting_name

def test_complete_integration():
    """Test the full pipeline with AI analysis"""
    
    print("🧪 TESTING COMPLETE AI INTEGRATION")
    print("=" * 37)
    
    # Test meeting content
    test_content = """
    Meeting with LeadSolve team about their real estate lead generation platform.
    They're facing challenges with low conversion rates and high cost per lead.
    Their main pain points include outdated CRM integration and poor lead quality.
    They're interested in Telnyx Voice API for automated follow-up calls and SMS for lead nurturing.
    Next steps: Technical demo of Voice API and pricing discussion for high-volume usage.
    Attendees: mike@leadsolve.io, sarah.sales@leadsolve.io
    """
    
    test_meeting = "Telnyx Lead Generation Discussion -- LeadSolve"
    
    print(f"🎯 Meeting: {test_meeting}")
    print(f"📄 Content: {len(test_content)} characters")
    print()
    
    # Step 1: AI Analysis
    print("🤖 Running AI analysis...")
    insights, company_description = get_ai_insights_and_company_description(test_content, test_meeting)
    insights['company_description'] = company_description
    
    print(f"  🏢 Company: {company_description}")
    print(f"  🔴 Pain Points: {len(insights['pain_points'])}")
    print(f"  💡 Products: {len(insights['products'])}")
    print()
    
    # Step 2: Parse meeting name
    prospect_name, company_name = parse_meeting_name(test_meeting)
    print(f"📋 Parsed: {prospect_name} from {company_name}")
    print()
    
    # Step 3: Create Slack message
    print("📱 Creating Slack message...")
    main_post, thread_reply = create_slack_message(
        prospect_name, company_name, 'ai_analysis', insights, 
        'Contact | Account | Event'
    )
    
    print("📱 SLACK MAIN POST:")
    print("-" * 50)
    print(main_post)
    print("-" * 50)
    print()
    
    print("🎯 SUCCESS! AI analysis → Company description → Rich Slack post")

if __name__ == "__main__":
    test_complete_integration()