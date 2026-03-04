# 🚀 V2 Enhanced Call Intelligence System

**Repository**: https://github.com/team-telnyx/meeting-sync  
**Branch**: v2-enhanced  
**Team**: Telnyx Sales Operations  
**Status**: ✅ **PRODUCTION READY** - Smart Deduplication + Salesforce Fallback

## 🎯 What This System Does

**V2 ENHANCED** processes calls from **TWO SOURCES** with **SMART DEDUPLICATION**:

### 📁 **Google Drive** (Processed FIRST - Gemini is faster)
- Monitors Google Drive for Google Meet recordings with Gemini notes
- Full AI analysis + Slack posting
- **Zero authentication complexity** - uses gog CLI

### 📞 **Fellow API** (Processed SECOND - Adds recording URL)
- For calls already processed by Google Drive: **ONLY adds Fellow recording URL**
- For new calls: Full AI analysis + Slack posting
- **No duplicate analysis** - saves tokens and prevents spam

## 🧠 Smart Deduplication Logic

```
📁 Google Drive Call Found
  ↓
🤖 Full AI Analysis + Slack Post
  ↓
📋 Mark in Database with dedup_key
  ↓
📞 Fellow API Check (later)
  ↓
❓ Same call found in Fellow?
  ↓
✅ YES: Add Fellow URL to Slack thread
❌ NO: Process as new call
```

**Deduplication Key**: `{prospect_email}_{call_date}` ensures same prospect on same day = same call

## 🛡️ Salesforce Fallback

**Enhanced Contact Matching**:
1. Search Salesforce by **both name AND email**
2. If found: ✅ Use contact data for AI analysis
3. If not found: ➕ **Add to unmatched_contacts table**

**Unmatched Contacts Table** stores:
- Prospect name & email
- Call ID & source
- Call date & processing time
- Notes for manual review

## 🔧 Enhanced Architecture

```
┌─────────────────┐    ┌─────────────────┐
│  Google Drive   │    │   Fellow API    │
│  (Gemini Notes) │    │  (Transcripts)  │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          │ PHASE 1              │ PHASE 2
          │ Full Analysis        │ Add URLs Only
          └──────────┬───────────┘
                     │
          ┌─────────────────────┐
          │ Smart Deduplication │
          │                     │
          │ • dedup_key lookup  │
          │ • Fellow URL append │
          │ • Slack thread adds │
          └─────────┬───────────┘
                    │
          ┌─────────────────────┐
          │ Enhanced Database   │
          │                     │
          │ • processed_calls   │
          │ • unmatched_contacts│
          │ • Source tracking   │
          └─────────┬───────────┘
                    │
          ┌─────────────────────┐
          │ Unified Output      │
          │                     │
          │ • Same Slack format │
          │ • SF fallback table │
          │ • No duplicates     │
          └─────────────────────┘
```

## 🚀 Quick Start

### 1. Test Enhanced System

```bash
cd /Users/niamhcollins/clawd/ae_call_analysis

# Test all enhanced features
python3 test_enhanced_system.py
```

### 2. Run Enhanced Production

```bash
# Process both sources with smart deduplication
python3 V2_ENHANCED_PRODUCTION.py
```

### 3. Check Unmatched Contacts

```bash
# View contacts that couldn't be matched to Salesforce
python3 check_unmatched_contacts.py
```

### 4. Set Up Automation

```bash
# Edit crontab for 30-minute intervals
crontab -e

# Add this line:
*/30 * * * * cd /Users/niamhcollins/clawd/ae_call_analysis && python3 V2_ENHANCED_PRODUCTION.py >> logs/v2_enhanced.log 2>&1
```

## 📊 Enhanced Processing Flow

### **Every 30 minutes:**

#### **PHASE 1: Google Drive (Process First)**
1. Search Google Drive for new "Notes by Gemini" docs from today
2. For each new doc:
   - Generate deduplication key
   - Check if already processed → Skip if yes
   - Extract Gemini notes content
   - Parse prospect name & AE from filename
   - Search Salesforce (name + email)
   - If no SF match → Add to unmatched_contacts table
   - Run full AI analysis
   - Post to Slack (main post + thread)
   - Mark as processed with dedup_key

#### **PHASE 2: Fellow (Add URLs or Process New)**
1. Get Fellow "Telnyx Intro Call" recordings from today
2. For each Fellow call:
   - Generate deduplication key
   - Check if already processed by Google Drive
   - **If DUPLICATE**: 
     - ➕ Add Fellow URL to database
     - 📎 Post Fellow recording link in Slack thread
     - ✅ Skip AI analysis (already done)
   - **If NEW**:
     - 🤖 Run full AI analysis
     - 📱 Post to Slack
     - 📋 Mark as processed

## 📁 Enhanced File Structure

```
ae_call_analysis/
├── V2_ENHANCED_PRODUCTION.py      # Main enhanced script
├── google_drive_integration.py    # Google Drive module
├── check_unmatched_contacts.py    # Unmatched contacts utility
├── test_enhanced_system.py        # Enhanced test script
├── v2_enhanced.db                 # Enhanced database
│   ├── processed_calls            # All processed calls
│   └── unmatched_contacts         # Salesforce fallbacks
├── .env                           # API credentials
└── logs/
    └── v2_enhanced.log            # Enhanced automation logs
```

## 🗃️ Enhanced Database Schema

