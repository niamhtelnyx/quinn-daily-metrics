# 🔔 Fellow Call Intelligence Webhook Setup

**Real-time processing via Zapier webhook integration**

## 🚀 Quick Start

```bash
# 1. Set up Fellow API access
./ae_call_analysis/setup_fellow_api.sh

# 2. Set your Fellow API key
export FELLOW_API_KEY="your_fellow_api_key_here"

# 3. Start the webhook server
./ae_call_analysis/start_webhook_server.sh

# 4. Test with Fellow call ID
python3 ae_call_analysis/test_call_id.py

# 5. Configure Zapier to POST call IDs to your webhook URL
```

## 📡 Zapier Configuration

**In your existing Zapier Fellow webhook:**

1. **Action**: Webhooks by Zapier → POST
2. **URL**: `http://[your-server-ip]:5000/webhook/fellow-call`
3. **Method**: POST
4. **Data**: Raw JSON body
5. **Headers**: `Content-Type: application/json`

**Simple payload structure** (just Fellow call ID):
```json
{
  "fellow_call_id": "QdZdMHWoec"
}
```

**Alternative formats supported:**
```json
{"call_id": "QdZdMHWoec"}
{"id": "QdZdMHWoec"}
```

**📡 The system fetches complete call data from Fellow API automatically!**

## 🔄 How It Works

```
Fellow Call → Zapier Webhook → Our Webhook Receiver → Enhanced Pipeline → Slack Alert
    ↓              ↓                    ↓                      ↓              ↓
New "Telnyx    POST call ID     Fetch full call data   Salesforce      #bot-testing
Intro Call"    to endpoint      from Fellow API        lookup +        threaded
created        (lightweight)   → Store in DB           OpenAI          message
                               → Process async
```

## 🛠️ Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /webhook/fellow-call` | **Main webhook** - Receives Zapier data |
| `GET /health` | Health check for monitoring |
| `POST /test` | Test endpoint with sample data |

## ✅ Enhanced Processing Pipeline

**Real-time processing includes:**

1. **📞 Call Storage** - Store in database (duplicate detection)
2. **🔍 Salesforce Lookup** - Match to real events + AE validation  
3. **🤖 OpenAI Analysis** - Complete strategic assessment
4. **🏢 Company Intelligence** - Business research + competitive analysis
5. **📝 Event Updates** - Append insights to Salesforce Event.Description
6. **🧵 Slack Intelligence** - Threaded executive-ready alerts

## 🧪 Testing

```bash
# Test the webhook receiver
python3 ae_call_analysis/test_webhook.py

# Expected output:
# ✅ Webhook test successful!
# 🎯 Check console for processing logs...
```

## 📊 Monitoring

**Webhook server logs show:**
- 🔔 Incoming webhook receipts
- 📦 Payload contents  
- 🚀 Processing status
- ✅ Slack deployment results
- ❌ Any errors or failures

## 🔧 Production Deployment

**For production, consider:**

1. **Reverse Proxy** (nginx) for SSL termination
2. **Process Manager** (pm2, systemd) for auto-restart  
3. **Load Balancer** for high availability
4. **Monitoring** (health checks, alerting)

**Example production URL:**
```
https://your-domain.com/api/fellow-webhook
```

## 🎯 Benefits vs Cron Job

| **30-min Cron** | **Real-time Webhook** |
|------------------|----------------------|
| ⏰ 30-minute delay | ⚡ **Instant processing** |
| 🔄 Polls all calls | 🎯 **Only new calls** |
| 📊 Batch processing | 🔥 **Individual focus** |
| ⏱️ Resource intensive | 💡 **Event-driven efficiency** |

## 🚨 Error Handling

**Built-in safeguards:**
- ✅ **Immediate webhook response** (don't block Zapier)
- ✅ **Async processing** (handle long OpenAI calls)
- ✅ **Duplicate detection** (prevent reprocessing)
- ✅ **Error logging** (troubleshooting visibility)  
- ✅ **Graceful failures** (continue on Salesforce/Slack errors)

---

**Ready to go live with real-time Call Intelligence!** 🎯

Next: Configure your Zapier webhook to point to the webhook receiver and enjoy instant AE call insights!