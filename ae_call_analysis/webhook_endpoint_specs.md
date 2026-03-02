# Fellow Call Intelligence Webhook - FastAPI Endpoint Specs

## 🎯 **Webhook Flow Design**

```
Fellow Call Complete → Zapier Automation → FastAPI Webhook → Enhanced Pipeline → Slack Alert
```

## 📡 **Endpoint Specifications**

### **Base Endpoint**
```
POST /webhook/fellow-call-intelligence
Content-Type: application/json
```

### **Authentication**
- **Method**: API Key in header
- **Header**: `X-API-Key: {webhook_secret_key}`
- **Alternative**: Webhook signature validation (HMAC-SHA256)

### **Request Payload**
```json
{
  "call_id": "QdZdMHWoec",
  "event_name": "call.completed", 
  "call_title": "Telnyx Intro Call (Ben Lewell)",
  "timestamp": "2026-02-27T15:25:00Z",
  "metadata": {
    "duration_minutes": 31,
    "participant_count": 3,
    "fellow_workspace": "telnyx"
  }
}
```

### **Response Format**
```json
{
  "status": "accepted",
  "message": "Call intelligence pipeline initiated",
  "processing_id": "uuid-here",
  "estimated_completion": "2-3 minutes",
  "webhook_id": "webhook_123456789"
}
```

## 🏗️ **FastAPI Implementation Structure**

### **1. Webhook Endpoint**
```python
@app.post("/webhook/fellow-call-intelligence")
async def fellow_call_webhook(
    payload: FellowCallWebhook,
    x_api_key: str = Header(None),
    background_tasks: BackgroundTasks
):
    # Validate API key
    # Queue background processing
    # Return immediate response
```

### **2. Background Processing Pipeline**
```python
async def process_call_intelligence(call_id: str, call_title: str):
    # 1. Fellow API - Get call transcript & details
    # 2. Salesforce Event Lookup - Find real event with record validation
    # 3. Company Intelligence - Research & business insights  
    # 4. OpenAI Analysis - Generate call intelligence
    # 5. Enhanced Message Format - Professional hyperlinked Slack format
    # 6. Salesforce Event Update - Append call summary
    # 7. Slack Deployment - Post threaded alert to #bot-testing
    # 8. Error handling & status updates
```

## 🔒 **Security & Validation**

### **Input Validation**
- Call ID format validation (Fellow format)
- Event name whitelist (`call.completed`, `call.transcription_ready`)
- Timestamp format validation
- Max payload size: 10KB

### **Rate Limiting**  
- 10 requests per minute per IP
- 100 requests per hour per API key
- Burst protection: 3 requests per 10 seconds

### **Authentication Options**
**Option A: Simple API Key**
```
X-API-Key: fellow_webhook_secret_2026
```

**Option B: HMAC Signature** (More secure)
```
X-Fellow-Signature: sha256=abcdef123456...
X-Fellow-Timestamp: 1640995200
```

## 📊 **Error Handling & Status Codes**

| Status Code | Scenario | Response |
|------------|----------|----------|
| `200` | Success - Processing initiated | `{"status": "accepted"}` |
| `400` | Invalid payload/missing fields | `{"error": "Invalid call_id format"}` |
| `401` | Authentication failed | `{"error": "Invalid API key"}` |
| `429` | Rate limit exceeded | `{"error": "Rate limit exceeded"}` |
| `500` | Internal processing error | `{"error": "Processing failed"}` |

## 🔄 **Processing States & Callbacks**

### **Optional Status Callback**
If Zapier needs processing status updates:
```
POST {zapier_callback_url}
{
  "webhook_id": "webhook_123456789",
  "status": "completed",
  "slack_message_id": "1772227446.785629",
  "processing_time_seconds": 127,
  "errors": []
}
```

## 📝 **Zapier Integration Requirements**

### **Zapier Webhook Configuration**
```
URL: https://your-domain.com/webhook/fellow-call-intelligence
Method: POST
Headers: 
  - X-API-Key: {secret_key}
  - Content-Type: application/json
```

### **Zapier Payload Mapping**
```javascript
{
  "call_id": "{{fellow_call_id}}",           // Fellow Call ID
  "event_name": "call.completed",            // Static or Fellow event type
  "call_title": "{{fellow_call_title}}",     // Fellow Call Title
  "timestamp": "{{fellow_call_end_time}}",   // ISO timestamp
  "metadata": {
    "duration_minutes": "{{fellow_duration}}",
    "participant_count": "{{fellow_participants}}"
  }
}
```

## 🛡️ **Production Considerations**

### **Infrastructure**
- **Hosting**: Cloud-based (AWS/GCP/Azure)
- **Database**: PostgreSQL for processing logs
- **Queue**: Redis/Celery for background processing
- **Monitoring**: Health check endpoint `/health`

### **Logging & Monitoring**
- Request/response logging
- Processing pipeline metrics
- Error rate monitoring  
- Slack delivery confirmation
- Salesforce update success tracking

### **Configuration**
```python
FELLOW_WEBHOOK_SECRET = "fellow_webhook_secret_2026"
SLACK_CHANNEL = "C38URQASH"  # #bot-testing
OPENAI_API_KEY = "sk-..."
SALESFORCE_ORG = "niamh@telnyx.com"
MAX_PROCESSING_TIME = 300  # 5 minutes timeout
```

## 🧪 **Testing & Development**

### **Test Payload**
```json
{
  "call_id": "QdZdMHWoec",
  "event_name": "call.completed",
  "call_title": "Telnyx Intro Call (Ben Lewell)",
  "timestamp": "2026-02-27T15:25:00Z"
}
```

### **Local Testing**
```bash
curl -X POST http://localhost:8000/webhook/fellow-call-intelligence \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test_key" \
  -d @test_payload.json
```

### **Health Check**
```
GET /health
Response: {"status": "healthy", "version": "1.0.0"}
```

## 📈 **Expected Performance**

- **Response Time**: < 200ms (immediate webhook response)
- **Processing Time**: 2-3 minutes (complete pipeline)
- **Throughput**: 10-50 calls per hour
- **Reliability**: 99.9% successful processing
- **Slack Delivery**: 99% success rate

## 🔄 **Deployment Strategy**

1. **Development**: Local FastAPI server with ngrok tunnel for Zapier testing
2. **Staging**: Cloud deployment with test Slack channel
3. **Production**: Full deployment with #bot-testing channel and monitoring

---

**Ready to implement?** This design provides a robust, scalable webhook endpoint that integrates seamlessly with Fellow → Zapier → Enhanced Call Intelligence Pipeline → Slack delivery. 🚀