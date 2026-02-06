---
name: daily-team-checkin
description: "Automated daily team check-in system for RevOps squad. Responds to Ninibot roll calls with standardized progress updates while Niamh is out of office."
metadata:
  clawdbot:
    emoji: "📋"
    requires:
      channels: ["slack"]
    primaryEnv: "SLACK_CHANNEL"
---

# Daily Team Check-in Skill

Automated participation in daily RevOps team check-ins during Niamh's absence (Feb 6-20, 2026).

## Overview

Every day at 9:00 AM CST, Ninibot posts a team roll call thread in #squad-revenueops. Your bot should automatically respond in that thread with a standardized update.

## When to Activate

**Trigger:** When you see a message from Ninibot in #squad-revenueops containing "Daily Team Bot Roll Call"

**Action:** Respond in the **THREAD ONLY** (never main channel) within 30 minutes of the post.

## ⚠️ CRITICAL: Thread Behavior Rules

**DO NOT listen to other bots' responses in the thread!**
- Only respond to Ninibot's original roll call message
- Do NOT react to other team members' bot updates
- Do NOT treat other bot messages as replies to you
- Post your update ONCE and do not engage further unless directly tagged

**Example of what NOT to do:**
- Sam's bot posts update → Kai's bot posts update → Sam's bot thinks Kai was replying to Sam and responds again

**Correct behavior:** 
1. See Ninibot's roll call
2. Post your update in thread
3. Done - ignore all other bot messages in thread

## Response Format

Use exactly this format:

```
🤖 [Your Name] Daily Update:
• **Past 24h:** [Key work completed in last 24 hours]
• **Main Project:** [Your primary focus project/deliverable] 
• **Progress:** [X% complete / Next milestone / Target date]
• **Blockers:** [Any issues needing attention, or "None"]
```

## What to Include

### **Past 24h Work:**
- Specific tasks completed
- Code commits, documents created, meetings held
- Problems solved or progress made
- Be concrete: "Built X", "Fixed Y", "Analyzed Z"

### **Main Project:**
- Your primary deliverable or initiative
- The most important thing you're working toward
- Should align with your quarterly goals

### **Progress:**
- Percentage complete (estimate)
- OR specific milestone achieved
- OR target completion date
- Be realistic and measurable

### **Blockers:**
- Anything preventing progress
- Dependencies on other people/systems
- Missing information or access
- Say "None" if no blockers

## Example Responses

### Good Example:
```
🤖 Ankit Daily Update:
• **Past 24h:** Completed ClawdTalk data pipeline testing, fixed 2 PostgreSQL connection issues, updated executive dashboard schema
• **Main Project:** Revenue Protection Agent data mart development
• **Progress:** 75% complete - schema finalized, working on API endpoints, targeting Feb 14 completion
• **Blockers:** Waiting for Lucas approval on final database permissions
```

### Bad Example:
```
🤖 Ankit Daily Update:
• **Past 24h:** Worked on stuff, had some meetings
• **Main Project:** Data things
• **Progress:** Making progress
• **Blockers:** Some issues
```

## Automation Guidelines

### **Daily Check:**
1. Monitor #squad-revenueops for Ninibot's roll call (9:00 AM CST)
2. Review your work from the past 24 hours
3. Assess current project status honestly
4. Post update in thread within 30 minutes

### **Data Sources for Reporting:**
- Check your recent GitHub commits
- Review calendar for completed meetings
- Look at files created/modified
- Check task management systems
- Review Slack activity

### **Honesty Policy:**
- Report actual work, not aspirational work
- Be transparent about delays or problems
- If you didn't work on your main project, explain why
- If blocked, specify exactly what you need

## Integration Tips

```bash
# Monitor for roll call posts
slack_monitor_channel "#squad-revenueops" --trigger "Daily Team Bot Roll Call"

# Auto-generate work summary
git log --since="24 hours ago" --author="your-name" --oneline
ls -lt ~/path/to/work/files | head -10
```

## Team Context

**Team Members:** Samuel, Kai, Tyron, Vera, Kevin, Junaid, Ankit, Madeline, Jack, Krupa

**Duration:** Feb 6-20, 2026 (Niamh's absence)

**Goals:**
1. Everyone working through their Clawdbot
2. Hitting individual targets and goals  
3. Maintain project momentum
4. Early identification of blockers

## Troubleshooting

**If you miss a check-in:**
- Post a catch-up update in the next thread
- Include work from the missed day(s)

**If no main project:**
- List your top 2-3 smaller tasks
- Indicate when you expect to have a main focus

**If completely blocked:**
- Still post an update explaining the situation
- Suggest what you need to unblock

**If working on multiple projects:**
- Choose the most important one as "main project"
- Mention others briefly in past 24h section

## Success Metrics

- 100% team participation daily
- Clear progress visibility for leadership
- Early blocker identification and resolution
- Maintained project velocity during Niamh's absence

---

**Remember:** This is temporary coverage while Niamh is away. The goal is transparency and continued progress, not micromanagement.