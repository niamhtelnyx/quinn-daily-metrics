# 🚀 Migration Plan: Restore AE Call Intelligence System

**Migration Date**: March 4, 2025  
**Engineer**: Senior Software Engineer  
**Target**: V1 functionality + Google Drive integration  
**Approach**: Build on proven V1 foundation, not V2 experiments

---

## 📋 Migration Overview

**Strategy**: Take V1's **working Salesforce + AI + Slack code** and replace only the Fellow API with Google Drive integration from V2. This preserves all working functionality while solving the data source requirement.

**Timeline**: 2-3 hours of focused engineering  
**Risk Level**: LOW (building on proven code)

---

## 🎯 Phase 1: Analysis Complete ✅ 

- [x] **Analyzed V1 working system** (`V1_ENHANCED_PRODUCTION.py`)
- [x] **Analyzed V2 broken systems** (multiple files)
- [x] **Documented gaps and losses** (`SYSTEM_ANALYSIS.md`)
- [x] **Identified migration approach** (V1 + Google Drive)

---

## 🔧 Phase 2: Code Migration (NEXT)

### **Step 1: Create V1 Google Drive Enhanced** (30 minutes)

**File**: `V1_GOOGLE_DRIVE_ENHANCED.py`

#### **2.1 Copy V1 Working Components**
```bash
# Start with proven V1 foundation
cp V1_ENHANCED_PRODUCTION.py V1_GOOGLE_DRIVE_ENHANCED.py
```

#### **2.2 Replace Data Source Functions**

**Remove from V1**:
- `get_fellow_intro_calls()` 
- `get_fellow_transcript()`

**Add from V2 (proven working)**:
- `get_recent_gemini_calls()` from `V2_RECENT_CALLS_ONLY.py`
- `get_google_doc_content()` from `V2_RECENT_CALLS_ONLY.py`
- `format_enhanced_google_drive_call()` from `V2_RECENT_CALLS_ONLY.py`

#### **2.3 Preserve All V1 Core Functions** ✅
- ✅ `analyze_call_with_ai()` - Keep V1's 9-point structure
- ✅ `find_salesforce_contact_enhanced()` - Keep company data extraction
- ✅ `find_or_update_salesforce_event()` - Keep EVENT record functionality
- ✅ `post_to_slack_bot_api()` + `post_thread_reply_to_slack()` - Keep threading
- ✅ `get_company_summary_with_ai()` - Keep company intelligence

#### **2.4 Integration Points**
```python
# Replace this V1 pattern:
calls, status = get_fellow_intro_calls()
transcript, msg = get_fellow_transcript(call)

# With this V2 pattern:
calls, status = get_recent_gemini_calls(TARGET_FOLDER_ID, hours_back=2)
content, msg = get_google_doc_content(call['id'])
formatted_call = format_enhanced_google_drive_call(call, content)
```

### **Step 2: Update Main Processing Loop** (15 minutes)

#### **2.1 Modify Loop Structure**
```python
def run_enhanced_automation():
    # V1 Salesforce token (keep)
    access_token, auth_msg = get_salesforce_token()
    
    # V2 Google Drive calls (replace)
    calls, status = get_recent_gemini_calls(TARGET_FOLDER_ID, hours_back=2)
    
    for call in calls:
        # V2 Google Drive processing (new)
        content, content_msg = get_google_doc_content(call['id'])
        formatted_call = format_enhanced_google_drive_call(call, content)
        
        prospect_name = formatted_call['prospect_name']
        
        # V1 Salesforce integration (keep)
        contact_data, contact_msg = find_salesforce_contact_enhanced(prospect_name, access_token)
        
        # V1 AI analysis with company data (keep)  
        ai_analysis = analyze_call_with_ai(content, prospect_name, 
                                          contact_data.get('company_name', ''),
                                          contact_data.get('company_website', ''))
        
        # V1 Salesforce event update (keep)
        event_id, event_msg = find_or_update_salesforce_event(contact_data, prospect_name, 
                                                              call['id'], access_token)
        
        # V1 threaded Slack posting (keep)
        if ai_analysis.get('status') == 'success':
            main_post = ai_analysis['main_post'] 
            slack_success, slack_msg = post_to_slack_bot_api(main_post)
            
            if slack_success and ai_analysis.get('thread_reply'):
                ts_match = re.search(r'ts: ([\d.]+)', slack_msg)
                if ts_match:
                    parent_ts = ts_match.group(1)
                    thread_reply = ai_analysis['thread_reply']
                    post_thread_reply_to_slack(thread_reply, parent_ts)
```

