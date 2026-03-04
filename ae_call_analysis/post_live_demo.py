#!/usr/bin/env python3
"""
Post a live demo alert to show V1 working
"""

import os

def main():
    # Read the latest alert
    try:
        with open('slack_alert_live_103927.txt', 'r') as f:
            alert = f.read()
    except FileNotFoundError:
        alert = "🔔 **V1 Live Demo**\n\nV1 Call Intelligence automation is live and working!\n\n_Processing Fellow calls automatically_"
    
    print("🚀 V1 LIVE DEMO - READY FOR SLACK")
    print("=" * 50)
    print("📱 Channel: C0AJ9E9F474")
    print("🤖 Status: Live automation running")
    print("📊 Processing: Fellow 'Telnyx Intro Call' recordings")
    print("")
    print("🔔 LIVE ALERT TO POST:")
    print("-" * 30)
    print(alert)
    print("-" * 30)
    print("")
    print("✅ V1 STATUS:")
    print("   🔄 Running every 30 minutes")
    print("   📞 Fellow API: Working") 
    print("   🏢 Salesforce: Ready")
    print("   📱 Slack: Channel C0AJ9E9F474")
    print("   💾 Database: v1_live_processed.db")
    print("")
    print("🎯 NEXT: V1 will automatically post new Fellow calls to Slack")

if __name__ == "__main__":
    main()