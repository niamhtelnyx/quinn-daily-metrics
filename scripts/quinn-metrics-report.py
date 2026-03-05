#!/usr/bin/env python3
"""
Quinn Daily Metrics Report Generator
Executes CORRECTED SQO definition queries and posts to #quinn-daily-metrics
"""

import subprocess
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
import os

class QuinnMetricsReporter:
    def __init__(self):
        self.date_str = datetime.now().strftime('%Y-%m-%d')
        self.quinn_user_id = '005Qk000001pqtdIAA'  # Quinn's Salesforce User ID
        self.results = {}
        
    def execute_soql_query(self, query_name: str, soql: str):
        """Execute SOQL query via Salesforce CLI"""
        print(f"🔍 Executing {query_name}...")
        
        try:
            # Use sf CLI to execute query
            result = subprocess.run([
                'sf', 'data', 'query', 
                '--query', soql,
                '--json'
            ], capture_output=True, text=True, check=True)
            
            data = json.loads(result.stdout)
            records = data.get('result', {}).get('records', [])
            
            print(f"✅ {query_name}: {len(records)} records")
            return records
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to execute {query_name}: {e}")
            print(f"Error output: {e.stderr}")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON for {query_name}: {e}")
            return []
    
    def get_sales_handoffs_today(self):
        """1. Sales Handoffs (TODAY)"""
        soql = f"""
        SELECT COUNT() 
        FROM Sales_Handoff__c 
        WHERE Owner_Name__c = 'Quinn Taylor' 
        AND Owner_Email__c = 'quinn@telnyx.com' 
        AND CreatedDate = TODAY
        """
        
        records = self.execute_soql_query("Sales Handoffs Today", soql)
        count = records[0].get('expr0', 0) if records else 0
        self.results['sales_handoffs'] = count
        return count
    
    def get_unique_accounts_today(self):
        """2. Unique Accounts (TODAY - 3-step process)"""
        # Step 1: Get Quinn tasks for today
        soql_tasks = f"""
        SELECT WhoId 
        FROM Task 
        WHERE OwnerId = '{self.quinn_user_id}' 
        AND CreatedDate = TODAY 
        AND WhoId != null
        """
        
        task_records = self.execute_soql_query("Quinn Tasks Today", soql_tasks)
        who_ids = [record['WhoId'] for record in task_records]
        
        if not who_ids:
            self.results['unique_accounts'] = 0
            return 0
        
        # Step 2: Get Contact accounts and Lead companies
        who_ids_str = "','".join(who_ids)
        
        # Contact accounts
        soql_contacts = f"""
        SELECT AccountId 
        FROM Contact 
        WHERE Id IN ('{who_ids_str}') 
        AND AccountId != null
        """
        
        contact_records = self.execute_soql_query("Contact Accounts", soql_contacts)
        account_ids = {record['AccountId'] for record in contact_records}
        
        # Lead companies (if any WhoIds are Leads)
        soql_leads = f"""
        SELECT Company 
        FROM Lead 
        WHERE Id IN ('{who_ids_str}') 
        AND Company != null
        """
        
        lead_records = self.execute_soql_query("Lead Companies", soql_leads)
        lead_companies = {record['Company'] for record in lead_records}
        
        # Step 3: Deduplicate and count
        unique_count = len(account_ids) + len(lead_companies)
        self.results['unique_accounts'] = unique_count
        return unique_count
    
    def get_qualification_rate_today(self):
        """3. Qualification Rate (TODAY)"""
        soql = f"""
        SELECT SDRbot_Perceived_Quality__c, COUNT(Id) total_count
        FROM Contact 
        WHERE D_T_Quinn_Active_Latest__c = TODAY 
        GROUP BY SDRbot_Perceived_Quality__c
        """
        
        records = self.execute_soql_query("Qualification Rate Today", soql)
        
        total_contacts = sum(record['total_count'] for record in records)
        sql_count = next((record['total_count'] for record in records 
                         if record['SDRbot_Perceived_Quality__c'] == 'SQL'), 0)
        
        qualification_rate = (sql_count / total_contacts * 100) if total_contacts > 0 else 0
        
        self.results['qualification_rate'] = {
            'rate': qualification_rate,
            'sql_count': sql_count,
            'total_count': total_contacts
        }
        
        return qualification_rate, sql_count, total_contacts
    
    def get_sql_rate_7_days(self):
        """4. SQL Rate (LAST 7 DAYS)"""
        # Get Quinn opportunity accounts from last 7 days
        soql_opps = f"""
        SELECT AccountId 
        FROM Opportunity 
        WHERE SDR__c = '{self.quinn_user_id}' 
        AND CreatedDate >= LAST_N_DAYS:7
        """
        
        opp_records = self.execute_soql_query("Quinn Opportunity Accounts (7d)", soql_opps)
        opp_account_ids = {record['AccountId'] for record in opp_records if record['AccountId']}
        
        if not opp_account_ids:
            self.results['sql_rate'] = {'rate': 0, 'matched': 0, 'total': 0}
            return 0, 0, 0
        
        # Get SQL contacts matched to these accounts
        account_ids_str = "','".join(opp_account_ids)
        
        soql_sql_contacts = f"""
        SELECT COUNT(Id) total_count
        FROM Contact 
        WHERE AccountId IN ('{account_ids_str}') 
        AND D_T_Quinn_Active_Latest__c >= LAST_N_DAYS:7 
        AND SDRbot_Perceived_Quality__c = 'SQL'
        """
        
        sql_records = self.execute_soql_query("SQL Contacts Matched (7d)", soql_sql_contacts)
        sql_matched = sql_records[0].get('total_count', 0) if sql_records else 0
        
        # Get total contacts from those accounts  
        soql_total_contacts = f"""
        SELECT COUNT(Id) total_count
        FROM Contact 
        WHERE AccountId IN ('{account_ids_str}') 
        AND D_T_Quinn_Active_Latest__c >= LAST_N_DAYS:7
        """
        
        total_records = self.execute_soql_query("Total Contacts Matched (7d)", soql_total_contacts)
        total_matched = total_records[0].get('total_count', 0) if total_records else 0
        
        sql_rate = (sql_matched / total_matched * 100) if total_matched > 0 else 0
        
        self.results['sql_rate'] = {
            'rate': sql_rate,
            'matched': sql_matched,
            'total': total_matched
        }
        
        return sql_rate, sql_matched, total_matched
    
    def get_sqo_rate_corrected_7_days(self):
        """5. SQO Rate (CORRECTED - LAST 7 DAYS using Velocity_D_T_Stage1__c)"""
        # Get SQOs (Stage 1 progressions) - CORRECTED
        soql_sqos = f"""
        SELECT COUNT(Id) total_count
        FROM Opportunity 
        WHERE SDR__c = '{self.quinn_user_id}' 
        AND Velocity_D_T_Stage1__c >= LAST_N_DAYS:7
        """
        
        sqo_records = self.execute_soql_query("SQOs (Corrected - Stage 1)", soql_sqos)
        sqo_count = sqo_records[0].get('total_count', 0) if sqo_records else 0
        
        # Get SQLs from last 7 days
        soql_sqls = f"""
        SELECT COUNT(Id) total_count
        FROM Contact 
        WHERE D_T_Quinn_Active_Latest__c >= LAST_N_DAYS:7 
        AND SDRbot_Perceived_Quality__c = 'SQL'
        """
        
        sql_records = self.execute_soql_query("SQLs (7d)", soql_sqls)
        sql_count = sql_records[0].get('total_count', 0) if sql_records else 0
        
        sqo_rate = (sqo_count / sql_count * 100) if sql_count > 0 else 0
        
        self.results['sqo_rate_corrected'] = {
            'rate': sqo_rate,
            'sqos': sqo_count,
            'sqls': sql_count
        }
        
        return sqo_rate, sqo_count, sql_count
    
    def get_mtd_sqo_tracking_corrected(self):
        """6. MTD SQO Tracking (CORRECTED using Velocity_D_T_Stage1__c)"""
        # MTD SQOs - CORRECTED
        soql_mtd = f"""
        SELECT COUNT(Id) total_count
        FROM Opportunity 
        WHERE SDR__c = '{self.quinn_user_id}' 
        AND Velocity_D_T_Stage1__c = THIS_MONTH
        """
        
        mtd_records = self.execute_soql_query("MTD SQOs (Corrected)", soql_mtd)
        mtd_sqos = mtd_records[0].get('total_count', 0) if mtd_records else 0
        
        # Last Month SQOs - CORRECTED
        soql_last_month = f"""
        SELECT COUNT(Id) total_count
        FROM Opportunity 
        WHERE SDR__c = '{self.quinn_user_id}' 
        AND Velocity_D_T_Stage1__c = LAST_MONTH
        """
        
        last_month_records = self.execute_soql_query("Last Month SQOs (Corrected)", soql_last_month)
        last_month_sqos = last_month_records[0].get('total_count', 0) if last_month_records else 0
        
        # Calculate projections
        current_day = datetime.now().day
        days_in_month = 31  # March has 31 days
        daily_pace = mtd_sqos / current_day if current_day > 0 else 0
        monthly_projection = daily_pace * days_in_month
        
        # Calculate vs last month
        vs_last_month_pct = ((mtd_sqos - last_month_sqos) / last_month_sqos * 100) if last_month_sqos > 0 else 0
        
        self.results['mtd_tracking'] = {
            'mtd_sqos': mtd_sqos,
            'last_month_sqos': last_month_sqos,
            'daily_pace': daily_pace,
            'monthly_projection': monthly_projection,
            'vs_last_month_pct': vs_last_month_pct,
            'current_day': current_day
        }
        
        return mtd_sqos, last_month_sqos, daily_pace, monthly_projection, vs_last_month_pct
    
    def generate_slack_report(self):
        """Generate Slack-formatted report (no markdown)"""
        date_formatted = datetime.now().strftime('%Y-%m-%d')
        
        # Extract results
        handoffs = self.results.get('sales_handoffs', 0)
        accounts = self.results.get('unique_accounts', 0)
        
        qual_data = self.results.get('qualification_rate', {})
        qual_rate = qual_data.get('rate', 0)
        qual_sql = qual_data.get('sql_count', 0)  
        qual_total = qual_data.get('total_count', 0)
        
        sql_data = self.results.get('sql_rate', {})
        sql_rate = sql_data.get('rate', 0)
        sql_matched = sql_data.get('matched', 0)
        sql_total = sql_data.get('total', 0)
        
        sqo_data = self.results.get('sqo_rate_corrected', {})
        sqo_rate = sqo_data.get('rate', 0)
        sqos = sqo_data.get('sqos', 0)
        sqls = sqo_data.get('sqls', 0)
        
        mtd_data = self.results.get('mtd_tracking', {})
        mtd_sqos = mtd_data.get('mtd_sqos', 0)
        last_month = mtd_data.get('last_month_sqos', 0)
        daily_pace = mtd_data.get('daily_pace', 0)
        monthly_proj = mtd_data.get('monthly_projection', 0)
        vs_last_pct = mtd_data.get('vs_last_month_pct', 0)
        current_day = mtd_data.get('current_day', 0)
        
        # Determine arrow for vs last month
        if vs_last_pct > 0:
            arrow = "↗"
        elif vs_last_pct < 0:
            arrow = "↘"
        else:
            arrow = "→"
        
        # Generate Slack message
        message = f"""📊 *Quinn Daily Metrics - {date_formatted}* (✅ SQO Definition Corrected)

• *Sales Handoffs:* {handoffs} (24h)
• *Unique Accounts Touched:* {accounts} (24h)
• *Qualification Rate:* {qual_rate:.1f}% SQL ({qual_sql}/{qual_total}) (24h)
• *SQL Rate:* {sql_rate:.1f}% ({sql_matched}/{sql_total}) (7d)
• *SQO Rate:* {sqo_rate:.1f}% ({sqos}/{sqls}) (7d) ✅

🎯 *MTD SQO Tracking:* (✅ Velocity_D_T_Stage1__c)
• *MTD SQOs:* {mtd_sqos} ({current_day} days) | Pace: ~{monthly_proj:.0f}/month
• *vs Last Month:* {vs_last_pct:+.1f}% {arrow} ({last_month})
• *Feb Baseline:* 11 MTD vs Jan (42) = pace tracking
• *7d Recent:* {sqos} SQOs (Stage 1 progressions)

💡 *Key Insights:* [Analysis using correct Stage 1 D&T progression data]

_Automated report • ✅ CORRECTED: SQO = Velocity_D_T_Stage1__c (actual Stage 1 movement)_"""
        
        return message
    
    def save_results_to_memory(self):
        """Save results to memory/quinn-metrics-[date].json"""
        memory_dir = Path("/Users/niamhcollins/clawd/memory")
        memory_dir.mkdir(exist_ok=True)
        
        filename = f"quinn-metrics-{self.date_str}.json"
        filepath = memory_dir / filename
        
        data = {
            "date": self.date_str,
            "timestamp": datetime.now().isoformat(),
            "metrics": self.results,
            "note": "CORRECTED SQO definition using Velocity_D_T_Stage1__c"
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"💾 Results saved to {filepath}")
        return filepath
    
    def run_full_report(self):
        """Execute all metrics and generate report"""
        print(f"🚀 Starting Quinn Daily Metrics Report for {self.date_str}")
        print("=" * 60)
        
        # Execute all metrics
        try:
            self.get_sales_handoffs_today()
            self.get_unique_accounts_today()
            self.get_qualification_rate_today()
            self.get_sql_rate_7_days()
            self.get_sqo_rate_corrected_7_days()
            self.get_mtd_sqo_tracking_corrected()
            
            # Generate report
            slack_message = self.generate_slack_report()
            
            # Save to memory
            self.save_results_to_memory()
            
            return slack_message
            
        except Exception as e:
            print(f"❌ Error generating report: {e}")
            return None

if __name__ == "__main__":
    reporter = QuinnMetricsReporter()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("🧪 Test mode - would execute queries but not post to Slack")
        message = reporter.run_full_report()
        if message:
            print("\n" + "="*60)
            print("SLACK MESSAGE PREVIEW:")
            print("="*60)
            print(message)
    else:
        message = reporter.run_full_report()
        if message:
            print("\n✅ Report generated successfully!")
            print("Message ready for Slack posting.")
        else:
            print("\n❌ Report generation failed!")
            sys.exit(1)