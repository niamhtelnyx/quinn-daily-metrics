# 📋 V1 Enhanced Call Intelligence - PROJECT CONTEXT

## 🎯 **CANONICAL REPOSITORY**

**⚠️ IMPORTANT**: This project ALWAYS belongs to:

```
Repository: https://github.com/team-telnyx/meeting-sync
Branch: v1-release
Team: Telnyx RevOps/Sales Operations
```

## 🔄 **GIT CONFIGURATION**

**Correct Remote Setup:**
```bash
git remote -v
# Should show:
meeting-sync    https://github.com/team-telnyx/meeting-sync.git (fetch)
meeting-sync    https://github.com/team-telnyx/meeting-sync.git (push)
```

**Default Push Target:**
```bash
git push  # Always goes to team-telnyx/meeting-sync
```

## ❌ **INCORRECT REPOSITORIES**

**Do NOT push to:**
- `niamhtelnyx/quinn-daily-metrics` (personal repo)
- `team-telnyx/revops-squad` (different project)
- Any other repository

## 📁 **PROJECT STRUCTURE**

```
team-telnyx/meeting-sync/
├── v1-release branch              ← Main deployment branch
├── ae_call_analysis/              ← Core project folder
├── fellow_cron_job.py             ← Main production script
├── V1_ENHANCED_PRODUCTION.py      ← Production backup
└── PROJECT_CONTEXT.md             ← This context file
```

## 🎯 **PROJECT IDENTITY**

**Name**: V1 Enhanced Call Intelligence  
**Purpose**: Automated Fellow → Slack + Salesforce integration with AI analysis  
**Owner**: Telnyx Sales Operations Team  
**Repository**: team-telnyx/meeting-sync  
**Deployment**: Production operational via automated cron/launchctl  

## 📈 **CURRENT STATUS**

**Features Deployed to team-telnyx/meeting-sync:**
✅ Working Fellow transcript extraction  
✅ AI-powered call analysis (9-point structure)  
✅ Original threaded Slack format (main post + thread)  
✅ Company summaries with clickable hyperlinks  
✅ Live monitoring (today's calls only)  
✅ Enhanced Salesforce integration  
✅ Production automation every 30 minutes  

## 🔧 **DEVELOPMENT WORKFLOW**

1. **Work locally** in ae_call_analysis/ folder
2. **Test changes** with python3 fellow_cron_job.py
3. **Commit changes** to v1-release branch
4. **Push to team repo**: `git push meeting-sync v1-release`
5. **Never push to personal repos**

## 📋 **MEMORY REFERENCE**

**For future sessions**: This Call Intelligence project is part of the Telnyx team repository ecosystem, specifically team-telnyx/meeting-sync, not any personal repositories. All deployments, documentation, and collaboration happen through the team repository.

---

**🎯 REMEMBER**: team-telnyx/meeting-sync is the single source of truth for this project.