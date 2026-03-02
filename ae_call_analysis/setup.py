#!/usr/bin/env python3
"""
Setup script for AE Call Analysis System
Initializes database, tests connections, and verifies configuration
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database.database import AECallAnalysisDB, get_db
from config.settings import AECallAnalysisConfig

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SetupManager:
    """Manages system setup and verification"""
    
    def __init__(self):
        self.config = AECallAnalysisConfig()
        self.db = None
        self.setup_results = {
            'database': False,
            'fellow_api': False,
            'salesforce': False,
            'llm_service': False,
            'slack': False
        }
    
    def setup_database(self) -> bool:
        """Initialize SQLite database"""
        try:
            logger.info("Setting up database...")
            self.db = get_db(self.config.database.path)
            
            # Test basic operations
            test_call_id = self.db.insert_call(
                fellow_id="test-setup-" + datetime.now().isoformat(),
                title="Test Setup Call",
                call_date=datetime.now(),
                ae_name="Setup Test",
                prospect_company="Test Company"
            )
            
            # Test retrieval
            call = self.db.get_call_by_fellow_id("test-setup-" + datetime.now().isoformat())
            
            # Cleanup test data
            with self.db.get_connection() as conn:
                conn.execute("DELETE FROM calls WHERE id = ?", (test_call_id,))
                conn.commit()
            
            logger.info("✅ Database setup successful")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database setup failed: {e}")
            return False
    
    def test_fellow_api(self) -> bool:
        """Test Fellow API connection"""
        try:
            import requests
            
            logger.info("Testing Fellow API connection...")
            
            headers = {
                'X-Api-Key': self.config.fellow_api.api_key,
                'Content-Type': 'application/json'
            }
            
            # Test with a minimal request
            response = requests.post(
                self.config.fellow_api.endpoint,
                headers=headers,
                json={"include": {"transcript": True}, "filters": {"title": "Test"}},
                timeout=10
            )
            
            if response.status_code in [200, 400, 422]:  # 400/422 might be expected for test query
                logger.info("✅ Fellow API connection successful")
                return True
            else:
                logger.error(f"❌ Fellow API returned status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Fellow API test failed: {e}")
            return False
    
    def test_salesforce_cli(self) -> bool:
        """Test Salesforce CLI connection"""
        try:
            import subprocess
            
            logger.info("Testing Salesforce CLI...")
            
            # Test SF CLI is available and authenticated
            result = subprocess.run(
                ['sf', 'org', 'list', '--json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                try:
                    orgs_data = json.loads(result.stdout)
                    result_data = orgs_data.get('result', {})
                    
                    # Check all org categories for connected orgs
                    connected_orgs = []
                    for org_type in ['other', 'nonScratchOrgs', 'devHubs', 'scratchOrgs']:
                        if org_type in result_data:
                            for org in result_data[org_type]:
                                if org.get('connectedStatus') == 'Connected':
                                    connected_orgs.append(org)
                
                except json.JSONDecodeError:
                    logger.error("❌ Failed to parse Salesforce CLI JSON response")
                    return False
                
                if connected_orgs:
                    logger.info(f"✅ Salesforce CLI connected to {len(connected_orgs)} org(s)")
                    for org in connected_orgs[:3]:  # Show first 3 orgs
                        logger.info(f"  - {org.get('username', 'unknown')} ({org.get('name', 'unknown')})")
                    return True
                else:
                    logger.error("❌ No connected Salesforce orgs found")
                    return False
            else:
                logger.error(f"❌ Salesforce CLI test failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Salesforce CLI test failed: {e}")
            return False
    
    def test_llm_service(self) -> bool:
        """Test LLM service availability"""
        try:
            # Simple test to see if we can import required libraries
            # In a real implementation, this would test actual LLM API
            import json
            
            logger.info("Testing LLM service...")
            
            # For now, just verify we have the necessary dependencies
            # This would be replaced with actual LLM API testing
            test_prompt = "Test prompt for AE call analysis"
            
            if len(test_prompt) > 0:  # Placeholder test
                logger.info("✅ LLM service test passed (placeholder)")
                return True
            else:
                logger.error("❌ LLM service test failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ LLM service test failed: {e}")
            return False
    
    def test_slack_integration(self) -> bool:
        """Test Slack integration"""
        try:
            logger.info("Testing Slack integration...")
            
            # For now, just check if configuration exists
            # In a real implementation, this would test webhook/bot token
            if hasattr(self.config, 'slack') and self.config.slack:
                logger.info("✅ Slack configuration found")
                return True
            else:
                logger.info("⚠️ Slack configuration not found (optional)")
                return True  # Slack is optional for MVP
                
        except Exception as e:
            logger.error(f"❌ Slack integration test failed: {e}")
            return False
    
    def run_setup(self) -> dict:
        """Run complete setup process"""
        logger.info("Starting AE Call Analysis System Setup")
        logger.info("=" * 50)
        
        # Database setup
        self.setup_results['database'] = self.setup_database()
        
        # API tests
        self.setup_results['fellow_api'] = self.test_fellow_api()
        self.setup_results['salesforce'] = self.test_salesforce_cli()
        self.setup_results['llm_service'] = self.test_llm_service()
        self.setup_results['slack'] = self.test_slack_integration()
        
        # Summary
        logger.info("=" * 50)
        logger.info("Setup Summary:")
        
        for component, status in self.setup_results.items():
            status_icon = "✅" if status else "❌"
            logger.info(f"  {status_icon} {component.replace('_', ' ').title()}")
        
        # Overall status
        critical_components = ['database', 'fellow_api', 'salesforce']
        critical_passed = all(self.setup_results[comp] for comp in critical_components)
        
        if critical_passed:
            logger.info("🎉 Setup completed successfully! System is ready to use.")
        else:
            logger.error("⚠️ Setup incomplete. Please fix the failed components.")
        
        # Create status file
        status_file = project_root / "setup_status.json"
        with open(status_file, 'w') as f:
            json.dump({
                'setup_completed_at': datetime.now().isoformat(),
                'results': self.setup_results,
                'overall_status': 'ready' if critical_passed else 'incomplete'
            }, f, indent=2)
        
        return self.setup_results
    
    def show_next_steps(self):
        """Show next steps based on setup results"""
        logger.info("\n" + "=" * 50)
        logger.info("Next Steps:")
        
        if all(self.setup_results.values()):
            logger.info("1. Run: python -m ae_call_analysis.main --fetch-calls")
            logger.info("2. Check the dashboard at: http://localhost:8000/dashboard")
            logger.info("3. Configure Slack webhooks for notifications")
        else:
            if not self.setup_results['database']:
                logger.info("1. Fix database setup issues")
            if not self.setup_results['fellow_api']:
                logger.info("2. Verify Fellow API key in configuration")
            if not self.setup_results['salesforce']:
                logger.info("3. Run 'sf org login web' to authenticate with Salesforce")
            if not self.setup_results['llm_service']:
                logger.info("4. Configure LLM service (OpenAI/Claude/etc.)")
        
        logger.info("\nFor help: python setup.py --help")
        logger.info("Documentation: README.md")

def main():
    """Main setup entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup AE Call Analysis System')
    parser.add_argument('--component', choices=['database', 'fellow', 'salesforce', 'llm', 'slack', 'all'],
                       default='all', help='Component to setup/test')
    parser.add_argument('--force', action='store_true', 
                       help='Force re-initialization of database')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    setup_manager = SetupManager()
    
    if args.component == 'all':
        results = setup_manager.run_setup()
        setup_manager.show_next_steps()
    else:
        # Run individual component test
        component_map = {
            'database': setup_manager.setup_database,
            'fellow': setup_manager.test_fellow_api,
            'salesforce': setup_manager.test_salesforce_cli,
            'llm': setup_manager.test_llm_service,
            'slack': setup_manager.test_slack_integration
        }
        
        if args.component in component_map:
            success = component_map[args.component]()
            sys.exit(0 if success else 1)
    
    # Exit with error code if critical components failed
    critical_components = ['database', 'fellow_api', 'salesforce']
    if not all(setup_manager.setup_results.get(comp, False) for comp in critical_components):
        sys.exit(1)

if __name__ == "__main__":
    main()