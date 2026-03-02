#!/usr/bin/env python3
"""
Slack Notification Service for AE Call Analysis
Delivers call insights to #bot-testing channel for stakeholders
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from config.settings import get_config

@dataclass
class CallInsight:
    """Structured call analysis data for Slack delivery"""
    call_id: str
    title: str
    ae_name: str
    prospect_name: str
    created_at: str
    simple_summary: Dict[str, Any]
    detailed_analysis: Dict[str, Any]
    confidence_score: int
    
    @property
    def prospect_interest(self) -> str:
        """Extract prospect interest level"""
        sentiment = self.simple_summary.get('prospect_sentiment', {})
        return sentiment.get('interest_level', 'unknown')
    
    @property
    def ae_excitement(self) -> str:
        """Extract AE excitement level"""
        sentiment = self.simple_summary.get('ae_sentiment', {})
        return sentiment.get('excitement_level', 'unknown')
    
    @property
    def products_discussed(self) -> List[str]:
        """Extract Telnyx products discussed"""
        return self.simple_summary.get('telnyx_products', [])
    
    @property
    def next_step_category(self) -> str:
        """Extract next step classification"""
        next_steps = self.simple_summary.get('next_steps', {})
        return next_steps.get('category', 'unknown')


class SlackNotifier:
    """Slack notification service for AE call analysis insights"""
    
    def __init__(self, channel_id: str = "C38URQASH"):
        self.config = get_config()
        self.channel_id = channel_id  # #bot-testing
        self.db_path = self.config.database.path
    
    def get_recent_calls(self, hours: int = 24) -> List[CallInsight]:
        """Get recent call analyses for notifications"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cutoff = datetime.now() - timedelta(hours=hours)
        
        query = """
        SELECT 
            c.id as call_id,
            c.title,
            c.created_at,
            ar.simple_summary,
            ar.detailed_analysis,
            ar.analysis_confidence
        FROM calls c
        JOIN analysis_results ar ON c.id = ar.call_id
        WHERE ar.created_at >= ?
        AND ar.simple_summary IS NOT NULL
        ORDER BY ar.created_at DESC
        """
        
        cursor.execute(query, (cutoff.isoformat(),))
        results = cursor.fetchall()
        conn.close()
        
        insights = []
        for row in results:
            # Extract names from title: "Telnyx Intro Call (Prospect Name)"
            title = row['title']
            prospect_name = self._extract_prospect_name(title)
            ae_name = "Unknown AE"  # Could enhance with AE tracking later
            
            try:
                simple_summary = json.loads(row['simple_summary'])
                detailed_analysis = json.loads(row['detailed_analysis'] or '{}')
                
                insight = CallInsight(
                    call_id=row['call_id'],
                    title=title,
                    ae_name=ae_name,
                    prospect_name=prospect_name,
                    created_at=row['created_at'],
                    simple_summary=simple_summary,
                    detailed_analysis=detailed_analysis,
                    confidence_score=row['analysis_confidence']
                )
                insights.append(insight)
            except json.JSONDecodeError:
                continue
        
        return insights
    
    def _extract_prospect_name(self, title: str) -> str:
        """Extract prospect name from title format: 'Telnyx Intro Call (Name)'"""
        if "(" in title and ")" in title:
            start = title.find("(") + 1
            end = title.find(")")
            return title[start:end].strip()
        return "Unknown"
    
    def format_daily_digest(self, insights: List[CallInsight]) -> Dict[str, Any]:
        """Format daily digest for Slack delivery"""
        if not insights:
            return {
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "📞 *AE Call Analysis - Daily Digest*\\n\\n_No new qualification calls analyzed in the last 24 hours._"
                        }
                    }
                ]
            }
        
        # Calculate metrics
        total_calls = len(insights)
        high_interest = len([i for i in insights if i.prospect_interest in ['8', '9', '10']])
        excited_aes = len([i for i in insights if i.ae_excitement in ['8', '9', '10']])
        moving_forward = len([i for i in insights if i.next_step_category == 'moving_forward'])
        
        # Most discussed products
        all_products = []
        for insight in insights:
            all_products.extend(insight.products_discussed)
        
        product_counts = {}
        for product in all_products:
            product_counts[product] = product_counts.get(product, 0) + 1
        
        top_products = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Build message blocks
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📞 *AE Call Analysis - Daily Digest*\\n_{datetime.now().strftime('%B %d, %Y')}_"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Calls:*\\n{total_calls}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*High Interest:*\\n{high_interest} ({high_interest/total_calls*100:.1f}%)"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Excited AEs:*\\n{excited_aes} ({excited_aes/total_calls*100:.1f}%)"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Moving Forward:*\\n{moving_forward} ({moving_forward/total_calls*100:.1f}%)"
                    }
                ]
            }
        ]
        
        # Add top products if any
        if top_products:
            product_text = "\\n".join([f"• {product} ({count})" for product, count in top_products])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🔥 Top Products Discussed:*\\n{product_text}"
                }
            })
        
        # Add individual call summaries for high-value calls
        high_value_calls = [
            i for i in insights 
            if (i.prospect_interest in ['8', '9', '10'] or 
                i.next_step_category == 'moving_forward')
        ]
        
        if high_value_calls:
            blocks.append({
                "type": "divider"
            })
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🎯 High-Value Calls:*"
                }
            })
            
            for call in high_value_calls[:5]:  # Show top 5
                pain_points = call.simple_summary.get('core_talking_points', [])[:2]
                pain_text = ", ".join(pain_points) if pain_points else "General discussion"
                
                call_text = (
                    f"*{call.prospect_name}* | "
                    f"Interest: {call.prospect_interest}/10 | "
                    f"AE: {call.ae_excitement}/10\\n"
                    f"_{pain_text}_"
                )
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": call_text
                    }
                })
        
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "_Automated AE Call Analysis • Daily digest at 9am CST_"
                }
            ]
        })
        
        return {"blocks": blocks}
    
    def format_high_value_alert(self, insight: CallInsight) -> Dict[str, Any]:
        """Format real-time alert for high-value calls"""
        pain_points = insight.simple_summary.get('core_talking_points', [])
        products = insight.products_discussed
        
        pain_text = "\\n".join([f"• {point}" for point in pain_points[:3]])
        product_text = ", ".join(products) if products else "General"
        
        alert_text = (
            f"🚨 *High-Value Call Alert*\\n\\n"
            f"*Prospect:* {insight.prospect_name}\\n"
            f"*Interest Level:* {insight.prospect_interest}/10\\n"
            f"*AE Excitement:* {insight.ae_excitement}/10\\n"
            f"*Products:* {product_text}\\n\\n"
            f"*Key Pain Points:*\\n{pain_text}\\n\\n"
            f"*Next Step:* {insight.next_step_category.replace('_', ' ').title()}"
        )
        
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": alert_text
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"_Call ID: {insight.call_id} • Confidence: {insight.confidence_score}/10_"
                        }
                    ]
                }
            ]
        }
    
    def should_send_alert(self, insight: CallInsight) -> bool:
        """Determine if call qualifies for real-time high-value alert"""
        # High interest prospect (8+ interest)
        high_interest = insight.prospect_interest in ['8', '9', '10']
        
        # Excited AE (8+ excitement)
        excited_ae = insight.ae_excitement in ['8', '9', '10']
        
        # Moving forward
        moving_forward = insight.next_step_category == 'moving_forward'
        
        # High confidence analysis (handle None values)
        confidence = insight.confidence_score or 0
        high_confidence = confidence >= 8
        
        # Must have high confidence + (high interest OR moving forward)
        return high_confidence and (high_interest or excited_ae or moving_forward)


def send_to_slack(message_data: Dict[str, Any], channel_id: str = "C38URQASH") -> bool:
    """Send message to Slack using Clawdbot's message tool"""
    import subprocess
    import tempfile
    import json
    
    # Use Clawdbot's message tool to send to Slack
    try:
        # Note: This would integrate with Clawdbot's message system
        # For now, return True to indicate successful formatting
        print(f"📤 Would send to Slack #{channel_id}:")
        print(json.dumps(message_data, indent=2))
        return True
    except Exception as e:
        print(f"❌ Slack send error: {e}")
        return False


if __name__ == "__main__":
    # Test the notification system
    notifier = SlackNotifier()
    recent_calls = notifier.get_recent_calls(hours=24)
    
    print(f"📊 Found {len(recent_calls)} recent calls")
    
    if recent_calls:
        # Test daily digest
        digest = notifier.format_daily_digest(recent_calls)
        print("\\n📋 Daily Digest:")
        print(json.dumps(digest, indent=2))
        
        # Test high-value alert
        for call in recent_calls:
            if notifier.should_send_alert(call):
                alert = notifier.format_high_value_alert(call)
                print(f"\\n🚨 High-Value Alert for {call.prospect_name}:")
                print(json.dumps(alert, indent=2))
                break