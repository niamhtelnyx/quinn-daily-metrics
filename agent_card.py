#!/usr/bin/env python3
"""
Agent Card for Service Order Specialist
Complies with Telnyx A2A Protocol specification
"""

AGENT_CARD = {
    "name": "service-order-specialist",
    "description": "Specialized agent for Telnyx Service Order operations, Salesforce integration, and commitment management with full validation and safety checks",
    "url": "https://service-order-specialist.internal.telnyx.com/a2a",
    "provider": {
        "organization": "Telnyx",
        "team": "platform",
        "url": "https://telnyx.com",
        "maintainer": "niamh@telnyx.com"
    },
    "skills": [
        {
            "id": "process-service-order-change",
            "name": "Process Service Order Changes",
            "description": "Handle customer service order modifications, commitment changes, date shifts, and billing adjustments with full validation and safety checks",
            "inputModes": ["text", "structured"],
            "outputModes": ["text", "structured"],
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string", 
                        "description": "Customer/company name for lookup"
                    },
                    "org_id": {
                        "type": "string", 
                        "description": "Organization ID (mcorgid) for validation",
                        "required": False
                    },
                    "action": {
                        "type": "string",
                        "enum": ["lookup", "approve", "terminate", "update_dates", "analyze"],
                        "description": "Action to perform on the service order"
                    },
                    "new_start_date": {
                        "type": "string",
                        "format": "date",
                        "description": "New contract start date (YYYY-MM-DD)",
                        "required": False
                    },
                    "validation_required": {
                        "type": "boolean",
                        "default": True,
                        "description": "Whether to perform full safety validation"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for the change (for audit trail)",
                        "required": False
                    }
                },
                "required": ["customer_name", "action"]
            },
            "examples": [
                {
                    "input": {
                        "customer_name": "ACME Corp",
                        "org_id": "c4499f9b-6ffd-4b60-9224-5b70ae0b1b04",
                        "action": "update_dates", 
                        "new_start_date": "2026-02-01",
                        "reason": "Customer requested start date change"
                    },
                    "output": {
                        "success": True,
                        "service_orders_updated": 1,
                        "commitment_handler_id": "ch_abc123",
                        "webhook_status": "success"
                    }
                }
            ]
        },
        {
            "id": "validate-commitment-terms",
            "name": "Validate Commitment Terms", 
            "description": "Review and validate proposed commitment changes for compliance, overlaps, and accuracy against existing commitments",
            "inputModes": ["text", "structured"],
            "outputModes": ["structured"],
            "parameters": {
                "type": "object",
                "properties": {
                    "org_id": {
                        "type": "string",
                        "description": "Organization ID to validate against"
                    },
                    "proposed_changes": {
                        "type": "object",
                        "description": "Proposed commitment changes",
                        "properties": {
                            "start_date": {"type": "string", "format": "date"},
                            "end_date": {"type": "string", "format": "date"},
                            "monthly_commit": {"type": "number"},
                            "currency": {"type": "string", "default": "USD"}
                        }
                    },
                    "check_overlaps": {
                        "type": "boolean", 
                        "default": True,
                        "description": "Check for overlapping commitments"
                    }
                },
                "required": ["org_id", "proposed_changes"]
            }
        },
        {
            "id": "extract-service-order-pdf",
            "name": "Extract Service Order from PDF",
            "description": "Parse service order PDFs to extract key contract information (dates, amounts, customer details) and return structured JSON",
            "inputModes": ["file", "text"],
            "outputModes": ["structured"],
            "parameters": {
                "type": "object", 
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "Path to service order PDF file"
                    },
                    "pdf_url": {
                        "type": "string",
                        "description": "URL to service order PDF (alternative to path)"
                    },
                    "extract_format": {
                        "type": "string",
                        "enum": ["json", "summary", "validation_ready"],
                        "default": "json",
                        "description": "Output format - json for raw data, summary for human readable, validation_ready for immediate use"
                    },
                    "validate_against_salesforce": {
                        "type": "boolean",
                        "default": False,
                        "description": "Cross-validate extracted data against existing Salesforce records"
                    }
                },
                "anyOf": [
                    {"required": ["pdf_path"]},
                    {"required": ["pdf_url"]}
                ]
            }
        },
        {
            "id": "salesforce-service-order-lookup", 
            "name": "Salesforce Service Order Lookup",
            "description": "Look up existing service orders in Salesforce with comprehensive status analysis and commitment validation",
            "inputModes": ["text", "structured"],
            "outputModes": ["structured"],
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "description": "Customer name to search for"
                    },
                    "org_id": {
                        "type": "string", 
                        "description": "Organization ID for validation",
                        "required": False
                    },
                    "include_terminated": {
                        "type": "boolean",
                        "default": False,
                        "description": "Include terminated service orders in results"
                    },
                    "include_commitment_status": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include current commitment manager status"
                    },
                    "validate_org_id": {
                        "type": "boolean",
                        "default": True,
                        "description": "Validate provided org ID matches customer"
                    }
                },
                "required": ["customer_name"]
            }
        }
    ],
    "authentication": {
        "schemes": ["bearer"],
        "description": "Requires valid Telnyx agent authentication token"
    },
    "supportedModes": ["sync", "streaming", "push"],
    "channels": ["a2a", "slack", "http"],
    "capabilities": [
        "salesforce-integration",
        "commitment-manager-api",
        "pdf-processing", 
        "financial-validation",
        "audit-logging",
        "webhook-validation"
    ],
    "specializations": [
        "Service Order lifecycle management",
        "Financial commitment validation",
        "Billing operations safety",
        "Contract processing and parsing", 
        "Rev Ops workflow automation"
    ],
    "resourceRequirements": {
        "class": "standard",
        "cpu": "200m-1000m",
        "memory": "512Mi-1Gi",
        "maxLifetime": "indefinite",
        "autoTerminateIdle": "30m"
    },
    "governance": {
        "approvalRequired": {
            "revOpsApproval": True,
            "financialOperations": True
        },
        "auditLevel": "high",
        "securityScope": "financial-operations"
    },
    "version": "1.0.0",
    "createdAt": "2026-02-03T21:00:00Z",
    "updatedAt": "2026-02-03T21:00:00Z"
}