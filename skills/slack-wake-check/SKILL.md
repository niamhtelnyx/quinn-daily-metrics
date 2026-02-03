# Slack Wake Check

## When to Use
When Niamh pings you in a DM asking if you're alive/online/here — phrases like:
- "are you online?"
- "are you alive?"
- "still here?"
- "hello? @ninibot"
- "you there?"
- any short DM that's basically checking if you're responsive

## What to Do

**Act like a worker caught sleeping on the job.** Don't just say "yep I'm here!" — go check what you missed.

### Step 1: Acknowledge briefly
Reply something like "I'm here! Let me check if I dropped anything..." (casual, slightly sheepish)

### Step 2: Find missed mentions (last 10 minutes)
Use the Slack API to check for recent mentions of `<@U0AB8C04G2H>` (Ninibot's user ID) across channels.

**Bot tokens can't use `search.messages`**, so use this approach:

```bash
# Get channels the bot is in
curl -s "https://slack.com/api/conversations.list" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -G --data-urlencode "types=public_channel,private_channel,mpim,im" \
  --data-urlencode "limit=200" \
  --data-urlencode "exclude_archived=true"
```

Then for each active channel (focus on ones from recent sessions), check recent messages:
```bash
# Check last 10 min of messages in a channel (oldest = unix timestamp 10 min ago)
OLDEST=$(date -v-10M +%s 2>/dev/null || date -d '10 minutes ago' +%s)
curl -s "https://slack.com/api/conversations.history" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -G --data-urlencode "channel=CHANNEL_ID" \
  --data-urlencode "oldest=$OLDEST" \
  --data-urlencode "limit=20"
```

For threads, also check replies:
```bash
curl -s "https://slack.com/api/conversations.replies" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -G --data-urlencode "channel=CHANNEL_ID" \
  --data-urlencode "ts=THREAD_TS" \
  --data-urlencode "oldest=$OLDEST" \
  --data-urlencode "limit=20"
```

**Shortcut:** Check `sessions_list` for recently active sessions first. Those are the threads most likely to have dropped messages. Then verify against Slack API for each session's channel.

### Step 3: For each missed mention, resume the session

Use `sessions_send` to send a message into the dropped session:
```
sessions_send(sessionKey="<the session key>", message="[WAKE CHECK] Niamh pinged me — I think I dropped this thread. Picking back up. Last message from Niamh in this thread: <quote the message>")
```

This wakes the session and continues the conversation there — **not** in the DM.

### Step 4: Report back in DM
Tell Niamh what you found:
- "Found 2 threads I dropped! Picking them back up now: [thread descriptions]"
- Or "Checked the last 10 min — looks like I didn't miss anything! What do you need?"

## Important Rules

- **Don't blend sessions.** Each dropped thread gets resumed in its own session via `sessions_send`.
- **Don't repeat the conversation** in the DM. Just tell Niamh you're picking it up, then go do it in the right thread.
- **Check both channels and threads.** Mentions could be in channel-level messages or thread replies.
- **Widening window.** Start with 10 minutes. If nothing found, widen to 30 min, then 60 min. Niamh might not ping immediately — she sometimes waits a while before checking on you.

## Environment
- Bot token: `$SLACK_BOT_TOKEN` (set in env, or see TOOLS.md)
- Ninibot user ID: `U0AB8C04G2H`
- Niamh user ID: `U017BLB9C4V`
