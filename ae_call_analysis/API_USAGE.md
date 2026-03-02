# Call Intelligence API Usage

## Quick Start

```bash
# Start the API
cd ae_call_analysis
export OPENAI_API_KEY='your_openai_key'
python3 simple_call_api.py
```

## Process a Call

```bash
curl -X POST "http://localhost:8080/process-call" \
  -H "Content-Type: application/json" \
  -d '{
    "prospect_name": "Jane Doe",
    "title": "Discovery Call - Jane Doe (TechCorp)",
    "transcript": "AE: Hi Jane, thanks for joining... [full transcript]",
    "call_date": "2026-02-27",
    "fellow_id": "optional_fellow_id"
  }'
```

## Response

```json
{
  "status": "success",
  "message": "Call processed successfully",
  "call_id": 2,
  "prospect_name": "Jane Doe",
  "processing_time": "1.2s",
  "analysis": {
    "prospect_interest_level": "High",
    "ae_excitement_level": "Medium",
    "analysis_confidence": 0.85,
    "strategic_insights": "Prospect expressed strong interest...",
    "company_intelligence": "TechCorp is a 500-person company...",
    "next_steps": "Schedule technical demo..."
  },
  "slack_preview": {
    "main_message": "🔔 New Call Intelligence Alert...",
    "thread_message": "📋 Call Details..."
  }
}
```

## List Recent Calls

```bash
curl "http://localhost:8080/calls"
```

## Integration Options

### Option 1: Direct API Calls
```python
import requests

call_data = {
    "prospect_name": "John Smith",
    "title": "Discovery Call",
    "transcript": "...",
}

response = requests.post(
    "http://localhost:8080/process-call",
    json=call_data
)
```

### Option 2: Fellow Integration (Future)
Add Fellow API lookup to fetch call data by Event GUID:
```python
# Will add Fellow API integration back once authentication resolved
```

### Option 3: Zapier Integration
Use Zapier HTTP webhook to POST call data to the API:
- Webhook URL: `http://localhost:8080/process-call`
- Method: POST
- Content-Type: application/json
- Body: Call data JSON

## Architecture

```
📞 Call Data Input
    ↓
🔍 Salesforce Event Lookup  
    ↓
🤖 OpenAI Strategic Analysis
    ↓
💾 Database Storage
    ↓
📱 Slack Alert Generation
    ↓
✅ Response with Results
```

## What Gets Processed

1. **Salesforce Integration**: Looks up existing events by prospect name
2. **AI Analysis**: OpenAI analyzes transcript for strategic insights
3. **Database Storage**: Stores call + analysis in SQLite
4. **Slack Alerts**: Generates threaded alert messages
5. **Response**: Returns complete results + processing metadata

## Benefits vs Previous Approach

❌ **Old Way**: ngrok → Zapier → Webhook → Background Processing  
✅ **New Way**: Direct FastAPI → Orchestrated Pipeline → Immediate Results

- **Simpler**: One file, clear flow
- **Faster**: No external tunneling or background jobs  
- **More Reliable**: Direct API calls, no network dependencies
- **Easier to Debug**: All logic in one place
- **Production Ready**: Standard FastAPI deployment