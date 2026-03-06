#!/usr/bin/env python3
"""
Salesforce Authentication Fixer
Diagnoses and repairs Salesforce connectivity issues automatically
"""

import os
import sys
import subprocess
import requests
import json
import time
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SalesforceAuthFixer:
    
    def __init__(self):
        self.sf_org = "niamh@telnyx.com"
        self.client_id = os.getenv('SF_CLIENT_ID')
        self.client_secret = os.getenv('SF_CLIENT_SECRET')
        self.instance_url = "https://telnyx.my.salesforce.com"
        
    def check_environment_variables(self) -> dict:
        """Check if required environment variables are set"""
        checks = {
            'SF_CLIENT_ID': bool(self.client_id),
            'SF_CLIENT_SECRET': bool(self.client_secret),
            'sf_cli_installed': self._check_sf_cli(),
            'curl_available': self._check_curl()
        }
        
        return checks
    
    def _check_sf_cli(self) -> bool:
        """Check if Salesforce CLI is installed and accessible"""
        try:
            result = subprocess.run(['sf', '--version'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def _check_curl(self) -> bool:
        """Check if curl is available"""
        try:
            result = subprocess.run(['curl', '--version'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def test_oauth2_credentials(self) -> dict:
        """Test OAuth2 client credentials flow"""
        if not self.client_id or not self.client_secret:
            return {
                'success': False,
                'error': 'Missing SF_CLIENT_ID or SF_CLIENT_SECRET environment variables'
            }
        
        auth_url = "https://login.salesforce.com/services/oauth2/token"
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        try:
            response = requests.post(auth_url, data=data, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                return {
                    'success': True,
                    'access_token': token_data.get('access_token'),
                    'instance_url': token_data.get('instance_url', self.instance_url),
                    'expires_in': token_data.get('expires_in', 3600)
                }
            else:
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'error': response.text
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Network error: {str(e)}'
            }
    
    def test_salesforce_cli(self) -> dict:
        """Test Salesforce CLI authentication"""
        if not self._check_sf_cli():
            return {
                'success': False,
                'error': 'Salesforce CLI not installed or not in PATH'
            }
        
        try:
            # Check org list
            result = subprocess.run([
                'sf', 'org', 'list'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Check if our org is authenticated
                if self.sf_org in result.stdout:
                    return {'success': True, 'message': 'CLI authentication working'}
                else:
                    return {
                        'success': False, 
                        'error': f'Org {self.sf_org} not found in authenticated orgs'
                    }
            else:
                return {
                    'success': False,
                    'error': f'CLI error: {result.stderr}'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Salesforce CLI command timed out (possible network issue)'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'CLI test failed: {str(e)}'
            }
    
    def test_api_connectivity(self, access_token: str) -> dict:
        """Test API connectivity with a simple query"""
        if not access_token:
            return {'success': False, 'error': 'No access token provided'}
        
        query_url = f"{self.instance_url}/services/data/v59.0/query/"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        params = {'q': 'SELECT Id FROM User LIMIT 1'}
        
        try:
            response = requests.get(query_url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'message': f'API working, found {data.get("totalSize", 0)} records'
                }
            else:
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'error': response.text
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'API connectivity error: {str(e)}'
            }
    
    def fix_cli_authentication(self) -> dict:
        """Attempt to fix CLI authentication"""
        if not self._check_sf_cli():
            return {
                'success': False,
                'error': 'Cannot fix CLI - Salesforce CLI not installed'
            }
        
        try:
            logger.info("Attempting to re-authenticate Salesforce CLI...")
            
            # Try to login (this will require interactive input)
            result = subprocess.run([
                'sf', 'org', 'login', 'web', 
                '--alias', 'telnyx',
                '--instance-url', 'https://telnyx.my.salesforce.com'
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': 'CLI authentication refreshed'
                }
            else:
                return {
                    'success': False,
                    'error': f'CLI login failed: {result.stderr}'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'CLI login timed out'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'CLI fix failed: {str(e)}'
            }
    
    def create_oauth2_test_script(self) -> str:
        """Create a standalone OAuth2 test script"""
        script_content = f'''#!/usr/bin/env python3
"""
Standalone Salesforce OAuth2 Test
Generated: {datetime.now().isoformat()}
"""

import requests
import os

def test_salesforce_oauth2():
    client_id = os.getenv('SF_CLIENT_ID', '{self.client_id}')
    client_secret = os.getenv('SF_CLIENT_SECRET', '{self.client_secret}')
    
    if not client_id or not client_secret:
        print("❌ Missing SF_CLIENT_ID or SF_CLIENT_SECRET")
        return False
    
    auth_url = "https://login.salesforce.com/services/oauth2/token"
    data = {{
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }}
    
    try:
        response = requests.post(auth_url, data=data, timeout=30)
        
        if response.status_code == 200:
            token_data = response.json()
            print("✅ OAuth2 authentication successful")
            print(f"   Instance URL: {{token_data.get('instance_url')}}")
            print(f"   Token expires in: {{token_data.get('expires_in')}} seconds")
            return True
        else:
            print(f"❌ OAuth2 failed: {{response.status_code}} - {{response.text}}")
            return False
            
    except Exception as e:
        print(f"❌ OAuth2 error: {{e}}")
        return False

if __name__ == "__main__":
    test_salesforce_oauth2()
'''
        
        script_path = os.path.join(os.getcwd(), 'test_sf_oauth2_standalone.py')
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        os.chmod(script_path, 0o755)
        return script_path
    
    def generate_fix_report(self) -> dict:
        """Generate comprehensive fix report"""
        logger.info("🔍 Starting Salesforce authentication diagnosis...")
        
        # Environment checks
        env_checks = self.check_environment_variables()
        
        # OAuth2 test
        oauth2_result = self.test_oauth2_credentials()
        
        # CLI test
        cli_result = self.test_salesforce_cli()
        
        # API connectivity test (if OAuth2 works)
        api_result = None
        if oauth2_result.get('success') and oauth2_result.get('access_token'):
            api_result = self.test_api_connectivity(oauth2_result['access_token'])
        
        # Create standalone test script
        test_script = self.create_oauth2_test_script()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'environment_checks': env_checks,
            'oauth2_test': oauth2_result,
            'cli_test': cli_result,
            'api_test': api_result,
            'test_script_created': test_script,
            'recommendations': []
        }
        
        # Generate recommendations
        if not oauth2_result.get('success'):
            report['recommendations'].append({
                'priority': 'HIGH',
                'action': 'Fix OAuth2 credentials',
                'details': 'Set SF_CLIENT_ID and SF_CLIENT_SECRET environment variables'
            })
        
        if not cli_result.get('success'):
            report['recommendations'].append({
                'priority': 'MEDIUM',
                'action': 'Fix Salesforce CLI',
                'details': 'Run: sf org login web --alias telnyx --instance-url https://telnyx.my.salesforce.com'
            })
        
        if oauth2_result.get('success') and cli_result.get('success'):
            report['recommendations'].append({
                'priority': 'LOW',
                'action': 'Both authentication methods working',
                'details': 'Consider using OAuth2 for automation, CLI for interactive work'
            })
        
        return report
    
    def print_report(self, report: dict):
        """Print formatted diagnosis report"""
        print("🔧 Salesforce Authentication Diagnosis Report")
        print(f"   Generated: {report['timestamp']}")
        print("")
        
        # Environment checks
        print("📋 Environment Checks:")
        for check, status in report['environment_checks'].items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {check}")
        print("")
        
        # OAuth2 results
        oauth2 = report['oauth2_test']
        oauth2_icon = "✅" if oauth2.get('success') else "❌"
        print(f"🔐 OAuth2 Authentication: {oauth2_icon}")
        if oauth2.get('success'):
            print(f"   Instance URL: {oauth2.get('instance_url')}")
            print(f"   Token expires: {oauth2.get('expires_in')} seconds")
        else:
            print(f"   Error: {oauth2.get('error')}")
        print("")
        
        # CLI results
        cli = report['cli_test']
        cli_icon = "✅" if cli.get('success') else "❌"
        print(f"💻 Salesforce CLI: {cli_icon}")
        if cli.get('success'):
            print(f"   Status: {cli.get('message')}")
        else:
            print(f"   Error: {cli.get('error')}")
        print("")
        
        # API results
        if report['api_test']:
            api = report['api_test']
            api_icon = "✅" if api.get('success') else "❌"
            print(f"🌐 API Connectivity: {api_icon}")
            if api.get('success'):
                print(f"   Status: {api.get('message')}")
            else:
                print(f"   Error: {api.get('error')}")
            print("")
        
        # Recommendations
        if report['recommendations']:
            print("💡 Recommendations:")
            for rec in report['recommendations']:
                priority_icon = {"HIGH": "🚨", "MEDIUM": "⚠️", "LOW": "ℹ️"}.get(rec['priority'], "•")
                print(f"   {priority_icon} {rec['action']}")
                print(f"     {rec['details']}")
            print("")
        
        print(f"📄 Standalone test script created: {report['test_script_created']}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--fix':
        # Attempt automatic fix
        fixer = SalesforceAuthFixer()
        
        print("🔧 Attempting automatic Salesforce authentication fix...")
        
        # Try OAuth2 first
        oauth_result = fixer.test_oauth2_credentials()
        if not oauth_result.get('success'):
            print("❌ OAuth2 authentication failed - check environment variables")
            print("   Required: SF_CLIENT_ID, SF_CLIENT_SECRET")
            return 1
        
        print("✅ OAuth2 authentication working")
        
        # Try CLI fix
        cli_fix_result = fixer.fix_cli_authentication()
        if cli_fix_result.get('success'):
            print("✅ CLI authentication fixed")
        else:
            print(f"⚠️  CLI fix failed: {cli_fix_result.get('error')}")
            print("   Manual intervention may be required")
        
        return 0
    
    else:
        # Generate diagnosis report
        fixer = SalesforceAuthFixer()
        report = fixer.generate_fix_report()
        fixer.print_report(report)
        
        # Exit codes for automation
        if report['oauth2_test'].get('success') and report['cli_test'].get('success'):
            return 0  # All good
        elif report['oauth2_test'].get('success'):
            return 1  # OAuth2 works, CLI needs attention
        else:
            return 2  # Critical - OAuth2 broken


if __name__ == "__main__":
    main()