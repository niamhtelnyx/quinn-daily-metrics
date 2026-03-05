# AE Call Analysis - Project Structure

## 🏗️ **Current Production System**

### **🟢 ACTIVE PRODUCTION FILES**
```
V1_WORKING_FINAL.py           ← CURRENT PRODUCTION SYSTEM (15-min intervals)
V1_15MIN_WRAPPER.py           ← 15-minute wrapper that calls main system  
fellow_cron_job.py            ← Cron bridge script (calls wrapper)
```

### **🔧 Configuration & Environment**
```
.env                          ← API credentials (Salesforce, Slack, etc.)
/Users/niamhcollins/clawd/.env.gog  ← Google OAuth credentials  
.env.example                  ← Template for environment setup
```

### **📊 Active Database**
```
v1_working_final.db           ← Current production database
```

## 📚 **Historical Development Versions**

### **V1 Evolution (Google Drive Integration)**
```
V1_ENHANCED_PRODUCTION.py     ← Original sophisticated Slack format (reference)
V1_GOOGLE_DRIVE_ENHANCED.py   ← Engineering subagent's V1 restoration  
V1_DATE_HIERARCHY.py          ← Date-based folder discovery
V1_DATE_FULL.py               ← Complete date hierarchy processing
V1_DATE_FULL_FUZZY.py         ← Added fuzzy Salesforce matching (caused hanging)
V1_USEFUL_SLACK.py            ← Simplified Slack format (replaced)
V1_CORRECT_SLACK_FORMAT.py    ← Attempt to restore original format
V1_FIXED_CONTENT.py           ← Content extraction fixes
V1_WORKING_FINAL.py           ← CURRENT: Working content + original format
```

### **V2 Unified System (Deprecated)**
```
V2_UNIFIED_PRODUCTION.py      ← Combined Fellow + Google Drive
V2_FINAL_PRODUCTION.py        ← Enhanced V2 version  
V2_FOLDER_SPECIFIC.py         ← Folder-targeted processing
V2_RECENT_CALLS_ONLY.py       ← Last 2 hours only processing
```

### **V3 Async System (Future)**
```
V3_ASYNC_PRODUCTION.py        ← Parallel processing (not in production)
```

## 🔍 **Debug & Testing Scripts**

### **System Testing**
```
test_15min_wrapper.py         ← Test wrapper functionality
test_working_system.py        ← Test complete system
debug_production_scenario.py  ← Debug production issues
debug_hanging_issues.py       ← Investigate system hanging
```

### **Content Extraction Testing**
```
debug_content_extraction.py   ← Debug Google Drive content issues
test_run_gog_command.py       ← Test gog CLI commands
```

### **Salesforce Integration Testing**
```
debug_salesforce_400.py       ← Debug Salesforce API issues
test_sf_links.py              ← Test Salesforce link generation
check_sf_events.py            ← Check Salesforce event matching
```

### **Slack Integration Testing**
```
test_slack_posting.py         ← Test Slack message posting
test_slack_simple.py          ← Simple Slack tests
quick_slack_test.py           ← Quick Slack verification
```

## 📋 **Documentation & Analysis**

### **Project Documentation**
```
PROJECT_CONTEXT.md            ← High-level project overview
SYSTEM_ANALYSIS.md            ← Engineering subagent's analysis
MIGRATION_PLAN.md             ← V1 to enhanced system migration
DEPLOYMENT_CHECKLIST.md       ← Deployment procedures
```

### **Development Tracking**
```
BULK_PROCESSING_ANALYSIS.md   ← Performance analysis
TOMORROW_TESTING_PLAN.md      ← Testing strategies
PRODUCTION_DEPLOY.md          ← Production deployment notes
```

### **Slack Integration Docs**
```
ENHANCED_SLACK_PREVIEW.md     ← Slack message format examples
SLACK_BOT_SETUP_GUIDE.md      ← Bot configuration guide
```

## 🗄️ **Database Files**

### **Production Databases**
```
v1_working_final.db           ← Current active database
ae_call_analysis.db           ← Legacy main database (1.3MB)
```

### **Development Databases**  
```
v1_date_full.db               ← Date hierarchy testing
v1_useful_slack.db            ← Simplified format testing
v1_working_hierarchy.db       ← Hierarchy processing testing
v2_final.db                   ← V2 system database
```

## 🚀 **Control Scripts**

### **Production Management**
```
start_system.sh               ← Start production system
force_15min_cron.sh           ← Force 15-minute cron setup
fellow_cron_job.py            ← Main cron entry point
```

### **V2 System Control (Deprecated)**
```
v2_control.sh                 ← V2 system management
run_v2_sales_calls.sh         ← V2 Slack posting
stop_v2_live.sh              ← Stop V2 background processes
```

## 📂 **Directories**

### **Logs**
```
logs/                         ← System execution logs
├── cron_*.log               ← Cron job outputs
├── v1_*.log                 ← V1 system logs
└── debug_*.log              ← Debug session logs
```

### **Data**
```
data/                         ← Temporary data storage
└── temp files from processing
```

## 🎯 **Current System Flow**

```
MacOS Cron (every 30 min)
    ↓
fellow_cron_job.py (bridge script)
    ↓  
V1_15MIN_WRAPPER.py (runs twice per 30min cycle)
    ↓
V1_WORKING_FINAL.py (main processing)
    ↓
1. Get Google Drive meetings (today's date folder)
2. Extract real content from Gemini notes  
3. Generate original sophisticated Slack format
4. Post main + threaded reply to #sales-calls
5. Store in v1_working_final.db
```

## 🔧 **Key Features Currently Working**

- ✅ **15-minute effective intervals** (via wrapper approach)
- ✅ **Real content extraction** from Google Drive  
- ✅ **Original sophisticated Slack format** with threading
- ✅ **Deduplication** to prevent repeat posts
- ✅ **Automatic date folder discovery** (2026-03-05 → 2026-03-06)
- ✅ **Error handling** with timeouts and graceful failures
- ✅ **Database tracking** of all processed calls

## 🛠️ **Recent Major Changes**

1. **Fixed content extraction** - Now gets real meeting content instead of file paths
2. **Restored original Slack format** - Back to sophisticated main post + detailed thread
3. **Implemented 15-minute intervals** - Wrapper approach bypasses macOS crontab restrictions  
4. **Enhanced error handling** - Prevents system hanging that caused SIGKILL issues
5. **Real-time date discovery** - Automatically processes new date folders as they appear

---

**Current Status**: ✅ **Fully Operational** - Processing 10 meetings per cycle with 100% success rate