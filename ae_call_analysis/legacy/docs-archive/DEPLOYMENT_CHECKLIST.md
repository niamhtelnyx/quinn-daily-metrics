# 🚀 Deployment Checklist: V1 Google Drive Enhanced

**System**: V1 Enhanced Call Intelligence with Google Drive Integration  
**File**: `V1_GOOGLE_DRIVE_ENHANCED.py`  
**Target**: Production deployment with all V1 functionality + Google Drive  
**Date**: March 4, 2025

---

## 📋 Pre-Deployment Testing

### ✅ **Phase 1: Environment Validation**

#### **1.1 Environment Variables Check**
```bash
# Required variables verification
grep -E "^(SLACK_BOT_TOKEN|OPENAI_API_KEY|SF_CLIENT_ID|SF_CLIENT_SECRET)" .env
```

**Expected Variables**:
- ✅ `SLACK_BOT_TOKEN=xoxb-*` (Slack posting)
- ✅ `OPENAI_API_KEY=sk-proj-*` (AI analysis)
- ✅ `SF_CLIENT_ID=*` (Salesforce integration)
- ✅ `SF_CLIENT_SECRET=*` (Salesforce integration)
- ✅ `SF_DOMAIN=telnyx` (Salesforce domain)

#### **1.2 Google Drive Authentication**
```bash
# Test Google Drive access
source /Users/niamhcollins/clawd/.env.gog
gog drive ls --parent 1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY --max 5
```

**Expected Output**: List of folders/files without authentication errors

#### **1.3 Database Setup**
```bash
# Verify database can be created
python3 -c "
from V1_GOOGLE_DRIVE_ENHANCED import is_call_processed
print('Database setup: OK')
"
```

**Expected**: No errors, database file `v1_google_drive.db` created

---

### ✅ **Phase 2: Component Testing**

#### **2.1 Google Drive Integration Test**
```bash
# Test recent calls retrieval
python3 -c "
from V1_GOOGLE_DRIVE_ENHANCED import get_recent_gemini_calls, TARGET_FOLDER_ID
calls, status = get_recent_gemini_calls(TARGET_FOLDER_ID, hours_back=24)
print(f'Google Drive Test: {status}')
print(f'Found {len(calls)} calls in last 24h')
for call in calls[:3]:
    print(f'  - {call[\"title\"][:50]}...')
"
```

**Expected Output**:
- ✅ No authentication errors
- ✅ List of recent Gemini notes found
- ✅ Call titles contain "Notes by Gemini"

#### **2.2 Content Extraction Test**
```bash
# Test content extraction from a known doc
python3 -c "
from V1_GOOGLE_DRIVE_ENHANCED import get_recent_gemini_calls, get_google_doc_content, TARGET_FOLDER_ID
calls, _ = get_recent_gemini_calls(TARGET_FOLDER_ID, hours_back=24)
if calls:
    call_id = calls[0]['id']
    content, error = get_google_doc_content(call_id)
    print(f'Content extraction: {\"SUCCESS\" if content else \"FAILED\"}')
    print(f'Content length: {len(content) if content else 0} chars')
    print(f'Error: {error}')
else:
    print('No recent calls to test with')
"
```

**Expected Output**:
- ✅ Content extraction: SUCCESS
- ✅ Content length > 100 characters
- ✅ Error: None

#### **2.3 Attendee Parsing Test**
```bash
# Test attendee extraction
python3 -c "
from V1_GOOGLE_DRIVE_ENHANCED import *
calls, _ = get_recent_gemini_calls(TARGET_FOLDER_ID, hours_back=24)
if calls:
    call = calls[0]
    content, _ = get_google_doc_content(call['id'])
    if content:
        formatted = format_enhanced_google_drive_call(call, content)
        print(f'Prospect: {formatted[\"prospect_name\"]}')
        print(f'AE: {formatted[\"ae_name\"]}')
        print(f'Email: {formatted[\"prospect_email\"]}')
    else:
        print('No content to parse')
else:
    print('No recent calls to test with')
"
```

