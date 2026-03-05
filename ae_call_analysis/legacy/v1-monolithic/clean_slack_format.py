#!/usr/bin/env python3
"""
Clean Slack Message Formatting for V1 Call Intelligence
"""

def format_clean_slack_alert(call_data, contact_data, event_id, ai_analysis):
    """Format clean, professional Slack alert"""
    title = call_data.get('title', 'Unknown Call')
    call_id = call_data.get('id', 'unknown')
    created_at = call_data.get('created_at', '')
    
    if '(' in title and ')' in title:
        prospect_name = title.split('(')[1].split(')')[0]
    else:
        prospect_name = 'Unknown Prospect'
    
    # Clean, professional format
    alert = f"""🔔 **New Telnyx Intro Call**

**Prospect:** {prospect_name}
**Date:** {created_at[:10] if created_at else 'Unknown'}
**Fellow ID:** {call_id}

📞 [View Recording](https://telnyx.fellow.app/recordings/{call_id})"""

    # Add company info cleanly
    if contact_data and contact_data.get('company_name'):
        company_name = contact_data['company_name']
        alert += f"\n🏢 **Company:** {company_name}"
    
    # Add AI analysis section - clean format
    if ai_analysis.get('status') == 'success':
        alert += f"\n\n**📊 CALL ANALYSIS**\n{ai_analysis['summary']}"
    else:
        alert += f"\n\n**📊 CALL ANALYSIS**\n❌ AI analysis unavailable - add OPENAI_API_KEY for insights"
    
    # Clean Salesforce links section
    if contact_data:
        alert += f"\n\n**🔗 SALESFORCE**"
        
        contact_id = contact_data['contact_id'] 
        sf_base = "https://telnyx.lightning.force.com/lightning/r"
        
        alert += f"\n• [Contact Record]({sf_base}/Contact/{contact_id}/view)"
        
        if contact_data.get('account_id'):
            account_id = contact_data['account_id']
            alert += f"\n• [Account Record]({sf_base}/Account/{account_id}/view)"
            
        if event_id:
            alert += f"\n• [Event Record]({sf_base}/Event/{event_id}/view)"
    
    # Clean footer
    alert += f"\n\n✅ **Ready for AE follow-up**"

    return alert

def test_clean_format():
    """Test the clean formatting"""
    
    # Mock data
    mock_call = {
        "id": "bw9vf7NWdh",
        "title": "Telnyx Intro Call (Trevor Abonyo)",
        "created_at": "2026-03-02T15:30:00Z"
    }
    
    mock_contact = {
        "contact_id": "003Qk00000EXAMPLE",
        "company_name": "Techpal Africa Solutions",
        "account_id": "001Qk00000EXAMPLE"
    }
    
    mock_ai = {
        "status": "no_transcript",
        "summary": "AI analysis unavailable - add OPENAI_API_KEY to .env for enhanced insights"
    }
    
    mock_event_id = "00UQk00000EXAMPLE"
    
    # Generate clean alert
    clean_alert = format_clean_slack_alert(mock_call, mock_contact, mock_event_id, mock_ai)
    
    print("🎨 CLEAN SLACK FORMAT PREVIEW:")
    print("=" * 50)
    print(clean_alert)
    print("=" * 50)
    
    return clean_alert

if __name__ == "__main__":
    test_clean_format()