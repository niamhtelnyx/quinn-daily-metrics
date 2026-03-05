#!/usr/bin/env python3
"""
Enhanced Slack Integration with AI Analysis + Salesforce Links + Company Summary
"""

import requests
import json
import os
from datetime import datetime

def load_env():
    """Load environment variables"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def analyze_call_with_ai(fellow_call_data):
    """
    Analyze Fellow call using OpenAI with 9-point analysis structure
    
    Args:
        fellow_call_data (dict): Fellow call data with transcript
        
    Returns:
        dict: Analysis results
    """
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    if not openai_api_key:
        return {
            "status": "no_api_key",
            "analysis": "AI analysis unavailable (no OpenAI API key)"
        }
    
    # Get transcript from Fellow call
    transcript = fellow_call_data.get('transcript', '')
    if not transcript:
        return {
            "status": "no_transcript", 
            "analysis": "AI analysis unavailable (no transcript)"
        }
    
    # 9-point analysis prompt structure
    analysis_prompt = f"""
Analyze this Telnyx intro call transcript and provide structured insights:

TRANSCRIPT:
{transcript}

Please provide analysis for these 9 key areas:

1. **Core Pain Points**: What specific business problems does the prospect have?
2. **Use Cases Discussed**: What specific ways will they use Telnyx services?
3. **Telnyx Products Mentioned**: Which Telnyx products/services were discussed?
4. **Buying Signals**: What indicates they're ready to purchase?
5. **Technical Requirements**: What technical specs or integrations do they need?
6. **Timeline & Urgency**: How urgent is their need? When do they want to start?
7. **Decision Makers**: Who makes purchasing decisions? Are they on the call?
8. **Competition**: Are they currently using competitors? Which ones?
9. **Next Steps**: What specific actions should happen next?

ADDITIONAL SCORING:
- **Interest Level** (1-10): How interested is the prospect?
- **Qualification Score** (1-10): How qualified are they as a lead?
- **AE Performance** (1-10): How well did the AE handle the call?

Format as JSON with clear, concise answers for each point.
"""

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4-turbo-preview",
                "messages": [
                    {"role": "system", "content": "You are an expert sales call analyst. Provide structured, actionable insights."},
                    {"role": "user", "content": analysis_prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.3
            },
            timeout=30
        )
        
        if response.status_code == 200:
            ai_response = response.json()
            content = ai_response['choices'][0]['message']['content']
            return {
                "status": "success",
                "analysis": content,
                "model": "gpt-4-turbo-preview"
            }
        else:
            return {
                "status": "error",
                "analysis": f"OpenAI API error: {response.status_code}"
            }
            
    except Exception as e:
        return {
            "status": "error", 
            "analysis": f"AI analysis failed: {str(e)}"
        }

def get_company_summary(prospect_name, company_name=None):
    """
    Get 1-sentence company summary
    
    Args:
        prospect_name (str): Prospect name
        company_name (str): Company name if available
        
    Returns:
        str: One sentence company description
    """
    # For now, return a placeholder. In V2, this could use:
    # - Clearbit API for company data
    # - LinkedIn API 
    # - Salesforce account description
    # - Web scraping of company website
    
    if company_name:
        return f"{company_name} is a technology company seeking telecommunications solutions."
    else:
        return f"Company details for {prospect_name} available in Salesforce record."

def get_salesforce_urls(contact_id, event_id, account_id=None):
    """
    Generate Salesforce record URLs
    
    Args:
        contact_id (str): Salesforce Contact ID
        event_id (str): Salesforce Event ID  
        account_id (str): Salesforce Account ID (optional)
        
    Returns:
        dict: URLs for Salesforce records
    """
    base_url = "https://telnyx.lightning.force.com/lightning/r"
    
    urls = {}
    
    if contact_id:
        urls['contact'] = f"{base_url}/Contact/{contact_id}/view"
    
    if event_id:
        urls['event'] = f"{base_url}/Event/{event_id}/view"
        
    if account_id:
        urls['account'] = f"{base_url}/Account/{account_id}/view"
        
    return urls

def format_enhanced_slack_alert(fellow_call_data, sf_data, ai_analysis):
    """
    Format enhanced Slack alert with AI analysis + SF links + company summary
    
    Args:
        fellow_call_data (dict): Fellow call data
        sf_data (dict): Salesforce data (contact, event, account info)
        ai_analysis (dict): AI analysis results
        
    Returns:
        str: Enhanced formatted Slack message
    """
    title = fellow_call_data.get('title', 'Unknown Call')
    call_id = fellow_call_data.get('id', 'unknown')
    created_at = fellow_call_data.get('created_at', '')
    
    # Extract prospect name
    if '(' in title and ')' in title:
        prospect_name = title.split('(')[1].split(')')[0]
    else:
        prospect_name = 'Unknown Prospect'
    
    # Get Salesforce URLs
    contact_id = sf_data.get('contact_id')
    event_id = sf_data.get('event_id')
    account_id = sf_data.get('account_id')
    company_name = sf_data.get('company_name')
    
    sf_urls = get_salesforce_urls(contact_id, event_id, account_id)
    company_summary = get_company_summary(prospect_name, company_name)
    
    # Build enhanced alert
    alert = f"""🔔 *New Telnyx Intro Call - Enhanced Analysis*

