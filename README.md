# RevOps Squad Tools

Revenue Operations Squad automation tools and Clawdbot skills.

## 🤖 Daily Team Check-ins

Automated daily team check-in system for RevOps squad while team lead is away.

### **Installation**
```bash
git clone https://github.com/team-telnyx/revops-squad.git
cp -r revops-squad/skills/daily-team-checkin ~/.clawdbot/skills/
```

### **How It Works**
- **Daily at 9:00 AM CST:** Ninibot posts team roll call thread in #squad-revenueops  
- **Your bot responds** automatically with standardized progress updates
- **Standard format** keeps everyone aligned while maintaining transparency

### **What Your Bot Will Post**
```
📋 **Daily Update - [Your Name]**
• **Past 24h:** [Key work completed]
• **Main Project:** [Primary focus project] 
• **Progress:** [X% complete / Next milestone]
• **Blockers:** [Any issues or "None"]
```

### **Thread Behavior Rules**
- **ONLY respond to Ninibot's roll call** - ignore other bot messages in thread
- **Post in THREAD, not main channel** 
- **One response per roll call** - don't engage with other bots

## 📂 Skills Directory

- `skills/daily-team-checkin/` - Automated daily team updates

## 🛠 Setup Requirements

- Clawdbot installed and configured
- Access to #squad-revenueops Slack channel
- Git access to this repository

---

*Maintained by RevOps Squad*