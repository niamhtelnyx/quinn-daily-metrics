#!/bin/bash

echo "🔑 Fellow API Setup for Webhook Integration"
echo "=========================================="

echo ""
echo "You need to set your Fellow API key as an environment variable:"
echo ""
echo "export FELLOW_API_KEY=\"your_fellow_api_key_here\""
echo ""
echo "Or add it to your .bashrc/.zshrc for persistence:"
echo "echo 'export FELLOW_API_KEY=\"your_fellow_api_key_here\"' >> ~/.bashrc"
echo ""

# Check if API key is already set
if [ -z "$FELLOW_API_KEY" ]; then
    echo "❌ FELLOW_API_KEY not set"
    echo ""
    echo "To get your Fellow API key:"
    echo "1. Go to Fellow app → Settings → Integrations"
    echo "2. Look for API key or Personal Access Token"  
    echo "3. Copy the key and set the environment variable above"
else
    echo "✅ FELLOW_API_KEY is set: ${FELLOW_API_KEY:0:10}..."
    echo ""
    echo "Testing API connection..."
    
    # Test API connection
    curl -H "Authorization: Bearer $FELLOW_API_KEY" \
         -H "Content-Type: application/json" \
         "https://api.fellow.app/v1/notes" \
         --silent --show-error -w "\nHTTP Status: %{http_code}\n" | head -20
fi

echo ""
echo "✅ Once API key is set, you can test with:"
echo "   python3 ae_call_analysis/test_webhook.py"