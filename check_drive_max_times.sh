#!/bin/bash
source /Users/niamhcollins/clawd/.env.gog

echo "Checking max file modification times per folder..."
echo "Folder,Max Modified Time,File Name"
echo "================================================"

# First get all folders in the main directory
folders=$(gog drive ls --parent 1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY --json | jq -r '.files[] | select(.mimeType=="application/vnd.google-apps.folder") | .id + "," + .name')

# Also check files in root folder
echo "Checking root folder files..."
root_files=$(gog drive ls --parent 1i0Vh_dTjkULE4VwVDSYlFrgnLTxXJoUY --json | jq -r '.files[] | select(.mimeType!="application/vnd.google-apps.folder") | .modifiedTime + "," + .name')
if [ ! -z "$root_files" ]; then
    max_root=$(echo "$root_files" | sort -r | head -1)
    echo "ROOT,$max_root"
fi

# Process each subfolder
while IFS=',' read -r folder_id folder_name; do
    echo "Checking folder: $folder_name"
    
    # Get all files in this folder and find the max modified time
    files_output=$(gog drive ls --parent "$folder_id" --json --max 1000 2>/dev/null)
    
    if [ $? -eq 0 ] && [ ! -z "$files_output" ]; then
        max_file=$(echo "$files_output" | jq -r '.files[] | .modifiedTime + "," + .name' 2>/dev/null | sort -r | head -1)
        if [ ! -z "$max_file" ] && [ "$max_file" != "," ]; then
            echo "$folder_name,$max_file"
        fi
    fi
    
    # Small delay to avoid rate limiting
    sleep 0.1
done <<< "$folders"