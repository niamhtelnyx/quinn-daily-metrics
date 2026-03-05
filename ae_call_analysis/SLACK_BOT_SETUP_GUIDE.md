# 🤖 SLACK BOT TOKEN SETUP GUIDE

## **OPTION 1: Use Existing Clawdbot Slack App (Recommended)**

If Clawdbot is already connected to your Slack workspace:

### Step 1: Find the Existing Bot Token
1. Go to https://api.slack.com/apps
2. Look for "Clawdbot" or similar app name
3. Click on the app
4. Go to **OAuth & Permissions** in left sidebar
5. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### Step 2: Add Token to Environment
```bash
# Add this line to .env
SLACK_BOT_TOKEN=xoxb-your-token-here
```

---

## **OPTION 2: Create New Slack App (If Needed)**

If you need a new bot for Call Intelligence:

### Step 1: Create Slack App
1. Go to https://api.slack.com/apps
2. Click **Create New App**
3. Choose **From scratch**
4. App Name: "Call Intelligence Bot"
5. Workspace: Select your Telnyx workspace

### Step 2: Configure Bot Permissions
1. Go to **OAuth & Permissions**
2. Under **Scopes** → **Bot Token Scopes**, add:
   - `chat:write` (send messages)
   - `chat:write.public` (send to channels without joining)
   
### Step 3: Install Bot to Workspace
1. Click **Install to Workspace**
2. Authorize the app
3. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### Step 4: Add Token to Environment
```bash
# Add this line to .env
SLACK_BOT_TOKEN=xoxb-your-copied-token
```

---

## **WHICH DO YOU PREFER?**

**Option 1 (Use existing)**: Faster, leverages existing Clawdbot setup
**Option 2 (Create new)**: Dedicated bot for Call Intelligence

---

## **TESTING THE SETUP**

Once you add the token:

```bash
cd ae_call_analysis
python3 slack_bot_integration.py
```

Should show:
```
✅ Bot authenticated: B06XXX on Telnyx
✅ Posted to Slack (ts: 1234567890.123456)
🎉 Bot integration working perfectly!
```

---

## **NEXT STEPS**

After token is working:
1. ✅ Test bot posting
2. ✅ Integrate into production script
3. ✅ Update cron job
4. ✅ Test end-to-end flow