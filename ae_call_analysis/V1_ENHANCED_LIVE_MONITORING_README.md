# 🚀 V1 Enhanced Call Intelligence - Live Monitoring

**Status**: ✅ **PRODUCTION OPERATIONAL** - Full AI-powered live monitoring system

## 🎯 What This System Does

Automatically monitors Fellow for new Telnyx intro calls **today only**, extracts full transcripts, runs AI analysis, updates Salesforce with insights, and posts professional alerts to Slack.

## ⚡ Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 2. Test the system
python3 fellow_cron_job.py

# 3. Set up automation (runs every 30 minutes)
crontab -e
# Add: */30 * * * * cd /path/to/ae_call_analysis && source .env && python3 fellow_cron_job.py >> logs/cron.log 2>&1
```

## 🔑 Required API Keys

Add these to your `.env` file:

```bash
# Fellow API (with include parameters for transcripts)
FELLOW_API_KEY=your_fellow_api_key_here

# Salesforce OAuth2 (for contact lookup and event updates)  
SF_CLIENT_ID=your_salesforce_client_id
SF_CLIENT_SECRET=your_salesforce_client_secret
SF_DOMAIN=your_salesforce_domain

# Slack Bot Token (for direct API posting)
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token

# OpenAI (for AI call analysis)
OPENAI_API_KEY=sk-proj-your-openai-api-key
```

## 🤖 AI Analysis Features

**9-Point Analysis Structure:**
- 🔴 **Pain Points**: Business problems identified
- 🎯 **Use Cases**: How they'll use Telnyx services  
- 💡 **Products**: Telnyx products discussed
- 📈 **Buying Signals**: Purchase readiness indicators
- ⚙️ **Technical Needs**: Integration requirements
- ⏰ **Timeline**: Urgency and project timeline
- 👤 **Decision Makers**: Key stakeholders involved
- 🔄 **Competition**: Current providers mentioned
- 🚀 **Next Steps**: Recommended follow-up actions

## 📅 Live Monitoring Behavior

**✅ Today Only**: Only processes calls from current date (no historical backlog)  
**✅ Real-time**: Runs every 30 minutes automatically  
**✅ Duplicate Prevention**: Never processes the same call twice  
**✅ Rate Limited**: Max 5 calls per run to prevent spam  
**✅ Error Handling**: Graceful failures with detailed logging  

## 🚀 Production Files

| File | Purpose | Size |
|------|---------|------|
| `fellow_cron_job.py` | Main production script | ~20KB |
| `V1_ENHANCED_PRODUCTION.py` | Production backup | ~20KB |
| `.env` | Environment variables | 1KB |
| `logs/cron.log` | Execution logs | Variable |

## 📊 Key Features

**✅ Working Fellow Transcripts**: Include parameters extract full speech segments  
**✅ AI Analysis**: OpenAI GPT-4 analysis on real call transcripts  
**✅ Live Monitoring**: Today-only processing for real-time alerts  
**✅ Enhanced Slack**: Professional formatting with hyperlinks  
**✅ Salesforce Integration**: Enhanced events with AI insights  
**✅ Production Ready**: Every 30 minutes automation  

---

**V1 Enhanced Call Intelligence - Production Ready** 🚀  
*Real-time monitoring with full AI analysis capabilities*