#!/usr/bin/env python3
"""
Company Business Intelligence Enhancement
Adds company research and business insights to Call Intelligence alerts
"""

import subprocess
import json
import sqlite3
import os
from datetime import datetime
from typing import Dict, Optional

class CompanyIntelligence:
    """Add company business insights to call intelligence"""
    
    def __init__(self, org_username: str = "niamh@telnyx.com", db_path: str = "ae_call_analysis.db"):
        self.org_username = org_username
        self.db_path = db_path
    
    def get_company_data_from_contact(self, contact_id: str) -> Dict:
        """Get company data from Salesforce Contact record"""
        
        query = f"""
        SELECT AccountId, Account.Name, Account.Website, 
               Account.Industry, Account.Description, Account.NumberOfEmployees,
               Account.AnnualRevenue, Account.Type
        FROM Contact 
        WHERE Id = '{contact_id}'
        """
        
        try:
            cmd = [
                'sf', 'data', 'query',
                '--query', query,
                '--target-org', self.org_username,
                '--json'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                response = json.loads(result.stdout)
                records = response.get('result', {}).get('records', [])
                
                if records:
                    contact = records[0]
                    account_data = {
                        'account_id': contact.get('AccountId'),
                        'company_name': contact.get('Account', {}).get('Name', 'Unknown'),
                        'website': contact.get('Account', {}).get('Website'),
                        'industry': contact.get('Account', {}).get('Industry'),
                        'description': contact.get('Account', {}).get('Description'),
                        'employees': contact.get('Account', {}).get('NumberOfEmployees'),
                        'revenue': contact.get('Account', {}).get('AnnualRevenue'),
                        'account_type': contact.get('Account', {}).get('Type')
                    }
                    return account_data
                    
            print(f"❌ Failed to get company data: {result.stderr if result.returncode != 0 else 'No records'}")
            return {}
            
        except Exception as e:
            print(f"❌ Error getting company data: {e}")
            return {}
    
    def generate_business_insight(self, company_data: Dict) -> str:
        """Generate 1-sentence business insight from company data"""
        
        company_name = company_data.get('company_name', 'Unknown Company')
        industry = company_data.get('industry', '')
        description = company_data.get('description', '')
        website = company_data.get('website', '')
        employees = company_data.get('employees')
        revenue = company_data.get('revenue')
        
        # Build insight based on available data
        insight_parts = []
        
        # Start with company name
        insight_parts.append(company_name)
        
        # Add industry/business type
        if industry:
            if industry == "Internet Software & Services":
                insight_parts.append("is a digital services company")
            elif "Technology" in industry:
                insight_parts.append("is a technology company")
            elif "Manufacturing" in industry:
                insight_parts.append("is a manufacturing company")
            else:
                insight_parts.append(f"operates in {industry.lower()}")
        else:
            insight_parts.append("is a business")
        
        # Add main service/product from description
        if description:
            # Extract key services from description
            desc_lower = description.lower()
            services = []
            
            if 'consulting' in desc_lower:
                services.append('consulting')
            if 'website' in desc_lower or 'web' in desc_lower:
                services.append('web development')
            if 'seo' in desc_lower:
                services.append('SEO')
            if 'support' in desc_lower:
                services.append('support services')
            if 'software' in desc_lower:
                services.append('software solutions')
            if 'api' in desc_lower:
                services.append('API services')
                
            if services:
                if len(services) == 1:
                    insight_parts.append(f"specializing in {services[0]}")
                else:
                    insight_parts.append(f"offering {', '.join(services[:-1])}, and {services[-1]}")
        
        # Add size context if available
        if employees:
            if employees < 10:
                insight_parts.append("(small business)")
            elif employees < 100:
                insight_parts.append("(mid-size company)")
            else:
                insight_parts.append("(enterprise)")
        
        # Combine into single sentence
        base_insight = " ".join(insight_parts)
        
        # Add website if available for validation
        if website:
            base_insight += f" ({website})"
        
        return base_insight + "."
    
    def store_company_intelligence(self, call_id: int, company_data: Dict, business_insight: str, research_data: Dict = None):
        """Store company intelligence in database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert company intelligence (table already created in schema)
            cursor.execute('''
            INSERT OR REPLACE INTO company_intelligence 
            (call_id, account_id, company_name, website, industry, description, 
             employees, revenue, account_type, business_insight, research_data, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                call_id,
                company_data.get('account_id'),
                company_data.get('company_name'),
                company_data.get('website'),
                company_data.get('industry'),
                company_data.get('description'),
                company_data.get('employees'),
                company_data.get('revenue'),
                company_data.get('account_type'),
                business_insight,
                json.dumps(research_data) if research_data else None,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Error storing company intelligence: {e}")
            return False
    
    def get_company_intelligence_by_call_id(self, call_id: int) -> Optional[Dict]:
        """Get stored company intelligence for a call"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT account_id, company_name, website, industry, description, 
                   employees, revenue, account_type, business_insight, research_data,
                   created_at, updated_at
            FROM company_intelligence 
            WHERE call_id = ?
            ''', (call_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'account_id': row[0],
                    'company_name': row[1],
                    'website': row[2],
                    'industry': row[3],
                    'description': row[4],
                    'employees': row[5],
                    'revenue': row[6],
                    'account_type': row[7],
                    'business_insight': row[8],
                    'research_data': json.loads(row[9]) if row[9] else None,
                    'created_at': row[10],
                    'updated_at': row[11]
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting company intelligence: {e}")
            return None

    def enhance_call_from_db(self, call_id: int) -> Dict:
        """Enhance a call with company intelligence using existing salesforce mapping"""
        
        try:
            # Get contact_id from salesforce_mappings
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT contact_id, contact_name FROM salesforce_mappings 
            WHERE call_id = ? AND contact_id IS NOT NULL
            ''', (call_id,))
            
            mapping = cursor.fetchone()
            conn.close()
            
            if not mapping or not mapping[0]:
                return {
                    'success': False,
                    'error': f'No Salesforce contact mapping found for call {call_id}'
                }
            
            contact_id = mapping[0]
            contact_name = mapping[1]
            
            print(f"🔗 Found contact mapping: {contact_name} ({contact_id})")
            
            # Use existing enhancement method
            result = self.enhance_call_with_company_intelligence('', contact_id, call_id)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Database error: {str(e)}'
            }

    def enhance_call_with_company_intelligence(self, event_id: str, contact_id: str, call_id: int = None) -> Dict:
        """Complete enhancement: get company data, generate insight, store in DB"""
        
        print(f"🏢 Enhancing call with company intelligence...")
        
        # Step 1: Get company data from Salesforce
        company_data = self.get_company_data_from_contact(contact_id)
        
        if not company_data.get('company_name'):
            return {
                'success': False,
                'error': 'No company data found'
            }
        
        print(f"✅ Company data: {company_data['company_name']}")
        
        # Step 2: Generate business insight
        business_insight = self.generate_business_insight(company_data)
        print(f"💡 Business insight: {business_insight}")
        
        # Step 3: Store in database if call_id provided
        stored = False
        if call_id:
            stored = self.store_company_intelligence(call_id, company_data, business_insight)
            if stored:
                print(f"💾 Company intelligence stored for call {call_id}")
        
        return {
            'success': True,
            'company_data': company_data,
            'business_insight': business_insight,
            'stored_in_db': stored,
            'enhanced_at': datetime.now().isoformat()
        }

