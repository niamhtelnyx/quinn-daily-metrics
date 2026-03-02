# 🔑 Credentials Setup Guide

## Current Status: ✅ DEMO WORKING

The Call Intelligence API is **fully functional** with intelligent analysis simulation. To enable real external API integrations, add the credentials below.

## 🎯 Demo System (Currently Running)

**Port**: `http://localhost:8082`
**Status**: ✅ Complete pipeline working
**Features**: Intelligent analysis, Salesforce demo, database storage, Slack alerts

```bash
# Test the working demo
curl -X POST "http://localhost:8082/process-call" \
  -H "Content-Type: application/json" \
  -d '{"prospect_name": "Jane Doe", "title": "Demo Call", "transcript": "..."}'
```

## 🔧 Credentials Needed for Full Integration

### 1. OpenAI API (for Enhanced Analysis)

**Get credential**: https://platform.openai.com/account/api-keys
**Format**: `sk-proj-...` (project API key) or `sk-...` (legacy API key)

```bash
export OPENAI_API_KEY="sk-proj-YOUR_OPENAI_KEY_HERE"
```

**Test it**:
```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"Hello"}],"max_tokens":5}'
```

### 2. Anthropic Claude API (Alternative to OpenAI)

**Get credential**: https://console.anthropic.com/dashboard
**Format**: `sk-ant-api03-...` (API key)

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-YOUR_CLAUDE_KEY_HERE"
```

**Test it**:
```bash
curl https://api.anthropic.com/v1/messages \
  -H "Authorization: Bearer $ANTHROPIC_API_KEY" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-3-sonnet-20240229","max_tokens":10,"messages":[{"role":"user","content":"Hello"}]}'
```

### 3. Fellow API (for Automatic Call Ingestion)

**Current**: Using hardcoded test key (not working)
**Need**: Valid Fellow API key for Telnyx organization

```bash
export FELLOW_API_KEY="YOUR_FELLOW_API_KEY_HERE"
```

**Test it**:
```bash
curl -H "Authorization: Bearer $FELLOW_API_KEY" \
     -H "Content-Type: application/json" \
     https://telnyx.fellow.app/api/v1/recordings
```

### 4. Slack (for Real Alert Delivery)

**Get credential**: Create Slack app at https://api.slack.com/apps
**Format**: `xoxb-...` (bot token) or webhook URL

```bash
export SLACK_BOT_TOKEN="xoxb-YOUR-SLACK-BOT-TOKEN"
# OR
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

## 🚀 Enhanced API with Real Credentials

Once you have working credentials, update the API:

### Option 1: Environment Variables
```bash
export OPENAI_API_KEY="sk-proj-your-real-key"
export FELLOW_API_KEY="your-fellow-key"
export SLACK_WEBHOOK_URL="your-slack-webhook"

# Restart with real credentials
cd ae_call_analysis
python3 enhanced_call_api.py  # Will create this with real integrations
```

### Option 2: Configuration File
```python
# config.py
CREDENTIALS = {
    "openai_api_key": "sk-proj-your-real-key",
    "fellow_api_key": "your-fellow-key", 
    "slack_webhook_url": "your-slack-webhook"
}
```

## 🔍 Current Credential Status

| Service | Status | Test Result |
|---------|---------|-------------|
| **OpenAI** | ❌ Invalid key | `401 Unauthorized` |
| **Claude (OAuth)** | ❌ Token expired | `401 Unauthorized` |
| **Fellow API** | ❌ Invalid key | `401 Unauthorized` |
| **Salesforce** | ✅ CLI working | `Success` via existing CLI |
| **Database** | ✅ Working | SQLite functional |
| **Slack** | ✅ Demo ready | Alert generation working |

## 🎯 What Works Right Now

### ✅ Working Features (No External APIs Needed)
- **Complete FastAPI pipeline**: All orchestration logic
- **Intelligent analysis**: Based on transcript content analysis
- **Database storage**: Full call and analysis data persistence
- **Salesforce demo**: Simulated integration with realistic data  
- **Slack alert generation**: Professional formatted alerts
- **REST API endpoints**: Full CRUD operations

### 🔧 Features Needing Real Credentials
- **AI-powered analysis**: OpenAI/Claude for sophisticated insights
- **Fellow call ingestion**: Automatic call data retrieval
- **Real Slack delivery**: Actual message posting to channels
- **Live Salesforce data**: Real-time event lookups

## 📊 Production Deployment

### Quick Start (Demo Mode)
```bash
cd ae_call_analysis
python3 demo_call_api.py    # Port 8082 - Demo with simulated analysis
```

### Full Production (Real Credentials)
```bash
# Set real credentials
export OPENAI_API_KEY="sk-proj-YOUR-KEY"
export FELLOW_API_KEY="YOUR-FELLOW-KEY"

# Run production version (will create)
python3 production_call_api.py  # Port 8080 - Full external integrations
```

## 🔗 Integration Examples

### Python Integration
```python
import requests

def process_call(prospect_name, title, transcript):
    response = requests.post("http://localhost:8082/process-call", 
        json={
            "prospect_name": prospect_name,
            "title": title,
            "transcript": transcript
        }
    )
    return response.json()

result = process_call("John Smith", "Demo Call", "transcript here...")
print(f"Processed call {result['call_id']} with {result['analysis']['analysis_confidence']:.0%} confidence")
```

### Zapier Integration
- **Webhook URL**: `http://localhost:8082/process-call`
- **Method**: POST
- **Body**: JSON with `prospect_name`, `title`, `transcript`
- **Response**: Complete analysis results

## 💡 Next Steps

1. **Get OpenAI API key** → Enhanced AI analysis
2. **Get working Fellow API credentials** → Automatic call ingestion
3. **Set up Slack webhook** → Real alert delivery
4. **Deploy to cloud** → 24/7 availability

The architecture is complete and working - just needs real API credentials to unlock full functionality!