### **Step 3: Add Google Drive Configuration** (5 minutes)

#### **3.1 Add Google Drive Folder Configuration**
```python
# Add to top of file
TARGET_FOLDER_ID = "1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY"  # From V2

def run_gog_command(cmd):
    """Run gog CLI command - from V2_RECENT_CALLS_ONLY.py"""
    # Copy proven working implementation
```

#### **3.2 Environment Integration**
```python
def load_env():
    """Enhanced environment loading for both .env and .env.gog"""
    # Load existing .env
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    # Load .env.gog for Google Drive (from V2)
    gog_env_path = '/Users/niamhcollins/clawd/.env.gog'
```

### **Step 4: Update Database Schema** (10 minutes)

#### **4.1 Enhance Database for Google Drive**
```python
def mark_call_processed(call_id, prospect_name, slack_success, sf_success, ai_success, source='google_drive'):
    """Enhanced to track source"""
    cursor.execute('''
        INSERT OR REPLACE INTO processed_calls 
        (call_id, prospect_name, processed_at, slack_posted, salesforce_updated, 
         ai_analyzed, source, dedup_key)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (call_id, prospect_name, datetime.now().isoformat(), 
          slack_success, sf_success, ai_success, source, dedup_key))
```

---

## 🔧 Phase 3: Testing & Validation (30 minutes)

### **Step 1: Unit Testing**

#### **3.1 Test Google Drive Integration**
```bash
cd /Users/niamhcollins/clawd/ae_call_analysis

# Test Google Drive connection
python3 -c "
from V1_GOOGLE_DRIVE_ENHANCED import get_recent_gemini_calls, TARGET_FOLDER_ID
calls, status = get_recent_gemini_calls(TARGET_FOLDER_ID, hours_back=24)
print(f'Found {len(calls)} calls: {status}')
"
```

#### **3.2 Test Content Extraction** 
```bash
# Test content extraction from a known doc
python3 -c "
from V1_GOOGLE_DRIVE_ENHANCED import get_google_doc_content
content, error = get_google_doc_content('KNOWN_DOC_ID')
print(f'Content length: {len(content) if content else 0}')
print(f'Error: {error}')
"
```

### **Step 2: Integration Testing**

#### **3.3 Test Salesforce Integration**
```bash
# Test Salesforce token and contact search
python3 -c "
from V1_GOOGLE_DRIVE_ENHANCED import get_salesforce_token, find_salesforce_contact_enhanced
token, msg = get_salesforce_token()
print(f'Salesforce: {msg}')
if token:
    contact, msg = find_salesforce_contact_enhanced('Test Contact', token)
    print(f'Contact search: {msg}')
"
```

#### **3.4 Test AI Analysis Structure**
```bash
# Test that AI analysis maintains V1 format
python3 -c "
from V1_GOOGLE_DRIVE_ENHANCED import analyze_call_with_ai
test_content = 'Test call transcript...'
analysis = analyze_call_with_ai(test_content, 'Test Prospect')
print(f'Analysis status: {analysis.get(\"status\")}')
print(f'Has main_post: {\"main_post\" in analysis}')
print(f'Has thread_reply: {\"thread_reply\" in analysis}')
"
```

### **Step 3: End-to-End Testing**

#### **3.5 Dry Run Test**
```bash
# Run system in test mode (no Slack posting)
SLACK_BOT_TOKEN="" python3 V1_GOOGLE_DRIVE_ENHANCED.py
```

#### **3.6 Single Call Test**
```bash
# Test with one known recent call
python3 V1_GOOGLE_DRIVE_ENHANCED.py | tee test_run_output.txt
# Review output for all expected functionality
```

---

## 🔧 Phase 4: Deployment (15 minutes)

### **Step 1: Environment Preparation**

#### **4.1 Backup Current System**
```bash
# Backup any existing automation
cp V1_ENHANCED_PRODUCTION.py V1_ENHANCED_PRODUCTION.py.backup
cp .env .env.backup
```

#### **4.2 Validate Environment Variables**
```bash
# Ensure all required environment variables exist
grep -E "^(FELLOW_API_KEY|SLACK_BOT_TOKEN|OPENAI_API_KEY|SF_CLIENT_ID|SF_CLIENT_SECRET)" .env
```

### **Step 2: Production Deployment**

#### **4.3 Deploy Enhanced System**
```bash
# Replace production system
mv V1_GOOGLE_DRIVE_ENHANCED.py V1_GOOGLE_DRIVE_PRODUCTION.py
```

