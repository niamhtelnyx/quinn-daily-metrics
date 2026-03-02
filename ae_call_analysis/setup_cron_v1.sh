#!/bin/bash

echo "🚀 Setting up Fellow Call Intelligence Cron Job - V1"
echo "=================================================="

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_SCRIPT="$SCRIPT_DIR/fellow_cron_job.py"

echo "📁 Script directory: $SCRIPT_DIR"
echo "🐍 Cron script: $CRON_SCRIPT"

# Check if script exists
if [ ! -f "$CRON_SCRIPT" ]; then
    echo "❌ Error: fellow_cron_job.py not found"
    exit 1
fi

# Make script executable
chmod +x "$CRON_SCRIPT"
echo "✅ Made script executable"

# Check Python dependencies
echo ""
echo "🔍 Checking dependencies..."
python3 -c "
try:
    import requests
    import sqlite3
    print('✅ requests, sqlite3 available')
except ImportError as e:
    print(f'❌ Missing dependency: {e}')
    print('Run: pip install requests')
    exit(1)

# Check if enhanced processor exists
try:
    from enhanced_call_processor import EnhancedCallProcessor
    print('✅ enhanced_call_processor available')
except ImportError:
    print('❌ Missing enhanced_call_processor.py')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Dependency check failed"
    exit 1
fi

# Set environment variables
echo ""
echo "🔧 Environment setup..."

# Default Fellow API key (may need updating)
FELLOW_KEY="${FELLOW_API_KEY:-}"  # Set FELLOW_API_KEY environment variable

# Create environment file
cat > "$SCRIPT_DIR/.env" << EOF
# Fellow API Configuration
FELLOW_API_KEY=$FELLOW_KEY

# Database Configuration  
DATABASE_PATH=$SCRIPT_DIR/ae_call_analysis.db

# Cron Configuration
CRON_LOG_PATH=$SCRIPT_DIR/logs/cron.log

# Python path
PYTHONPATH=$SCRIPT_DIR
EOF

echo "✅ Environment file created: $SCRIPT_DIR/.env"

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs"
echo "✅ Logs directory created"

# Test run the cron job
echo ""
echo "🧪 Testing cron job (dry run)..."

cd "$SCRIPT_DIR"
export FELLOW_API_KEY="$FELLOW_KEY"
export PYTHONPATH="$SCRIPT_DIR"

# Run a quick test
python3 "$CRON_SCRIPT" 2>&1 | head -20

echo ""
echo "📋 Cron job setup options:"
echo ""

echo "1️⃣ SYSTEM CRONTAB (Recommended):"
echo "   # Edit crontab"
echo "   crontab -e"
echo ""
echo "   # Add this line for 30-minute runs:"
echo "   */30 * * * * cd $SCRIPT_DIR && source .env && python3 fellow_cron_job.py >> logs/cron.log 2>&1"
echo ""

echo "2️⃣ MANUAL TEST RUN:"
echo "   cd $SCRIPT_DIR"
echo "   source .env"  
echo "   python3 fellow_cron_job.py"
echo ""

echo "3️⃣ CONTINUOUS MODE (Testing):"
echo "   cd $SCRIPT_DIR"
echo "   export CRON_MODE=continuous"
echo "   python3 fellow_cron_job.py"
echo ""

echo "📊 MONITORING:"
echo "   # View cron logs"
echo "   tail -f $SCRIPT_DIR/logs/cron.log"
echo ""
echo "   # Check database"
echo "   sqlite3 $SCRIPT_DIR/ae_call_analysis.db 'SELECT * FROM cron_runs ORDER BY run_timestamp DESC LIMIT 5'"
echo ""

echo "🎯 NEXT STEPS:"
echo "1. Verify Fellow API key is working"
echo "2. Choose cron setup method (option 1 recommended)"
echo "3. Run initial test"
echo "4. Monitor logs for first few runs"
echo "5. Validate Slack alerts are being sent"

echo ""
echo "✅ V1 Cron Job setup complete!"
echo "📋 The system will now:"
echo "   • Poll Fellow API every 30 minutes"
echo "   • Process new calls through enhanced pipeline"
echo "   • Send Slack alerts to stakeholders"
echo "   • Track all runs in database"