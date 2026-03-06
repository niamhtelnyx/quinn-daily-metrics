#!/usr/bin/env python3
"""
Configuration and constants for the AE Call Intelligence system
"""

from datetime import datetime

# Google Drive Configuration
MAIN_MEETING_NOTES_FOLDER_ID = "1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY"
GOG_ACCOUNT = "niamh@telnyx.com"
GOG_TIMEOUT = 15  # Reduced from 30 to prevent hanging
MAX_MEETINGS_PER_RUN = 15
MAX_FILES_PER_MEETING = 10

# Salesforce Configuration  
SALESFORCE_TIMEOUT = 20
SALESFORCE_LOGIN_URL = "https://login.salesforce.com/services/oauth2/token"
SALESFORCE_BASE_URL = "https://telnyx.lightning.force.com/lightning/r"

# Slack Configuration
SLACK_CHANNEL = "#sales-calls"
SLACK_USERNAME = "ninibot" 
SLACK_ICON = ":telephone_receiver:"
SLACK_TIMEOUT = 10

# Database Configuration
DATABASE_NAME = "v1_modular.db"

# Content Processing Configuration
MIN_SUMMARY_LENGTH = 100
MIN_TRANSCRIPT_LENGTH = 200
MIN_CONTENT_LENGTH = 50
MAX_INSIGHT_LENGTH = 150

# Content Type Mappings
CONTENT_TYPE_INDICATORS = {
    'transcript': '🎙️ Transcript',
    'gemini_summary': '🤖 AI Summary', 
    'chat_messages': '💬 Chat Messages',
    'full_content': '📄 Full Notes'
}

# Transcript Detection Patterns
TRANSCRIPT_PATTERNS = [
    r'\btranscript\s+recording\b',
    r'\brecording\s+transcript\b',  
    r'\bcall\s+transcript\b',
    r'\bmeeting\s+transcript\b',
    r'\btranscription\s+started\b',
    r'\btranscription\s+ended\b',
    r'^\s*transcript\s*$',
    r'\btranscript\s*\n\s*\n',
]

TRANSCRIPT_INDICATORS = [
    'transcription ended after',
    'this editable transcript was computer generated',
    'people can also change the text after it was created',
    'recording started',
    'recording ended'
]

# Insight Extraction Keywords
PAIN_KEYWORDS = [
    'issue', 'problem', 'challenge', 'difficulty', 'concern', 
    'struggle', 'bottleneck', 'frustration', 'blocker'
]

PRODUCT_KEYWORDS = {
    'voice': 'Programmable Voice API',
    'sms': 'SMS API', 
    'messaging': 'Messaging API',
    'sip': 'SIP Trunking',
    'call control': 'Call Control API',
    'webhook': 'Webhook APIs',
    'phone': 'Phone Numbers API'
}

ACTION_KEYWORDS = [
    'will', 'next', 'follow up', 'send', 'schedule', 
    'review', 'test', 'implement', 'plan to', 'going to'
]

# Utility Functions
def get_today_date():
    """Get today's date in YYYY-MM-DD format"""
    return datetime.now().strftime("%Y-%m-%d")

def get_timestamp():
    """Get current timestamp"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")