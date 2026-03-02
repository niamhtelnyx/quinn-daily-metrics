#!/usr/bin/env python3
"""
Slack Integration for AE Call Analysis
Connects the SlackNotifier to Clawdbot's message system
"""

import json
from typing import Dict, Any
from services.slack_notifier import SlackNotifier

class SlackIntegration:
    """Integration between AE Call Analysis and Clawdbot Slack messaging"""
    
    def __init__(self, channel_id: str = "C38URQASH"):  # #bot-testing
        # Override database path to use the working database
        class ProductionSlackNotifier(SlackNotifier):
            def __init__(self, channel_id):
                super().__init__(channel_id)
                self.db_path = './ae_call_analysis.db'  # Use the real database
        
        self.notifier = ProductionSlackNotifier(channel_id)
        self.channel_id = channel_id
    
    def send_daily_digest(self, hours: int = 24) -> bool:
        """Send daily digest to Slack channel"""
        try:
            # Get recent calls
            recent_calls = self.notifier.get_recent_calls(hours=hours)
            
            # Format digest
            message_data = self.notifier.format_daily_digest(recent_calls)
            
            # Convert to text format for Clawdbot message tool
            slack_text = self._blocks_to_text(message_data['blocks'])
            
            print(f"📊 Daily Digest for {len(recent_calls)} calls:")
            print(slack_text)
            print(f"\n🎯 Ready to send to #bot-testing (Channel ID: {self.channel_id})")
            
            return True
            
        except Exception as e:
            print(f"❌ Error sending daily digest: {e}")
            return False
    
    def send_high_value_alerts(self, hours: int = 24) -> int:
        """Send alerts for high-value calls"""
        try:
            # Get recent calls
            recent_calls = self.notifier.get_recent_calls(hours=hours)
            
            # Find high-value calls
            alerts_sent = 0
            for call in recent_calls:
                if self.notifier.should_send_alert(call):
                    # Format alert
                    message_data = self.notifier.format_high_value_alert(call)
                    slack_text = self._blocks_to_text(message_data['blocks'])
                    
                    print(f"🚨 High-Value Alert for {call.prospect_name}:")
                    print(slack_text)
                    print(f"🎯 Ready to send to #bot-testing")
                    print("---")
                    
                    alerts_sent += 1
            
            return alerts_sent
            
        except Exception as e:
            print(f"❌ Error sending high-value alerts: {e}")
            return 0
    
    def _blocks_to_text(self, blocks: list) -> str:
        """Convert Slack blocks to text format for Clawdbot"""
        text_parts = []
        
        for block in blocks:
            if block.get('type') == 'section':
                if 'text' in block:
                    text_parts.append(block['text']['text'])
                if 'fields' in block:
                    for field in block['fields']:
                        text_parts.append(field['text'])
            elif block.get('type') == 'context':
                for element in block.get('elements', []):
                    if 'text' in element:
                        text_parts.append(element['text'])
            elif block.get('type') == 'divider':
                text_parts.append("---")
        
        return '\n\n'.join(text_parts)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the notification system"""
        try:
            recent_calls = self.notifier.get_recent_calls(hours=24)
            high_value_calls = [
                call for call in recent_calls 
                if self.notifier.should_send_alert(call)
            ]
            
            return {
                "status": "operational",
                "total_calls_24h": len(recent_calls),
                "high_value_calls_24h": len(high_value_calls),
                "channel_id": self.channel_id,
                "database_path": self.notifier.db_path
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "channel_id": self.channel_id
            }


def demo_slack_integration():
    """Demo the Slack integration functionality"""
    print("🚀 AE CALL ANALYSIS - SLACK INTEGRATION DEMO")
    print("=" * 50)
    
    integration = SlackIntegration()
    
    # Show status
    status = integration.get_status()
    print(f"📊 STATUS:")
    print(f"   System: {status['status']}")
    print(f"   Calls (24h): {status.get('total_calls_24h', 0)}")
    print(f"   High-value: {status.get('high_value_calls_24h', 0)}")
    print(f"   Channel: #{status['channel_id']}")
    print()
    
    # Demo daily digest
    print("📋 DAILY DIGEST:")
    print("-" * 30)
    integration.send_daily_digest(hours=48)  # 48h to get more data
    print()
    
    # Demo high-value alerts
    print("🚨 HIGH-VALUE ALERTS:")
    print("-" * 30)
    alerts_count = integration.send_high_value_alerts(hours=48)
    print(f"\n✅ {alerts_count} high-value alerts ready")
    print()
    
    print("🎯 PHASE 3 SLACK INTEGRATION: COMPLETE!")


if __name__ == "__main__":
    demo_slack_integration()