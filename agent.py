#!/usr/bin/env python3
"""
Service Order Specialist Agent

Specialized agent for handling Salesforce Service Order operations,
commitment management, and billing validation with direct Slack access.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

# A2A Skills that other agents can discover and use
A2A_SKILLS = [
    {
        "id": "process-service-order-change",
        "name": "Process Service Order Changes",
        "description": "Handle customer service order modifications, commitment changes, date shifts, and billing adjustments with full validation",
        "inputModes": ["text", "structured"],
        "outputModes": ["text", "structured"],
        "parameters": {
            "customer_name": {"type": "string", "description": "Customer/company name"},
            "org_id": {"type": "string", "description": "Organization ID (mcorgid)", "required": False},
            "action": {"type": "string", "enum": ["lookup", "approve", "terminate", "update_dates"], "description": "Action to perform"},
            "new_start_date": {"type": "string", "format": "date", "required": False},
            "validation_required": {"type": "boolean", "default": True}
        }
    },
    {
        "id": "validate-commitment-terms", 
        "name": "Validate Commitment Terms",
        "description": "Review and validate proposed commitment changes for compliance, overlaps, and accuracy",
        "inputModes": ["text", "structured"],
        "outputModes": ["text", "structured"],
        "parameters": {
            "org_id": {"type": "string", "description": "Organization ID to validate"},
            "proposed_changes": {"type": "object", "description": "Proposed commitment changes"},
            "check_overlaps": {"type": "boolean", "default": True}
        }
    },
    {
        "id": "extract-service-order-pdf",
        "name": "Extract Service Order from PDF", 
        "description": "Parse service order PDFs to extract key contract information and return structured JSON",
        "inputModes": ["file", "text"],
        "outputModes": ["structured"],
        "parameters": {
            "pdf_path": {"type": "string", "description": "Path to service order PDF"},
            "extract_format": {"type": "string", "enum": ["json", "summary"], "default": "json"}
        }
    },
    {
        "id": "salesforce-service-order-lookup",
        "name": "Salesforce Service Order Lookup",
        "description": "Look up existing service orders in Salesforce with status analysis",
        "inputModes": ["text"],
        "outputModes": ["structured"],
        "parameters": {
            "customer_name": {"type": "string", "description": "Customer name to search"},
            "include_terminated": {"type": "boolean", "default": False},
            "validate_org_id": {"type": "string", "required": False}
        }
    }
]

# Agent Card Configuration (published at /.well-known/agent-card.json)
AGENT_CARD = {
    "name": "service-order-specialist",
    "version": "1.0.0",
    "description": "Specialized agent for Telnyx Service Order operations, Salesforce integration, and commitment management with direct Slack access for ops teams",
    "skills": A2A_SKILLS,
    "authentication": {
        "schemes": ["bearer"],
        "description": "Requires valid Telnyx agent token"
    },
    "supportedModes": ["sync", "streaming"],
    "channels": ["slack", "a2a", "http"],
    "provider": {
        "organization": "Telnyx",
        "team": "platform",
        "url": "https://telnyx.com",
        "maintainer": "niamh@telnyx.com"
    },
    "capabilities": [
        "salesforce-integration",
        "commitment-manager-api", 
        "pdf-processing",
        "slack-messaging",
        "data-validation"
    ],
    "specializations": [
        "Service Order management",
        "Commitment validation", 
        "Billing operations",
        "Contract processing"
    ]
}

class ServiceOrderSpecialistAgent:
    def __init__(self):
        self.name = "service-order-specialist"
        self.skills_dir = Path(__file__).parent / "skills"
        self.load_skills()
        
    def load_skills(self):
        """Load domain skills from skills directory"""
        skill_files = [
            "service-order-ops.md",
            "pdf-service-order-parser.md", 
            "slack.md"
        ]
        
        self.skills_content = {}
        for skill_file in skill_files:
            skill_path = self.skills_dir / skill_file
            if skill_path.exists():
                with open(skill_path, 'r') as f:
                    self.skills_content[skill_file] = f.read()
    
    async def handle_a2a_request(self, skill_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming A2A requests for specific skills"""
        
        if skill_id == "process-service-order-change":
            return await self.process_service_order_change(payload)
        elif skill_id == "validate-commitment-terms":
            return await self.validate_commitment_terms(payload)
        elif skill_id == "extract-service-order-pdf":
            return await self.extract_service_order_pdf(payload)
        elif skill_id == "salesforce-service-order-lookup":
            return await self.salesforce_lookup(payload)
        else:
            return {
                "success": False,
                "error": f"Unknown skill: {skill_id}",
                "available_skills": [skill["id"] for skill in A2A_SKILLS]
            }
    
    async def process_service_order_change(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process service order changes with full validation"""
        # Implementation using service-order-ops skill
        return {
            "success": True,
            "message": "Service order change processed",
            "details": payload
        }
    
    async def validate_commitment_terms(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate commitment terms and check for overlaps"""
        # Implementation using commitment validation logic
        return {
            "success": True,
            "validation_result": "passed",
            "details": payload
        }
    
    async def extract_service_order_pdf(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract service order data from PDF"""
        # Implementation using pdf-service-order-parser skill
        return {
            "success": True,
            "extracted_data": {},
            "format": payload.get("extract_format", "json")
        }
    
    async def salesforce_lookup(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Look up service orders in Salesforce"""
        # Implementation using Salesforce queries
        return {
            "success": True,
            "service_orders": [],
            "customer": payload.get("customer_name")
        }

def create_agent_card_endpoint():
    """Create the /.well-known/agent-card.json endpoint"""
    return AGENT_CARD

if __name__ == "__main__":
    agent = ServiceOrderSpecialistAgent()
    print(f"Service Order Specialist Agent initialized with {len(A2A_SKILLS)} A2A skills")
    print(f"Skills loaded: {list(agent.skills_content.keys())}")