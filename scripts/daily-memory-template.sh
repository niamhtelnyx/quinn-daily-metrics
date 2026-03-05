#!/bin/bash

# Daily Memory Template Script
# Creates today's memory file template if it doesn't already exist

# Get today's date in YYYY-MM-DD format
TODAY=$(date +%Y-%m-%d)
MEMORY_DIR="/Users/niamhcollins/clawd/memory"
MEMORY_FILE="$MEMORY_DIR/$TODAY.md"

# Create memory directory if it doesn't exist
mkdir -p "$MEMORY_DIR"

# Check if today's memory file already exists
if [[ -f "$MEMORY_FILE" ]]; then
    echo "Memory file for $TODAY already exists: $MEMORY_FILE"
    exit 0
fi

# Create today's memory file with template
cat > "$MEMORY_FILE" << EOF
# $TODAY

## Morning

## Afternoon

## Evening

## Notes & Context

## Tasks & Decisions

EOF

echo "Created memory file template: $MEMORY_FILE"