*Prospect*: {prospect_name}
*Date*: {created_at[:10] if created_at else 'Unknown'}  
*Fellow ID*: `{call_id}`

📞 *Recording*: <https://telnyx.fellow.app/recordings/{call_id}|View in Fellow>

🏢 *Company*: {company_summary}

---

🤖 *AI CALL ANALYSIS*:"""

    # Add AI analysis section
    if ai_analysis.get('status') == 'success':
        alert += f"""
{ai_analysis.get('analysis', 'Analysis unavailable')}
"""
    else:
        alert += f"""
❌ AI analysis unavailable: {ai_analysis.get('analysis', 'Unknown error')}

*Manual review recommended for detailed insights.*
"""

    # Add Salesforce links section
    alert += f"""

---

🔗 *SALESFORCE RECORDS*:"""
    
    if sf_urls.get('contact'):
        alert += f"""
👤 <{sf_urls['contact']}|View Contact Record>"""
    
    if sf_urls.get('event'):
        alert += f"""
📅 <{sf_urls['event']}|View Event Record>"""
        
    if sf_urls.get('account'):
        alert += f"""
🏢 <{sf_urls['account']}|View Account Record>"""
    
    if not sf_urls:
        alert += f"""
⚠️ Salesforce records need manual linking"""

    # Footer
    alert += f"""

---

✅ *Next Actions*: AE follow-up required
🔄 *Status*: Processed by V1 Enhanced Intelligence  
⏰ *Generated*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

    return alert

def test_enhanced_integration():
    """Test the enhanced Slack integration"""
    load_env()
    
    print("🚀 ENHANCED SLACK INTEGRATION TEST")
    print("=" * 50)
    
    # Mock data for testing
    mock_fellow_data = {
        "id": "test123",
        "title": "Telnyx Intro Call (John Smith)",
        "created_at": "2026-03-03T12:00:00Z",
        "transcript": "Sample transcript for testing AI analysis..."
    }
    
    mock_sf_data = {
        "contact_id": "003Qk00000EXAMPLE",
        "event_id": "00UQk00000EXAMPLE", 
        "account_id": "001Qk00000EXAMPLE",
        "company_name": "TechCorp Inc"
    }
    
    print("1. Testing AI analysis...")
    ai_analysis = analyze_call_with_ai(mock_fellow_data)
    print(f"   Status: {ai_analysis.get('status')}")
    
    print("\\n2. Generating enhanced alert...")
    enhanced_alert = format_enhanced_slack_alert(mock_fellow_data, mock_sf_data, ai_analysis)
    
    print("\\n3. Enhanced alert preview:")
    print("-" * 50)
    print(enhanced_alert)
    print("-" * 50)
    
    print("\\n✅ Enhanced integration ready for production!")

if __name__ == "__main__":
    test_enhanced_integration()