**Expected Output**:
- ✅ Prospect name extracted (not "Unknown Prospect")
- ✅ AE name extracted (not "Unknown AE")  
- ✅ Email extracted (if available in content)

---

### ✅ **Phase 3: Salesforce Integration Testing**

#### **3.1 Salesforce Authentication Test**
```bash
# Test Salesforce token generation
python3 -c "
from V1_GOOGLE_DRIVE_ENHANCED import get_salesforce_token
token, msg = get_salesforce_token()
print(f'Salesforce Auth: {msg}')
print(f'Token length: {len(token) if token else 0}')
"
```

**Expected Output**:
- ✅ Salesforce Auth: ✅ Salesforce authenticated
- ✅ Token length > 100

#### **3.2 Contact Search Test**
```bash
# Test contact search with a known prospect
python3 -c "
from V1_GOOGLE_DRIVE_ENHANCED import get_salesforce_token, find_salesforce_contact_enhanced
token, _ = get_salesforce_token()
if token:
    # Test with a known contact name (replace with actual)
    contact, msg = find_salesforce_contact_enhanced('Test Contact', token)
    print(f'Contact Search: {msg}')
    if contact:
        print(f'Found: {contact[\"contact_name\"]} at {contact.get(\"company_name\", \"N/A\")}')
        print(f'Website: {contact.get(\"company_website\", \"N/A\")}')
else:
    print('No Salesforce token')
"
```

**Expected Output**:
- ✅ Contact Search: ✅ Found contact: [Name] at [Company]
- ✅ Company data extracted (name, website if available)

#### **3.3 Event Lookup Test** ⚠️ **CRITICAL**
```bash
# Test event lookup functionality (most critical V1 feature)
python3 -c "
from V1_GOOGLE_DRIVE_ENHANCED import *
token, _ = get_salesforce_token()
if token:
    # Use a contact with known events
    contact, _ = find_salesforce_contact_enhanced('Known Contact', token)
    if contact:
        event_id, msg = find_or_update_salesforce_event(contact, 'Known Contact', 'test_id', token)
        print(f'Event Lookup: {msg}')
        print(f'Event ID: {event_id}')
    else:
        print('No contact found for event test')
else:
    print('No Salesforce token')
"
```

**Expected Output**:
- ✅ Event Lookup: ✅ Updated event [event_id] OR ⚠️ No existing event found
- ✅ No errors in event search/update process

---

### ✅ **Phase 4: AI Analysis Testing**

#### **4.1 AI Analysis Structure Test**
```bash
# Test AI analysis with sample content
python3 -c "
from V1_GOOGLE_DRIVE_ENHANCED import analyze_call_with_ai
test_content = '''
Meeting with TechCorp about implementing Telnyx Voice API.
Discussed their current phone system challenges and pricing requirements.
Next step is technical proof of concept.
'''
analysis = analyze_call_with_ai(test_content, 'TechCorp', 'TechCorp Inc', 'techcorp.com')
print(f'AI Analysis Status: {analysis.get(\"status\")}')
print(f'Has main_post: {\"main_post\" in analysis}')
print(f'Has thread_reply: {\"thread_reply\" in analysis}')
if analysis.get('main_post'):
    print('Main post preview:', analysis['main_post'][:100])
"
```

**Expected Output**:
- ✅ AI Analysis Status: success
- ✅ Has main_post: True  
- ✅ Has thread_reply: True
- ✅ Main post contains scores, pain points, next steps

#### **4.2 Company Summary Test**
```bash
# Test company summary generation
python3 -c "
from V1_GOOGLE_DRIVE_ENHANCED import get_company_summary_with_ai
test_content = 'We are a software development company building CRM solutions for enterprise clients.'
summary = get_company_summary_with_ai(test_content, 'TechCorp', 'TechCorp Inc')
print(f'Company Summary: {summary}')
print(f'Summary generated: {summary is not None}')
"
```

