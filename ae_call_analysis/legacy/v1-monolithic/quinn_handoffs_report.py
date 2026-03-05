#!/usr/bin/env python3
"""
Quinn Daily Handoffs Report
Query Salesforce for Quinn Taylor handoffs and post to Slack
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta
from collections import Counter

def log_message(message):
    """Log with timestamp"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}] {message}")

def get_salesforce_token():
    """Get Salesforce OAuth2 access token using client credentials flow"""
    try:
        client_id = os.getenv('SALESFORCE_CLIENT_ID')
        client_secret = os.getenv('SALESFORCE_CLIENT_SECRET')
        domain = os.getenv('SF_DOMAIN', 'telnyx')
        
        if not client_id or not client_secret:
            log_message("❌ Salesforce credentials missing")
            return None
            
        auth_url = f"https://{domain}.my.salesforce.com/services/oauth2/token"
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        response = requests.post(auth_url, data=data, timeout=30)
        if response.status_code == 200:
            log_message("✅ Salesforce authenticated")
            return response.json().get('access_token')
        else:
            log_message(f"❌ Salesforce auth failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        log_message(f"❌ Salesforce auth error: {str(e)}")
        return None

def query_quinn_handoffs():
    """Query Salesforce for Quinn Taylor handoffs today"""
    token = get_salesforce_token()
    if not token:
        return None
        
    domain = os.getenv('SF_DOMAIN', 'telnyx')
    instance_url = f"https://{domain}.my.salesforce.com"
    
    # Exact SOQL from the cron job
    query = """SELECT Id, Name, CreatedDate, Owner_Name__c, Owner_Email__c, Contact__c, Lead__c, Handoff_Type__c, Sales_Handoff_Reason__c 
FROM Sales_Handoff__c 
WHERE Owner_Name__c = 'Quinn Taylor' 
AND Owner_Email__c = 'quinn@telnyx.com' 
AND CreatedDate = TODAY 
ORDER BY CreatedDate DESC"""
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(
            f"{instance_url}/services/data/v57.0/query",
            params={'q': query},
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            results = response.json()
            log_message(f"✅ Query successful - {len(results.get('records', []))} handoffs found")
            return results.get('records', [])
        else:
            log_message(f"❌ Salesforce query failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        log_message(f"❌ Query error: {str(e)}")
        return None

def load_memory_data():
    """Load previous day's count for trending analysis"""
    memory_file = "/Users/niamhcollins/clawd/memory/quinn-handoffs-daily.json"
    try:
        if os.path.exists(memory_file):
            with open(memory_file, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_memory_data(data):
    """Save today's data for future trending"""
    memory_file = "/Users/niamhcollins/clawd/memory/quinn-handoffs-daily.json"
    os.makedirs(os.path.dirname(memory_file), exist_ok=True)
    
    try:
        with open(memory_file, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log_message(f"⚠️ Could not save memory data: {e}")

def analyze_handoffs(handoffs):
    """Analyze handoffs data and generate insights"""
    if not handoffs:
        return {
            'total': 0,
            'trending': "No data",
            'peak_hour': "No data",
            'top_reasons': [],
            'insights': "No handoffs today"
        }
    
    # Basic counts
    total = len(handoffs)
    
    # Hour analysis (EST/CST)
    hours = []
    for handoff in handoffs:
        try:
            # Parse ISO datetime and convert to CST
            created = datetime.fromisoformat(handoff['CreatedDate'].replace('Z', '+00:00'))
            cst_time = created.astimezone(timezone.utc).replace(tzinfo=None) - timedelta(hours=6)
            hours.append(cst_time.hour)
        except:
            pass
    
    peak_hour = "N/A"
    if hours:
        hour_counts = Counter(hours)
        peak_hour_num = hour_counts.most_common(1)[0][0]
        peak_count = hour_counts.most_common(1)[0][1]
        peak_hour = f"{peak_hour_num:02d}:00 CST ({peak_count} handoffs)"
    
    # Reason analysis
    reasons = [h.get('Sales_Handoff_Reason__c', 'Unknown') for h in handoffs if h.get('Sales_Handoff_Reason__c')]
    reason_counts = Counter(reasons)
    top_reasons = [reason for reason, count in reason_counts.most_common(3)]
    
    # Trending analysis
    memory_data = load_memory_data()
    yesterday_count = memory_data.get('yesterday_count', 0)
    
    trending = "First day"
    if yesterday_count > 0:
        change = total - yesterday_count
        if change > 0:
            pct_change = (change / yesterday_count) * 100
            trending = f"+{change} vs yesterday (+{pct_change:.0f}%)"
        elif change < 0:
            pct_change = (abs(change) / yesterday_count) * 100
            trending = f"{change} vs yesterday (-{pct_change:.0f}%)"
        else:
            trending = "No change vs yesterday"
    
    # Generate insights
    insights = []
    if total == 0:
        insights.append("No handoffs today")
    elif total >= 10:
        insights.append("High volume day")
    elif total >= 5:
        insights.append("Moderate activity")
    else:
        insights.append("Low activity")
    
    if len(set(reasons)) == 1 and total > 1:
        insights.append(f"All handoffs for same reason: {reasons[0]}")
    
    # Save today's data for tomorrow's trending
    today_data = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'yesterday_count': total,
        'updated_at': datetime.now().isoformat()
    }
    save_memory_data(today_data)
    
    return {
        'total': total,
        'trending': trending,
        'peak_hour': peak_hour,
        'top_reasons': top_reasons[:3],
        'insights': " • ".join(insights)
    }

def format_slack_message(analysis):
    """Format the Slack message with proper formatting"""
    date_str = datetime.now().strftime('%B %d, %Y')
    
    # Determine trend arrow
    arrow = ""
    if "+" in analysis['trending']:
        arrow = "📈"
    elif "-" in analysis['trending']:
        arrow = "📉"
    elif "No change" in analysis['trending']:
        arrow = "➡️"
    
    # Format top reasons
    reasons_text = ", ".join(analysis['top_reasons']) if analysis['top_reasons'] else "No data"
    
    # Alert emoji for insights
    alert_emoji = "🚨" if analysis['total'] >= 10 else "📊"
    
    message = f"""📈 *Quinn Handoffs Update - {date_str}*

• *Total Handoffs:* {analysis['total']} (24h)
• *Trending:* {analysis['trending']} {arrow}
• *Peak Hour:* {analysis['peak_hour']}
• *Top Reasons:* {reasons_text}
• *7d Average:* N/A (when available)

{alert_emoji} *Key Insights:* {analysis['insights']}

_Daily handoffs tracking • Automated at 2pm CST_"""
    
    return message

def main():
    """Main execution function"""
    log_message("🤖 Starting Quinn Daily Handoffs Report")
    
    # Source environment variables
    env_file = "/Users/niamhcollins/clawd/ae_call_analysis/.env"
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    # Query handoffs
    handoffs = query_quinn_handoffs()
    if handoffs is None:
        log_message("❌ Failed to query handoffs")
        return False
    
    # Analyze results
    analysis = analyze_handoffs(handoffs)
    
    # Format message
    message = format_slack_message(analysis)
    
    # Output for Clawdbot message tool
    print("\n" + "="*50)
    print("SLACK MESSAGE:")
    print("="*50)
    print(message)
    print("="*50)
    
    log_message(f"✅ Report generated - {analysis['total']} handoffs")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)