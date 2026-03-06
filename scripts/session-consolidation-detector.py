#!/usr/bin/env python3
"""
Session Consolidation Detector
Identifies fragmented sessions and suggests consolidation opportunities
"""

import sys
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class SessionConsolidationDetector:
    
    def __init__(self):
        self.session_patterns = {
            'technical_work': [
                'api', 'integration', 'database', 'oauth', 'authentication', 
                'deployment', 'docker', 'github', 'automation', 'script'
            ],
            'service_orders': [
                'service order', 'salesforce', 'commitment', 'quinn', 'so',
                'revenue', 'billing', 'opportunity'
            ],
            'call_intelligence': [
                'fellow', 'call analysis', 'google drive', 'meeting', 'livekit',
                'voice', 'recording', 'transcript'
            ],
            'documentation': [
                'skill', 'memory', 'documentation', 'readme', 'guide',
                'template', 'framework'
            ],
            'efficiency': [
                'automation', 'optimization', 'efficiency', 'workflow',
                'process', 'improvement', 'review'
            ]
        }
        
        self.fragmentation_indicators = [
            'multiple sessions for same project',
            'repeated context setting',
            'cross-referencing between sessions',
            'similar technical discussions',
            'related debugging across sessions'
        ]
    
    def analyze_session_data(self, sessions_data: list) -> dict:
        """Analyze session data to identify fragmentation patterns"""
        
        # Group sessions by content similarity
        categorized_sessions = defaultdict(list)
        time_clusters = defaultdict(list)
        
        for session in sessions_data:
            # Categorize by content
            category = self._categorize_session(session)
            categorized_sessions[category].append(session)
            
            # Group by time proximity
            session_time = self._parse_session_time(session)
            if session_time:
                time_key = session_time.strftime('%Y-%m-%d-%H')  # Hour-based clustering
                time_clusters[time_key].append(session)
        
        # Identify fragmentation
        fragmentation_issues = self._identify_fragmentation(categorized_sessions, time_clusters)
        
        # Calculate consolidation opportunities
        consolidation_opportunities = self._calculate_consolidation_opportunities(
            categorized_sessions, time_clusters
        )
        
        return {
            'analysis_timestamp': datetime.now().isoformat(),
            'total_sessions': len(sessions_data),
            'categorized_sessions': dict(categorized_sessions),
            'time_clusters': dict(time_clusters),
            'fragmentation_issues': fragmentation_issues,
            'consolidation_opportunities': consolidation_opportunities,
            'fragmentation_score': self._calculate_fragmentation_score(fragmentation_issues)
        }
    
    def _categorize_session(self, session: dict) -> str:
        """Categorize a session based on its content"""
        content = (session.get('description', '') + ' ' + 
                  session.get('last_message', '') + ' ' +
                  session.get('title', '')).lower()
        
        # Score against each category
        category_scores = {}
        for category, keywords in self.session_patterns.items():
            score = sum(1 for keyword in keywords if keyword in content)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores, key=category_scores.get)
        else:
            return 'uncategorized'
    
    def _parse_session_time(self, session: dict) -> datetime:
        """Parse session timestamp"""
        time_str = session.get('last_active', session.get('created_at'))
        if not time_str:
            return None
            
        try:
            # Handle various timestamp formats
            if 'T' in time_str:
                return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            else:
                return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        except:
            return None
    
    def _identify_fragmentation(self, categorized: dict, time_clusters: dict) -> list:
        """Identify specific fragmentation issues"""
        issues = []
        
        # Check for category-based fragmentation
        for category, sessions in categorized.items():
            if len(sessions) > 3:  # More than 3 sessions in same category
                issues.append({
                    'type': 'category_fragmentation',
                    'category': category,
                    'session_count': len(sessions),
                    'severity': 'HIGH' if len(sessions) > 5 else 'MEDIUM',
                    'description': f'{len(sessions)} sessions in {category} category',
                    'sessions': [s.get('id', 'unknown') for s in sessions[:5]]  # Show first 5
                })
        
        # Check for time-based fragmentation
        for time_key, sessions in time_clusters.items():
            if len(sessions) > 4:  # More than 4 sessions in same hour
                issues.append({
                    'type': 'time_fragmentation',
                    'time_period': time_key,
                    'session_count': len(sessions),
                    'severity': 'MEDIUM',
                    'description': f'{len(sessions)} sessions active in {time_key}',
                    'sessions': [s.get('id', 'unknown') for s in sessions[:5]]
                })
        
        # Check for potential duplicate topics
        session_titles = defaultdict(list)
        for category, sessions in categorized.items():
            for session in sessions:
                title_words = set(session.get('title', '').lower().split())
                if len(title_words) > 2:  # Only consider meaningful titles
                    key = tuple(sorted(title_words))
                    session_titles[key].append(session)
        
        for title_key, sessions in session_titles.items():
            if len(sessions) > 1:
                issues.append({
                    'type': 'duplicate_topics',
                    'topic': ' '.join(title_key[:5]),  # Show first 5 words
                    'session_count': len(sessions),
                    'severity': 'LOW',
                    'description': f'{len(sessions)} sessions with similar topics',
                    'sessions': [s.get('id', 'unknown') for s in sessions]
                })
        
        return issues
    
    def _calculate_consolidation_opportunities(self, categorized: dict, time_clusters: dict) -> list:
        """Calculate specific consolidation opportunities"""
        opportunities = []
        
        # Category-based consolidation
        for category, sessions in categorized.items():
            if len(sessions) > 2:
                # Check if sessions could be merged based on recency
                recent_sessions = [
                    s for s in sessions 
                    if self._parse_session_time(s) and 
                    self._parse_session_time(s) > datetime.now() - timedelta(days=2)
                ]
                
                if len(recent_sessions) > 1:
                    opportunities.append({
                        'type': 'category_merge',
                        'category': category,
                        'sessions_to_merge': len(recent_sessions),
                        'potential_savings': len(recent_sessions) - 1,
                        'priority': 'HIGH' if len(recent_sessions) > 3 else 'MEDIUM',
                        'description': f'Merge {len(recent_sessions)} recent {category} sessions',
                        'action': f'Consolidate {category} work into single session'
                    })
        
        # Time-based consolidation for overlapping work
        active_sessions = []
        for time_key, sessions in time_clusters.items():
            if len(sessions) > 2:
                # Parse time to check if it's recent
                try:
                    cluster_time = datetime.strptime(time_key, '%Y-%m-%d-%H')
                    if cluster_time > datetime.now() - timedelta(hours=6):  # Recent activity
                        active_sessions.extend(sessions)
                except:
                    continue
        
        if len(active_sessions) > 5:
            opportunities.append({
                'type': 'active_session_consolidation',
                'sessions_count': len(active_sessions),
                'potential_savings': len(active_sessions) - 2,  # Keep 2 main sessions
                'priority': 'HIGH',
                'description': f'{len(active_sessions)} sessions active in last 6 hours',
                'action': 'Consider closing completed sessions and merging related work'
            })
        
        return opportunities
    
    def _calculate_fragmentation_score(self, issues: list) -> float:
        """Calculate overall fragmentation score (0-10, higher = more fragmented)"""
        score = 0
        
        for issue in issues:
            if issue['severity'] == 'HIGH':
                score += 3
            elif issue['severity'] == 'MEDIUM':
                score += 2
            else:
                score += 1
        
        # Cap at 10
        return min(score, 10)
    
    def generate_consolidation_report(self, analysis: dict) -> str:
        """Generate human-readable consolidation report"""
        report = []
        
        report.append("🔄 Session Consolidation Analysis")
        report.append(f"   Generated: {analysis['analysis_timestamp']}")
        report.append(f"   Total sessions analyzed: {analysis['total_sessions']}")
        report.append(f"   Fragmentation score: {analysis['fragmentation_score']:.1f}/10")
        report.append("")
        
        # Session distribution
        report.append("📊 Session Distribution by Category:")
        for category, sessions in analysis['categorized_sessions'].items():
            report.append(f"   • {category}: {len(sessions)} sessions")
        report.append("")
        
        # Fragmentation issues
        if analysis['fragmentation_issues']:
            report.append("⚠️  Fragmentation Issues Detected:")
            for issue in analysis['fragmentation_issues']:
                severity_icon = {
                    'HIGH': '🚨',
                    'MEDIUM': '⚠️',
                    'LOW': 'ℹ️'
                }.get(issue['severity'], '•')
                
                report.append(f"   {severity_icon} {issue['description']}")
                if issue.get('sessions'):
                    session_preview = ', '.join(issue['sessions'][:3])
                    if len(issue['sessions']) > 3:
                        session_preview += f" (+{len(issue['sessions']) - 3} more)"
                    report.append(f"     Sessions: {session_preview}")
            report.append("")
        
        # Consolidation opportunities
        if analysis['consolidation_opportunities']:
            report.append("💡 Consolidation Opportunities:")
            for opp in analysis['consolidation_opportunities']:
                priority_icon = {
                    'HIGH': '🚨',
                    'MEDIUM': '⚠️',
                    'LOW': 'ℹ️'
                }.get(opp['priority'], '•')
                
                report.append(f"   {priority_icon} {opp['description']}")
                report.append(f"     Action: {opp['action']}")
                if 'potential_savings' in opp:
                    report.append(f"     Potential savings: {opp['potential_savings']} sessions")
            report.append("")
        
        # Recommendations
        report.append("🎯 Recommendations:")
        
        if analysis['fragmentation_score'] > 7:
            report.append("   🚨 HIGH fragmentation detected:")
            report.append("     • Consider closing completed sessions")
            report.append("     • Merge related work into fewer sessions")
            report.append("     • Use sub-agents for isolated technical tasks")
        elif analysis['fragmentation_score'] > 4:
            report.append("   ⚠️  MEDIUM fragmentation detected:")
            report.append("     • Review active sessions for merge opportunities")
            report.append("     • Close sessions that are no longer needed")
        else:
            report.append("   ✅ Session organization looks good!")
            report.append("     • Continue current session management practices")
        
        return '\n'.join(report)
    
    def suggest_specific_actions(self, analysis: dict) -> list:
        """Suggest specific actionable steps"""
        actions = []
        
        # High-priority consolidation actions
        for opp in analysis['consolidation_opportunities']:
            if opp['priority'] == 'HIGH':
                actions.append({
                    'priority': 'IMMEDIATE',
                    'action': opp['action'],
                    'expected_benefit': f"Reduce active sessions by {opp.get('potential_savings', 'several')}",
                    'category': opp['type']
                })
        
        # Session cleanup actions
        if analysis['fragmentation_score'] > 6:
            actions.append({
                'priority': 'HIGH',
                'action': 'Review and close completed sessions',
                'expected_benefit': 'Reduce cognitive load and context switching',
                'category': 'cleanup'
            })
        
        # Prevention strategies
        actions.append({
            'priority': 'ONGOING',
            'action': 'Use sessions_spawn for isolated technical tasks',
            'expected_benefit': 'Prevent fragmentation of main sessions',
            'category': 'prevention'
        })
        
        return actions


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 session-consolidation-detector.py <sessions_data_file>")
        print("       python3 session-consolidation-detector.py mock")
        print("")
        print("sessions_data_file should be JSON with format:")
        print('[{"id": "sess1", "title": "...", "last_active": "...", "description": "..."}]')
        sys.exit(1)
    
    detector = SessionConsolidationDetector()
    
    if sys.argv[1] == 'mock':
        # Create mock data for testing
        mock_sessions = [
            {"id": "sess1", "title": "Salesforce Integration", "last_active": "2026-03-05T10:00:00", "description": "OAuth2 authentication issues"},
            {"id": "sess2", "title": "Service Order Workflow", "last_active": "2026-03-05T10:30:00", "description": "Quinn metrics automation"},
            {"id": "sess3", "title": "API Testing", "last_active": "2026-03-05T11:00:00", "description": "Authentication debugging"},
            {"id": "sess4", "title": "Fellow Call Analysis", "last_active": "2026-03-05T11:15:00", "description": "Google Drive integration"},
            {"id": "sess5", "title": "Call Intelligence V2", "last_active": "2026-03-05T11:30:00", "description": "Enhanced system deployment"},
            {"id": "sess6", "title": "Database Migration", "last_active": "2026-03-05T12:00:00", "description": "Schema updates for v2"},
            {"id": "sess7", "title": "Salesforce CLI Fix", "last_active": "2026-03-05T12:30:00", "description": "Authentication repair"},
            {"id": "sess8", "title": "Google Workspace", "last_active": "2026-03-05T13:00:00", "description": "Skill documentation update"}
        ]
        sessions_data = mock_sessions
    else:
        # Load from file
        with open(sys.argv[1], 'r') as f:
            sessions_data = json.load(f)
    
    # Analyze sessions
    analysis = detector.analyze_session_data(sessions_data)
    
    # Generate and print report
    report = detector.generate_consolidation_report(analysis)
    print(report)
    
    # Generate specific actions
    actions = detector.suggest_specific_actions(analysis)
    if actions:
        print("\n🎯 Specific Action Items:")
        for action in actions:
            priority_icon = {
                'IMMEDIATE': '🚨',
                'HIGH': '⚠️',
                'ONGOING': 'ℹ️'
            }.get(action['priority'], '•')
            
            print(f"   {priority_icon} {action['action']}")
            print(f"     Benefit: {action['expected_benefit']}")
    
    # Exit with fragmentation score for automation
    fragmentation_score = analysis['fragmentation_score']
    if fragmentation_score > 7:
        sys.exit(2)  # High fragmentation
    elif fragmentation_score > 4:
        sys.exit(1)  # Medium fragmentation
    else:
        sys.exit(0)  # Low fragmentation


if __name__ == "__main__":
    main()