#!/bin/bash
source /Users/niamhcollins/clawd/.env.gog

FOLDER_ID="1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY"

echo "Checking your specific folder: $FOLDER_ID and all subfolders..."

# Get all files recursively by getting all subfolders first, then checking each
echo "Getting all subfolders..."
subfolders=$(gog drive ls --parent "$FOLDER_ID" --json --max 1000 | jq -r '.files[] | select(.mimeType=="application/vnd.google-apps.folder") | .id')

echo "Found $(echo "$subfolders" | wc -l) subfolders"

# Check main folder files first
echo "Checking main folder files..."
main_files=$(gog drive ls --parent "$FOLDER_ID" --json --max 1000 | jq -r '.files[] | select(.mimeType!="application/vnd.google-apps.folder") | .modifiedTime + "," + .name + ",MAIN_FOLDER"')

# Check each subfolder
all_files="$main_files"
echo "Checking subfolders..."

for folder_id in $subfolders; do
    echo "Checking subfolder: $folder_id"
    folder_files=$(gog drive ls --parent "$folder_id" --json --max 1000 2>/dev/null | jq -r '.files[] | .modifiedTime + "," + .name + "," + (.parents[0] // "unknown")' 2>/dev/null || true)
    if [ ! -z "$folder_files" ]; then
        all_files="$all_files
$folder_files"
    fi
    sleep 0.1
done

# Sort all files and get the top 10
echo ""
echo "Most recent files in your folder and subfolders:"
echo "==============================================="
echo "$all_files" | grep -v '^$' | sort -r | head -10 | while IFS=',' read -r modified_time file_name folder_info; do
    echo "Time: $modified_time"
    echo "File: $file_name"
    echo "Location: $folder_info"
    echo "---"
done

echo ""
echo "THE MOST RECENT FILE:"
echo "===================="
most_recent=$(echo "$all_files" | grep -v '^$' | sort -r | head -1)
echo "$most_recent" | while IFS=',' read -r modified_time file_name folder_info; do
    echo "📄 File: $file_name"
    echo "🕐 Modified: $modified_time"
    echo "📁 Location: $folder_info"
done