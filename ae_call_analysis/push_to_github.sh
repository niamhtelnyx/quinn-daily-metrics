#!/bin/bash
# Push Call Intelligence System to GitHub
echo "🚀 Pushing Call Intelligence System to meeting-sync repository..."
echo ""
echo "When prompted:"
echo "  Username: niamhtelnyx"  
echo "  Password: [paste your GitHub Personal Access Token]"
echo ""

cd "$(dirname "$0")"
git push meeting-sync HEAD:main

echo ""
echo "✅ Call Intelligence System pushed to: https://github.com/team-telnyx/meeting-sync"