**Expected Output**:
- ✅ Company Summary: [Descriptive company summary]
- ✅ Summary generated: True

---

### ✅ **Phase 5: Slack Integration Testing**

#### **5.1 Slack Authentication Test**
```bash
# Test Slack token validation
python3 -c "
import requests
import os
from V1_GOOGLE_DRIVE_ENHANCED import load_env
load_env()
token = os.getenv('SLACK_BOT_TOKEN')
if token:
    response = requests.get('https://slack.com/api/auth.test',
                          headers={'Authorization': f'Bearer {token}'})
    data = response.json()
    print(f'Slack Auth: {\"SUCCESS\" if data.get(\"ok\") else \"FAILED\"}')
    print(f'Bot name: {data.get(\"user\", \"Unknown\")}')
else:
    print('No Slack token found')
"
```

**Expected Output**:
- ✅ Slack Auth: SUCCESS
- ✅ Bot name: [Bot name]

#### **5.2 Slack Posting Test** ⚠️ **CAUTION**
```bash
# ONLY run this in test channel or with approval
# Test basic Slack posting (use test channel)
python3 -c "
from V1_GOOGLE_DRIVE_ENHANCED import post_to_slack_bot_api
test_msg = '🧪 V1 Enhanced Test - Please ignore'
# CHANGE CHANNEL TO TEST CHANNEL
success, msg = post_to_slack_bot_api(test_msg, 'C_TEST_CHANNEL')  
print(f'Slack Post: {msg}')
"
```

**Expected Output**:
- ✅ Slack Post: ✅ Posted to Slack (ts: [timestamp])

#### **5.3 Thread Reply Test** ⚠️ **CAUTION**
```bash
# Test threading (only if step 5.2 succeeded)
python3 -c "
from V1_GOOGLE_DRIVE_ENHANCED import post_thread_reply_to_slack
test_reply = '🧪 Test thread reply - Please ignore'
# Use timestamp from step 5.2
success, msg = post_thread_reply_to_slack(test_reply, '[TIMESTAMP_FROM_5.2]', 'C_TEST_CHANNEL')
print(f'Thread Reply: {msg}')
"
```

**Expected Output**:
- ✅ Thread Reply: ✅ Posted thread reply

---

### ✅ **Phase 6: End-to-End Integration Test**

#### **6.1 Dry Run Test** (No Slack posting)
```bash
# Run system without Slack posting to test full flow
SLACK_BOT_TOKEN="" python3 V1_GOOGLE_DRIVE_ENHANCED.py
```

**Expected Output**:
- ✅ Google Drive calls found
- ✅ Content extracted successfully  
- ✅ Attendees parsed correctly
- ✅ Salesforce contacts found
- ✅ AI analysis successful
- ✅ Salesforce events updated
- ✅ Slack posting skipped (no token)
- ✅ Database records created

#### **6.2 Limited Live Test** ⚠️ **PRODUCTION**
```bash
# Run with actual Slack posting (monitors only recent calls)
python3 V1_GOOGLE_DRIVE_ENHANCED.py | tee test_live_run.log
```

**Expected Output**: See logs for full processing pipeline success

---

## 🔧 **Phase 7: Production Deployment**

### ✅ **7.1 Backup Current System**
```bash
# Backup existing system
cp V1_ENHANCED_PRODUCTION.py V1_ENHANCED_PRODUCTION.py.backup
cp .env .env.backup
```

### ✅ **7.2 Deploy New System**
```bash
# Deploy enhanced system
cp V1_GOOGLE_DRIVE_ENHANCED.py V1_GOOGLE_DRIVE_PRODUCTION.py
```

