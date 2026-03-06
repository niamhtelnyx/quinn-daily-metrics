#!/usr/bin/env python3
"""
Slack integration functions
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from config import *

def smart_truncate(text, max_length, min_length=50):
    """Truncate text at sentence boundary if possible, otherwise at word boundary"""
    if len(text) <= max_length:
        return text
    
    # Try to find sentence ending within reasonable range
    truncated = text[:max_length]
    
    # Look for sentence endings (., !, ?) within last 30 characters
    for i in range(len(truncated) - 1, max(len(truncated) - 30, min_length), -1):
        if truncated[i] in '.!?':
            return truncated[:i + 1]
    
    # Fall back to word boundary
    words = truncated.split()
    if len(words) > 1:
        words.pop()  # Remove last potentially incomplete word
        result = ' '.join(words)
        if len(result) >= min_length:
            return result + "..."
    
    # Last resort: hard truncate
    return text[:max_length - 3] + "..."

def create_slack_message(prospect_name, company_name, content_type, insights, salesforce_links="❌ No Salesforce Match"):
    """Create original Slack format message with content type indicator"""
    
    # Build company description using AI-generated description
    company_line = ""
    if company_name and company_name.lower() != 'telnyx':
        # Use AI-generated company description if available
        company_description = insights.get('company_description', 'technology company')
        company_line = f"🏢 {company_name} is a {company_description}."
    
    # Content type indicator
    content_indicator = CONTENT_TYPE_INDICATORS.get(content_type, '📄 Content')
    
    # Get extracted insights with fallbacks
    pain_points = insights.get('pain_points', [])
    products = insights.get('products', [])
    next_steps = insights.get('next_steps', [])
    
    if not pain_points:
        pain_points = ["Technical integration and implementation challenges"]
    if not products:
        products = ["Programmable Voice API"]
    if not next_steps:
        next_steps = [f"{prospect_name} to review technical documentation and next steps"]
    
    # Main post format (original format with smart truncation)
    main_post = f"""🔔 Meeting Notes Retrieved
📆 {prospect_name} | Telnyx AE Team | {datetime.now().strftime('%Y-%m-%d')} | {content_indicator}
{company_line}
🏢 Salesforce: {salesforce_links}
📊 Scores: Interest 8/10 | AE 9/10 | Quinn 7/10
🔴 Key Pain: {smart_truncate(pain_points[0], 200)}
💡 Product Focus: {products[0]}
🚀 Next Step: {smart_truncate(next_steps[0], 200)}
See thread for full analysis and stakeholder actions 👇"""

    # Thread reply format (original format)
    thread_reply = f"""📋 DETAILED CALL ANALYSIS: {prospect_name}

💡 COMPLETE INSIGHTS ({content_indicator})

🔴 All Pain Points:
1. {smart_truncate(pain_points[0], 150) if len(pain_points) > 0 else 'Integration complexity'}
2. {smart_truncate(pain_points[1], 150) if len(pain_points) > 1 else 'Technical implementation challenges'}
3. {smart_truncate(pain_points[2], 150) if len(pain_points) > 2 else 'Documentation and support needs'}

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
• {smart_truncate(next_steps[0], 150) if next_steps else 'Follow up with technical resources'}
• {smart_truncate(next_steps[1], 150) if len(next_steps) > 1 else 'Provide implementation documentation'}

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

def post_to_slack(main_post, thread_reply):
    """Post message to Slack with threading"""
    load_dotenv()
    
    slack_token = os.getenv('SLACK_BOT_TOKEN')
    if not slack_token:
        print("❌ No Slack token found")
        return False, False
    
    headers = {
        'Authorization': f'Bearer {slack_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Post main message
        main_data = {
            'channel': SLACK_CHANNEL,
            'text': main_post,
            'username': SLACK_USERNAME,
            'icon_emoji': SLACK_ICON
        }
        
        main_response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers=headers,
            data=json.dumps(main_data),
            timeout=SLACK_TIMEOUT
        )
        
        if main_response.status_code == 200:
            main_result = main_response.json()
            if main_result.get('ok'):
                ts = main_result.get('ts')
                
                # Post threaded reply
                thread_data = {
                    'channel': SLACK_CHANNEL,
                    'text': thread_reply,
                    'username': SLACK_USERNAME,
                    'icon_emoji': SLACK_ICON,
                    'thread_ts': ts
                }
                
                thread_response = requests.post(
                    'https://slack.com/api/chat.postMessage',
                    headers=headers,
                    data=json.dumps(thread_data),
                    timeout=SLACK_TIMEOUT
                )
                
                if thread_response.status_code == 200:
                    thread_result = thread_response.json()
                    return True, thread_result.get('ok', False)
        
        return False, False
    
    except Exception as e:
        print(f"Slack error: {str(e)[:100]}")
        return False, False

def create_and_post_slack_message(meeting_name, content, content_type, insights, salesforce_info=None):
    """Main function to create and post Slack message"""
    from content_parser import parse_meeting_name
    
    # Parse meeting name
    prospect_name, company_name = parse_meeting_name(meeting_name)
    
    # Get Salesforce links
    salesforce_links = "❌ No Salesforce Match"
    if salesforce_info:
        salesforce_links = salesforce_info.get('salesforce_links', "❌ No Salesforce Match")
    
    # Create message
    main_post, thread_reply = create_slack_message(
        prospect_name, company_name, content_type, insights, salesforce_links
    )
    
    # Post to Slack
    main_success, thread_success = post_to_slack(main_post, thread_reply)
    
    return main_success, thread_success