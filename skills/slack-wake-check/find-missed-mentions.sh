#!/bin/bash
# Find recent Slack mentions of Ninibot that may have been missed
# Usage: SLACK_BOT_TOKEN=xoxb-... ./find-missed-mentions.sh [minutes_back]

set -euo pipefail

MINUTES_BACK="${1:-10}"
BOT_USER_ID="U0AB8C04G2H"
NIAMH_USER_ID="U017BLB9C4V"
TOKEN="${SLACK_BOT_TOKEN:?Set SLACK_BOT_TOKEN}"

# Calculate oldest timestamp
if [[ "$(uname)" == "Darwin" ]]; then
  OLDEST=$(date -v-${MINUTES_BACK}M +%s)
else
  OLDEST=$(date -d "${MINUTES_BACK} minutes ago" +%s)
fi

echo "Checking for mentions of <@${BOT_USER_ID}> in the last ${MINUTES_BACK} minutes (since $(date -r $OLDEST 2>/dev/null || date -d @$OLDEST))..."
echo "---"

# Get channels bot is in
CHANNELS=$(curl -s "https://slack.com/api/conversations.list" \
  -H "Authorization: Bearer $TOKEN" \
  -G --data-urlencode "types=public_channel,private_channel,mpim" \
  --data-urlencode "limit=200" \
  --data-urlencode "exclude_archived=true" | \
  jq -r '.channels[]? | select(.is_member == true) | "\(.id)|\(.name // .id)"')

FOUND=0

while IFS='|' read -r CHAN_ID CHAN_NAME; do
  [[ -z "$CHAN_ID" ]] && continue

  # Check recent messages in channel
  MESSAGES=$(curl -s "https://slack.com/api/conversations.history" \
    -H "Authorization: Bearer $TOKEN" \
    -G --data-urlencode "channel=$CHAN_ID" \
    --data-urlencode "oldest=$OLDEST" \
    --data-urlencode "limit=50")

  # Find messages mentioning the bot
  MENTIONS=$(echo "$MESSAGES" | jq -r --arg bot "$BOT_USER_ID" \
    '.messages[]? | select(.text | contains("<@" + $bot + ">")) | "\(.ts)|\(.user // "unknown")|\(.text[:200])|\(.thread_ts // "")"')

  while IFS='|' read -r MSG_TS MSG_USER MSG_TEXT THREAD_TS; do
    [[ -z "$MSG_TS" ]] && continue
    FOUND=$((FOUND + 1))

    echo "MENTION FOUND:"
    echo "  Channel: #${CHAN_NAME} (${CHAN_ID})"
    echo "  Message TS: ${MSG_TS}"
    echo "  Thread TS: ${THREAD_TS:-none}"
    echo "  From: ${MSG_USER}"
    echo "  Text: ${MSG_TEXT}"
    echo "---"

    # If it's a thread, also check thread replies for mentions
    if [[ -n "$THREAD_TS" && "$THREAD_TS" != "$MSG_TS" ]]; then
      REPLIES=$(curl -s "https://slack.com/api/conversations.replies" \
        -H "Authorization: Bearer $TOKEN" \
        -G --data-urlencode "channel=$CHAN_ID" \
        --data-urlencode "ts=$THREAD_TS" \
        --data-urlencode "oldest=$OLDEST" \
        --data-urlencode "limit=20")

      REPLY_MENTIONS=$(echo "$REPLIES" | jq -r --arg bot "$BOT_USER_ID" \
        '.messages[]? | select(.text | contains("<@" + $bot + ">")) | select(.ts != "'"$MSG_TS"'") | "\(.ts)|\(.user // "unknown")|\(.text[:200])"')

      while IFS='|' read -r R_TS R_USER R_TEXT; do
        [[ -z "$R_TS" ]] && continue
        FOUND=$((FOUND + 1))
        echo "  THREAD REPLY MENTION:"
        echo "    Reply TS: ${R_TS}"
        echo "    From: ${R_USER}"
        echo "    Text: ${R_TEXT}"
        echo "  ---"
      done <<< "$REPLY_MENTIONS"
    fi
  done <<< "$MENTIONS"

  # Also check for threads with recent replies mentioning bot (parent messages outside window)
  THREAD_MESSAGES=$(echo "$MESSAGES" | jq -r '.messages[]? | select(.reply_count != null and .reply_count > 0) | .ts')
  while read -r PARENT_TS; do
    [[ -z "$PARENT_TS" ]] && continue
    REPLIES=$(curl -s "https://slack.com/api/conversations.replies" \
      -H "Authorization: Bearer $TOKEN" \
      -G --data-urlencode "channel=$CHAN_ID" \
      --data-urlencode "ts=$PARENT_TS" \
      --data-urlencode "oldest=$OLDEST" \
      --data-urlencode "limit=20")

    REPLY_MENTIONS=$(echo "$REPLIES" | jq -r --arg bot "$BOT_USER_ID" \
      '.messages[]? | select(.text | contains("<@" + $bot + ">")) | "\(.ts)|\(.user // "unknown")|\(.text[:200])"')

    while IFS='|' read -r R_TS R_USER R_TEXT; do
      [[ -z "$R_TS" ]] && continue
      FOUND=$((FOUND + 1))
      echo "THREAD MENTION FOUND:"
      echo "  Channel: #${CHAN_NAME} (${CHAN_ID})"
      echo "  Thread: ${PARENT_TS}"
      echo "  Reply TS: ${R_TS}"
      echo "  From: ${R_USER}"
      echo "  Text: ${R_TEXT}"
      echo "---"
    done <<< "$REPLY_MENTIONS"
  done <<< "$THREAD_MESSAGES"

done <<< "$CHANNELS"

echo ""
echo "Total mentions found: ${FOUND}"
