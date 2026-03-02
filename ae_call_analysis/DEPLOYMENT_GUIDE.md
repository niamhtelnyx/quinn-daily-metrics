# Call Intelligence API - Deployment Guide

## 🚀 Quick Start

```bash
# 1. Start the API
cd ae_call_analysis
export OPENAI_API_KEY='your_openai_key'  # Optional: for AI analysis
python3 simple_call_api.py

# 2. Test it
python3 test_api.py

# 3. View API docs
open http://localhost:8080/docs
```

## 📡 API Endpoints

| Endpoint | Method | Purpose |
|----------|---------|---------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/process-call` | POST | Main orchestration |
| `/calls` | GET | List recent calls |
| `/docs` | GET | Swagger UI |

## 📞 Process a Call

```bash
curl -X POST "http://localhost:8080/process-call" \
  -H "Content-Type: application/json" \
  -d '{
    "prospect_name": "Jane Smith",
    "title": "Discovery Call - Jane Smith (TechCorp)",
    "transcript": "Full call transcript here...",
    "call_date": "2026-02-27"
  }'
```

## 🔄 Integration Options

### Option 1: Direct Python Integration
```python
import requests

def process_call(prospect_name, title, transcript):
    response = requests.post("http://localhost:8080/process-call", 
        json={
            "prospect_name": prospect_name,
            "title": title,
            "transcript": transcript
        }
    )
    return response.json()

# Use it
result = process_call("John Doe", "Demo Call", "transcript...")
print(f"Call {result['call_id']} processed: {result['prospect_name']}")
```

### Option 2: Zapier Webhook
- **Webhook URL**: `http://localhost:8080/process-call`
- **Method**: POST
- **Content-Type**: application/json
- **Body**: JSON with `prospect_name`, `title`, `transcript`

### Option 3: Fellow Integration (Future)
Add Fellow API lookup to automatically fetch call data by Event GUID.

## 🏗️ Architecture

```
📞 Call Data Input (JSON)
    ↓
🔍 Salesforce Event Lookup (optional)
    ↓
🤖 OpenAI Strategic Analysis (optional)
    ↓
💾 SQLite Database Storage
    ↓
📱 Slack Alert Generation
    ↓
✅ Complete Results Response
```

## 📊 Response Format

```json
{
  "status": "success",
  "message": "Call processed successfully", 
  "call_id": 123,
  "prospect_name": "Jane Smith",
  "processing_time": "1.2s",
  "analysis": {
    "prospect_interest_level": "High",
    "ae_excitement_level": "Medium",
    "analysis_confidence": 0.85,
    "strategic_insights": "Prospect shows strong interest...",
    "company_intelligence": "TechCorp is a growing startup...",
    "next_steps": "Schedule technical demo within 1 week"
  },
  "slack_preview": {
    "main_message": "🔔 New Call Intelligence Alert...",
    "thread_message": "📋 Detailed analysis..."
  }
}
```

## 🚀 Production Deployment

### Option 1: Simple Server
```bash
# Install dependencies
pip install fastapi uvicorn requests

# Set environment variables
export OPENAI_API_KEY="sk-..."
export FELLOW_API_KEY="..." # For future Fellow integration

# Run server
python3 simple_call_api.py
```

### Option 2: Docker
```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install fastapi uvicorn requests
EXPOSE 8080
CMD ["python3", "simple_call_api.py"]
```

### Option 3: Cloud Deploy
Deploy to Heroku, Railway, DigitalOcean, AWS, etc.
- Port: 8080
- Environment: Set OPENAI_API_KEY
- Health check: `/health`

## 🔧 Configuration

### Environment Variables
```bash
export OPENAI_API_KEY="sk-..."           # For AI analysis
export FELLOW_API_KEY="..."             # For Fellow integration 
export SLACK_WEBHOOK_URL="..."          # For Slack alerts
export DATABASE_PATH="calls.db"         # SQLite database
```

### Database Setup
The API automatically creates SQLite tables:
- `calls`: Call data and metadata
- `analysis_results`: AI analysis results

## 📈 Benefits vs Previous Setup

| Feature | Old Webhook | New FastAPI |
|---------|-------------|-------------|
| **Complexity** | High (ngrok + Zapier + background) | Low (single file) |
| **Reliability** | Network dependent | Direct API calls |
| **Speed** | 2-3 minute background jobs | Immediate response |
| **Debugging** | Multi-service logs | Single log stream |
| **Deployment** | Tunnel + coordination | Standard web service |
| **Integration** | Webhook only | REST API + multiple options |

## 🎯 Next Steps

1. **Fix API Keys**: Add working OpenAI + Salesforce credentials
2. **Add Fellow Integration**: Restore Fellow API lookup by Event GUID  
3. **Deploy to Production**: Choose cloud platform and deploy
4. **Slack Integration**: Add real Slack webhook posting
5. **Monitoring**: Add logging, metrics, error tracking

## 🧪 Testing

```bash
# Test the API
python3 test_api.py

# Test specific endpoint
curl http://localhost:8080/health

# View API documentation
open http://localhost:8080/docs
```