#### **4.4 Update Cron Job**
```bash
# Update crontab to use new system
crontab -e

# Replace Fellow-based automation with:
# */30 * * * * cd /Users/niamhcollins/clawd/ae_call_analysis && python3 V1_GOOGLE_DRIVE_PRODUCTION.py >> logs/v1_google_drive.log 2>&1
```

### **Step 3: Monitoring Setup**

#### **4.5 Create Log Directory**
```bash
mkdir -p logs
touch logs/v1_google_drive.log
```

#### **4.6 Monitor First Run**
```bash
# Watch logs for first automated run
tail -f logs/v1_google_drive.log
```

---

## 🔧 Phase 5: Git Workflow (10 minutes)

### **Step 1: Branch Management**

#### **5.1 Create Feature Branch**
```bash
cd /Users/niamhcollins/clawd/ae_call_analysis
git status
git checkout -b feature/v1-google-drive-integration

# Add all new files
git add V1_GOOGLE_DRIVE_ENHANCED.py SYSTEM_ANALYSIS.md MIGRATION_PLAN.md DEPLOYMENT_CHECKLIST.md
```

#### **5.2 Commit Changes**
```bash
git commit -m "feat: V1 enhanced with Google Drive integration

- Add V1_GOOGLE_DRIVE_ENHANCED.py (V1 + Google Drive)
- Replace Fellow API with Google Drive integration  
- Preserve all V1 Salesforce EVENT functionality
- Maintain 9-point AI analysis structure
- Keep threaded Slack posting format
- Add engineering analysis and migration docs

Closes: V2 functionality gaps
Maintains: All V1 proven features
"
```

### **Step 2: Repository Management**

#### **5.3 Push to Remote**
```bash
# Push feature branch
git push origin feature/v1-google-drive-integration
```

#### **5.4 Create Pull Request**
```bash
# Create PR with proper description:
# Title: V1 Enhanced Call Intelligence with Google Drive Integration  
# Description: Restores full functionality lost in V2, adds Google Drive source
```

---

## 📊 Success Criteria Verification

### **Must Have (All V1 Features)**
- [ ] ✅ **Salesforce EVENT lookup and updates**
- [ ] ✅ **9-point AI analysis structure (main post + thread)**
- [ ] ✅ **Threaded Slack posting**  
- [ ] ✅ **Company website links (`<URL|Company>` format)**
- [ ] ✅ **Company AI summaries**
- [ ] ✅ **Salesforce contact search with account data**
- [ ] ✅ **Call deduplication**
- [ ] ✅ **Database tracking**

### **New Requirements**
- [ ] ✅ **Google Drive integration (not Fellow)**
- [ ] ✅ **Recent calls filtering (efficiency)**
- [ ] ✅ **Quality control validation**

### **Technical Requirements**
- [ ] ✅ **Proper git workflow (feature branch, commits, PR)**
- [ ] ✅ **Environment configuration**
- [ ] ✅ **Error handling and logging**
- [ ] ✅ **Documentation (analysis, plan, checklist)**

---

## ⚠️ Risk Mitigation

### **Low Risk Areas** ✅
- **V1 Core Functions**: Already proven and working
- **Google Drive Integration**: Working in V2_RECENT_CALLS_ONLY.py
- **Database**: Simple schema enhancement

### **Medium Risk Areas** ⚠️
- **Integration Points**: Where V1 and V2 code merge
- **Environment Setup**: Both .env and .env.gog dependencies
- **AI Prompt Compatibility**: Ensure prompts work with Google Drive content

### **Mitigation Strategies**
1. **Extensive Testing**: Test each component individually, then integrated
2. **Rollback Plan**: Keep V1_ENHANCED_PRODUCTION.py as fallback
3. **Gradual Deployment**: Test with limited calls before full automation
4. **Monitoring**: Watch logs closely for first 24 hours

---

## 📈 Timeline Summary

| Phase | Duration | Status |
|-------|----------|--------|
| **Analysis** | 1 hour | ✅ Complete |
| **Code Migration** | 1 hour | 🔄 Next |
| **Testing** | 30 min | ⏳ Pending |
| **Deployment** | 15 min | ⏳ Pending |  
| **Git Workflow** | 10 min | ⏳ Pending |
| **Total** | **2h 55min** | 🎯 **Target** |

---

## 🎯 Next Action

**IMMEDIATE NEXT STEP**: Begin Phase 2 - Create `V1_GOOGLE_DRIVE_ENHANCED.py` by copying V1 and replacing data source functions with proven V2 Google Drive integration code.

This approach minimizes risk by building on proven foundations while achieving all requirements.