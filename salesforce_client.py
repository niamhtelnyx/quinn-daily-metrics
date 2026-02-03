#!/usr/bin/env python3
"""
Salesforce CLI integration for Service Order Specialist
Uses sf CLI for all Salesforce operations following Telnyx architecture
"""

import asyncio
import json
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

class SalesforceClient:
    """Salesforce integration using sf CLI"""
    
    def __init__(self, org_username: str = "niamh@telnyx.com"):
        self.org_username = org_username
    
    async def _execute_sf_command(self, cmd: List[str]) -> Dict[str, Any]:
        """Execute sf CLI command and return parsed JSON result"""
        try:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                raise Exception(f"sf CLI error: {stderr.decode()}")
            
            return json.loads(stdout.decode())
        except json.JSONDecodeError:
            raise Exception("Invalid JSON response from sf CLI")
        except Exception as e:
            raise Exception(f"sf CLI execution failed: {str(e)}")
    
    async def lookup_service_orders(
        self, 
        customer_name: str, 
        include_terminated: bool = False,
        org_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Look up service orders for a customer"""
        
        # Base query for service orders
        base_query = """
        SELECT Id, Name, Stage__c, Contract_Start_Date__c, Contract_End_Date__c, 
               Contract_Duration__c, Min_Monthly_Commit__c, Rev_Ops_Approved__c, 
               commitment_handler_id__c, Opportunity__c, Mission_Control_Account__c
        FROM Service_Order__c 
        WHERE Name LIKE '%{customer}%'
        """.format(customer=customer_name.replace("'", "\\'"))
        
        if not include_terminated:
            base_query += " AND Stage__c != 'Terminated'"
        
        cmd = [
            "sf", "data", "query",
            "-o", self.org_username,
            "--query", base_query,
            "--json"
        ]
        
        sf_result = await self._execute_sf_command(cmd)
        service_orders = sf_result.get("result", {}).get("records", [])
        
        # If org_id provided, validate it matches
        validation_result = None
        if org_id and service_orders:
            validation_result = await self._validate_org_id(service_orders[0], org_id)
        
        return {
            "lookup_successful": True,
            "customer": customer_name,
            "service_orders_found": len(service_orders),
            "service_orders": service_orders,
            "org_id_validation": validation_result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _validate_org_id(self, service_order: Dict[str, Any], provided_org_id: str) -> Dict[str, Any]:
        """Validate that the provided org ID matches the customer's actual org ID"""
        
        mc_account_id = service_order.get("Mission_Control_Account__c")
        if not mc_account_id:
            return {
                "validation_passed": False,
                "error": "No Mission Control Account found on service order"
            }
        
        # Query Mission Control Account for Organization ID
        cmd = [
            "sf", "data", "query",
            "-o", self.org_username,
            "--query", f"SELECT Id, Name, Organization_ID__c FROM Mission_Control_Account__c WHERE Id = '{mc_account_id}'",
            "--json"
        ]
        
        sf_result = await self._execute_sf_command(cmd)
        mc_accounts = sf_result.get("result", {}).get("records", [])
        
        if not mc_accounts:
            return {
                "validation_passed": False,
                "error": f"Mission Control Account {mc_account_id} not found"
            }
        
        actual_org_id = mc_accounts[0].get("Organization_ID__c")
        
        return {
            "validation_passed": actual_org_id == provided_org_id,
            "provided_org_id": provided_org_id,
            "actual_org_id": actual_org_id,
            "mission_control_account": mc_accounts[0]
        }
    
    async def update_service_order(
        self, 
        service_order_id: str, 
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a service order with new field values"""
        
        # Build update values string
        update_values = []
        for field, value in updates.items():
            if isinstance(value, str):
                update_values.append(f"{field}='{value}'")
            elif isinstance(value, bool):
                update_values.append(f"{field}={str(value).lower()}")
            else:
                update_values.append(f"{field}={value}")
        
        update_string = " ".join(update_values)
        
        cmd = [
            "sf", "data", "update", "record",
            "-o", self.org_username,
            "-s", "Service_Order__c",
            "-i", service_order_id,
            "-v", update_string,
            "--json"
        ]
        
        sf_result = await self._execute_sf_command(cmd)
        
        return {
            "update_successful": True,
            "service_order_id": service_order_id,
            "updates_applied": updates,
            "salesforce_result": sf_result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_service_order_details(self, service_order_id: str) -> Dict[str, Any]:
        """Get Service Order Details records (for ramped commitments)"""
        
        cmd = [
            "sf", "data", "query",
            "-o", self.org_username,
            "--query", f"""
            SELECT Id, Name, Cycle_Number__c, Commit_Amount__c, Commit_Duration__c, 
                   Commit_Start_Date__c, Commit_End_Date__c, 
                   Commit_Start_Date_Normalized__c, Commit_End_Date_Normalized__c 
            FROM Service_Order_Details__c 
            WHERE Service_Order__c = '{service_order_id}' 
            ORDER BY Cycle_Number__c
            """,
            "--json"
        ]
        
        sf_result = await self._execute_sf_command(cmd)
        details = sf_result.get("result", {}).get("records", [])
        
        commitment_type = "ramped" if details else "static"
        
        return {
            "service_order_id": service_order_id,
            "commitment_type": commitment_type,
            "service_order_details": details,
            "details_count": len(details),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def check_chatter_feed(self, service_order_id: str, limit: int = 3) -> Dict[str, Any]:
        """Check Chatter feed for webhook notifications"""
        
        cmd = [
            "sf", "data", "query", 
            "-o", self.org_username,
            "--query", f"""
            SELECT Id, Body, CreatedDate 
            FROM FeedItem 
            WHERE ParentId = '{service_order_id}' 
            ORDER BY CreatedDate DESC 
            LIMIT {limit}
            """,
            "--json"
        ]
        
        sf_result = await self._execute_sf_command(cmd)
        feed_items = sf_result.get("result", {}).get("records", [])
        
        return {
            "service_order_id": service_order_id,
            "chatter_items": feed_items,
            "items_found": len(feed_items),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }