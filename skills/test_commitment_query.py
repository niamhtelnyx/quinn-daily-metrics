#!/usr/bin/env python3
"""Test the updated commitment database query skill directly"""

from commitment_database_query import handle_commitment_database_query_request
import json

# Test with Salesforce ID to see auto-resolution working
result = handle_commitment_database_query_request({
    'organization_id': 'a0TQk00000TcP5CMAV',
    'include_cancelled': True,
    'format': 'summary'
})

print("=== UPDATED SKILL TEST ===")
print(json.dumps(result, indent=2, default=str))
print("\nResolution info:", result.get('org_id_resolution', 'None'))
print("Final org ID used:", result.get('organization_id'))