def demo_company_intelligence():
    """Demo the company intelligence enhancement"""
    
    print("🏢 COMPANY INTELLIGENCE ENHANCEMENT DEMO")
    print("="*60)
    
    intelligence = CompanyIntelligence()
    
    # Test with Nick Mihalovich contact (we know this has good company data)
    test_contact_id = "003Qk00000jw4fsIAA"  # Nick Mihalovich
    test_event_id = "00UQk00000OMYzhMAH"
    
    print(f"Testing with Contact ID: {test_contact_id}")
    
    # Run enhancement
    result = intelligence.enhance_call_with_company_intelligence(test_event_id, test_contact_id)
    
    if result['success']:
        company_data = result['company_data']
        business_insight = result['business_insight']
        
        print(f"\\n🎯 ENHANCEMENT COMPLETE:")
        print(f"Company: {company_data['company_name']}")
        print(f"Website: {company_data['website']}")
        print(f"Industry: {company_data['industry']}")
        print(f"Business Insight: {business_insight}")
        
        print(f"\\n📝 CALL INTELLIGENCE PREVIEW WITH COMPANY DATA:")
        print(f"**Nick Mihalovich & Darren Dunner** | **Rob Messier** | 2026-03-03")
        print(f"**🏢 Company:** {business_insight}")
        print(f"**📊 Scores:** Interest 7/10 | AE 8/10 | Quinn 8/10")
        
        # Save for integration
        with open('company_intelligence_demo.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\\n💾 Company intelligence demo saved")
        print(f"🎯 Ready to integrate into Call Intelligence alerts!")
        
        return result
        
    else:
        print(f"❌ Enhancement failed: {result['error']}")
        return None

if __name__ == "__main__":
    demo_company_intelligence()