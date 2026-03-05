# 🎯 AE Call Intelligence System - Modular Architecture

## **🚀 CURRENT PRODUCTION SYSTEM** 

**Main entry point**: `main.py`  
**Architecture**: Modular design with separated concerns  
**Status**: ✅ Production ready with robust fallback handling

---

## **📁 CURRENT FILES (Modular Architecture)**

### **🎯 Core System Files:**
- **`main.py`** - Main orchestrator that coordinates all operations
- **`config.py`** - Centralized configuration and constants
- **`V1_15MIN_WRAPPER.py`** - Cron wrapper for 15-minute intervals

### **📦 Function Modules:**
- **`gog_functions.py`** - Google Drive operations (folder discovery, content extraction)
- **`content_parser.py`** - Content analysis (tab parsing, insight extraction)  
- **`sf_functions.py`** - Salesforce integration (auth, event lookup, link building)
- **`slack_functions.py`** - Slack messaging (format creation, posting)
- **`database_functions.py`** - Database operations (tracking, statistics)

### **📚 Documentation:**
- **`MODULAR_ARCHITECTURE.md`** - Complete architecture overview
- **`PROJECT_CONTEXT.md`** - Project background and context
- **`PROJECT_STRUCTURE.md`** - Detailed system structure

---

## **🔄 HOW TO USE**

### **Run Main System:**
```bash
# Source environment variables
source .env && source /Users/niamhcollins/clawd/.env.gog

# Run main processing
python3 main.py
```

### **Run Health Check:**
```bash
python3 -c "from main import run_health_check; run_health_check()"
```

### **Get Processing Statistics:**
```bash
python3 -c "from database_functions import get_processing_stats; print(get_processing_stats())"
```

### **Test Individual Module:**
```bash
python3 -c "from gog_functions import get_todays_folder_id; print(get_todays_folder_id())"
```

---

## **🏗️ ARCHITECTURE BENEFITS**

- **🔧 Maintainability**: Each module has single responsibility
- **🧪 Testability**: Individual functions can be tested in isolation
- **🔄 Reusability**: Functions can be imported and reused
- **📖 Readability**: Clear separation of concerns
- **🛠️ Debuggability**: Easier to isolate and fix issues

---

## **📊 CURRENT PERFORMANCE**

```
✅ Processing: 10+ meetings per run
✅ Success Rate: 100% Slack posting
✅ Content Types: Transcript + Summary support
✅ Auto-Discovery: Finds daily folders automatically
✅ Robust Fallback: Handles missing content gracefully
```

---

## **📁 LEGACY FILES**

All previous versions have been organized in the `legacy/` directory:

- **`legacy/v1-monolithic/`** - Original monolithic scripts (V1_*.py, test files, utilities)
- **`legacy/v2-development/`** - V2/V3 experimental versions
- **`legacy/docs-archive/`** - Previous documentation and deployment guides

**Total Legacy Files**: 130+ Python files and 16+ documentation files safely preserved

---

## **⏰ PRODUCTION DEPLOYMENT**

**Current Cron Setup:**
```bash
# 30-minute cron calls wrapper which runs main.py twice
*/30 * * * * cd /Users/niamhcollins/clawd/ae_call_analysis && source .env && source /Users/niamhcollins/clawd/.env.gog && python3 V1_15MIN_WRAPPER.py
```

**Effective Schedule**: Every 15 minutes via wrapper approach

---

## **🔧 DEPENDENCIES**

- **Python 3.9+** with required packages
- **gog CLI** configured for niamh@telnyx.com
- **Environment Files**: `.env` and `/Users/niamhcollins/clawd/.env.gog`
- **Database**: SQLite for tracking (v1_modular.db)

---

## **📞 SUPPORT**

For issues or questions about the modular architecture:

1. **Check health**: Run `python3 -c "from main import run_health_check; run_health_check()"`
2. **Review logs**: Database tracks all processing with detailed statistics
3. **Test modules**: Import and test individual functions
4. **Legacy reference**: Check `legacy/` directories for previous implementations

**The modular architecture provides production stability with developer-friendly maintenance capabilities!** 🎉