### **processed_calls Table**
```sql
CREATE TABLE processed_calls (
    id INTEGER PRIMARY KEY,
    call_id TEXT,                 -- Fellow ID or Google Doc ID
    source TEXT,                  -- 'fellow' or 'google_drive'  
    prospect_name TEXT,
    prospect_email TEXT,
    ae_name TEXT,
    call_date TEXT,
    processed_at TEXT,
    slack_posted BOOLEAN,
    slack_ts TEXT,                -- For thread replies
    salesforce_updated BOOLEAN,
    ai_analyzed BOOLEAN,
    dedup_key TEXT,               -- For deduplication
    fellow_url TEXT,              -- Fellow recording URL  
    google_doc_id TEXT,           -- Google Doc ID
    UNIQUE(call_id, source)
);
```

### **unmatched_contacts Table**
```sql
CREATE TABLE unmatched_contacts (
    id INTEGER PRIMARY KEY,
    prospect_name TEXT,
    prospect_email TEXT,
    call_id TEXT,
    source TEXT,                  -- 'fellow' or 'google_drive'
    call_date TEXT,
    created_at TEXT,
    notes TEXT                    -- Why unmatched, manual notes
);
```

## 🎯 Example Processing Scenarios

### **Scenario 1: Google Drive First, Fellow Later**
1. **15:30** - Google Meet ends, Gemini processes notes
2. **15:35** - V2 Enhanced finds Google Drive doc
3. **15:36** - Full AI analysis + Slack post with thread
4. **16:00** - Fellow finishes processing transcript  
5. **16:05** - V2 Enhanced finds Fellow recording
6. **16:06** - Detects duplicate via dedup_key
7. **16:07** - Adds Fellow URL comment to Slack thread
8. **Result**: One Slack post, one thread, Fellow recording added

### **Scenario 2: Fellow Only**
1. **14:30** - Fellow-only call (no Google Meet recording)
2. **15:00** - V2 Enhanced processes Fellow call
3. **15:01** - No duplicate found (new dedup_key)
4. **15:02** - Full AI analysis + Slack posting
5. **Result**: Standard processing like V1

### **Scenario 3: Unmatched Contact**
1. **Call processed** from either source
2. **Salesforce search** fails (no name or email match)
3. **Contact added** to unmatched_contacts table
4. **AI analysis continues** without Salesforce data
5. **Manual review** possible via check_unmatched_contacts.py

## 🔧 Configuration

### **Environment Variables** (Same as V1)
```bash
# Fellow API
FELLOW_API_KEY=your_fellow_key

# Salesforce (optional but recommended)
SF_CLIENT_ID=your_sf_client_id
SF_CLIENT_SECRET=your_sf_secret
SF_DOMAIN=telnyx

# Slack (required)
SLACK_BOT_TOKEN=xoxb-your-slack-token

# AI Analysis (required)
OPENAI_API_KEY=sk-proj-your-openai-key
```

### **Google Drive Setup**
Uses `gog` CLI (already configured):
- ✅ Authenticated for `niamh@telnyx.com`
- ✅ Access to `drive` and `docs` services
- ✅ Environment loaded from `/Users/niamhcollins/clawd/.env.gog`

## 📊 Monitoring & Management

### **Check Processing Status**
```bash
# View recent logs
tail -f logs/v2_enhanced.log

# Check database stats
sqlite3 v2_enhanced.db "
SELECT source, COUNT(*) as calls_processed 
FROM processed_calls 
WHERE DATE(processed_at) = DATE('now') 
GROUP BY source"
```

### **Review Unmatched Contacts**
```bash
# View summary and recent unmatched
python3 check_unmatched_contacts.py

# Export for manual review
python3 check_unmatched_contacts.py --export
```

### **Database Queries**
```sql
-- Today's processing summary
SELECT 
    source, 
    COUNT(*) as total,
    SUM(ai_analyzed) as ai_success,
    SUM(slack_posted) as slack_success
FROM processed_calls 
WHERE DATE(processed_at) = DATE('now')
GROUP BY source;

-- Recent unmatched contacts
SELECT prospect_name, prospect_email, source, created_at
FROM unmatched_contacts 
WHERE created_at >= datetime('now', '-7 days')
ORDER BY created_at DESC;

-- Deduplication effectiveness
SELECT 
    dedup_key,
    GROUP_CONCAT(source) as sources,
    COUNT(*) as occurrences
FROM processed_calls
GROUP BY dedup_key
HAVING COUNT(*) > 1;
```

## 🎉 Enhanced Benefits

**Compared to V1:**
- ✅ **2X call coverage** (Fellow + Google Drive)
- ✅ **Smart deduplication** (no duplicate processing)
- ✅ **Salesforce fallback** (no lost prospects)  
- ✅ **Enhanced tracking** (source-aware database)
- ✅ **Zero authentication overhead** (gog CLI integration)
- ✅ **Unified monitoring** (single Slack channel)

**Key Improvements:**
- 🧠 **Intelligent processing** - Gemini first, Fellow adds URLs
- 🛡️ **Robust fallbacks** - Unmatched contacts tracked
- 🔄 **Efficient deduplication** - Date + prospect based keys  
- 📊 **Enhanced analytics** - Source tracking and stats
- 🚀 **Production ready** - Tested and validated

---

**🎯 V2 Enhanced Call Intelligence - Production Ready** 🚀  
*Smart deduplication with Salesforce fallback - No call left behind!*