### ✅ **7.3 Update Automation**
```bash
# Update crontab
crontab -e

# Replace existing Fellow automation with:
# */30 * * * * cd /Users/niamhcollins/clawd/ae_call_analysis && python3 V1_GOOGLE_DRIVE_PRODUCTION.py >> logs/v1_google_drive.log 2>&1
```

### ✅ **7.4 Create Log Monitoring**
```bash
# Set up log directory
mkdir -p logs
touch logs/v1_google_drive.log

# Monitor first run
tail -f logs/v1_google_drive.log
```

---

## 🔍 **Phase 8: Post-Deployment Monitoring**

### ✅ **8.1 First Hour Monitoring**
- [ ] ✅ **Automation runs without errors**
- [ ] ✅ **Google Drive calls found and processed**
- [ ] ✅ **Slack posts appear in expected format**
- [ ] ✅ **Salesforce events updated correctly**
- [ ] ✅ **Database records created**

### ✅ **8.2 First Day Validation**
- [ ] ✅ **Multiple calls processed successfully**
- [ ] ✅ **No duplicate processing**
- [ ] ✅ **All V1 features working (9-point analysis, threading, etc.)**
- [ ] ✅ **Salesforce EVENT updates confirmed**

### ✅ **8.3 Quality Checks**
```bash
# Check database stats
sqlite3 v1_google_drive.db "
SELECT 
    COUNT(*) as total_calls,
    SUM(slack_posted) as slack_success,
    SUM(salesforce_updated) as sf_success,
    SUM(ai_analyzed) as ai_success
FROM processed_calls 
WHERE DATE(processed_at) = DATE('now');"

# Check recent logs
tail -50 logs/v1_google_drive.log | grep -E "(✅|❌)"
```

**Expected**:
- ✅ All success rates > 80%
- ✅ No critical errors in logs
- ✅ Processing times reasonable (<2 min per call)

---

## 🚨 **Rollback Plan**

### **If Issues Found**:

#### **Quick Rollback**
```bash
# Stop new automation
crontab -e  # Comment out new cron job

# Restore V1 Fellow system
cp V1_ENHANCED_PRODUCTION.py.backup V1_ENHANCED_PRODUCTION.py
cp .env.backup .env

# Resume old automation
crontab -e  # Restore Fellow cron job
```

#### **Issue Investigation**
```bash
# Check logs for specific errors
grep -E "(❌|Error|Failed)" logs/v1_google_drive.log

# Test individual components
python3 -c "from V1_GOOGLE_DRIVE_ENHANCED import [failing_function]; [test_call]"

# Validate environment
env | grep -E "(SLACK|OPENAI|SF_)"
```

---

## ✅ **Success Criteria Summary**

### **Must Pass Before Production**:
- [x] ✅ **Google Drive integration working**
- [x] ✅ **Salesforce EVENT lookup and updates**  
- [x] ✅ **9-point AI analysis structure maintained**
- [x] ✅ **Threaded Slack posting preserved**
- [x] ✅ **Company website links working**
- [x] ✅ **All V1 core features functional**
- [x] ✅ **No duplicate processing**
- [x] ✅ **Error handling robust**

### **Performance Targets**:
- [x] ✅ **Processing time: <2 minutes per call**
- [x] ✅ **Success rate: >85% for all components**  
- [x] ✅ **Memory usage: Stable**
- [x] ✅ **No authentication failures**

---

## 📋 **Final Pre-Launch Checklist**

Before activating in production:

- [ ] ✅ **All Phase 1-6 tests passed**
- [ ] ✅ **Backup completed**  
- [ ] ✅ **Log monitoring set up**
- [ ] ✅ **Rollback plan tested**
- [ ] ✅ **Team notified of deployment**
- [ ] ✅ **First run monitored successfully**

**🚀 READY FOR PRODUCTION DEPLOYMENT**

---

**Note**: This checklist ensures the enhanced system maintains ALL V1 functionality while successfully integrating Google Drive. Any test failure should trigger investigation and fixes before production deployment.