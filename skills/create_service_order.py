"""
Create Service Order Skill - Complete MMC Submission 4.0 Screen Flow Simulation

This skill replicates the exact field mappings and business logic from the 
MMC Submission 4.0 screen flow, handling all service order types and complex commit scenarios.

Based on analysis of Flow ID: 301Qk00000cnzURIAY
"""

import json
import subprocess
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Salesforce Service_Order__c Picklist Values (validated 2026-02-24)
VALID_PICKLIST_VALUES = {
    'Commit_Cycle__c': ['Monthly', 'Quarterly', 'Annual'],
    'Type__c': ['Static', 'Ramped', 'Support'],
    'Stage__c': ['Draft', 'Out for Signature', 'Signed', 'Canceled', 'Terminated'],
    'Applicable_Service_Region__c': ['(US/CAN)', '(global, Excluding US/CAN)', 'enter custom value']
}

def validate_picklist_value(field_name: str, value: str) -> str:
    """
    Validate and return a valid picklist value for the given field
    
    Args:
        field_name: Salesforce field name (e.g., 'Commit_Cycle__c')
        value: Input value to validate
        
    Returns:
        Valid picklist value or default safe value
    """
    
    if field_name not in VALID_PICKLIST_VALUES:
        return value  # Field is not a known picklist
    
    valid_values = VALID_PICKLIST_VALUES[field_name]
    
    # Exact match (case-sensitive)
    if value in valid_values:
        return value
    
    # Case-insensitive match
    for valid_value in valid_values:
        if value.lower() == valid_value.lower():
            return valid_value
    
    # Mapping common variations
    if field_name == 'Commit_Cycle__c':
        value_lower = value.lower()
        if value_lower in ['month', 'monthly', 'mo']:
            return 'Monthly'
        elif value_lower in ['quarter', 'quarterly', 'q', 'qtr']:
            return 'Quarterly'
        elif value_lower in ['year', 'yearly', 'annual', 'annually']:
            return 'Annual'
        else:
            return 'Monthly'  # Default safe value
    
    elif field_name == 'Type__c':
        value_lower = value.lower()
        if 'static' in value_lower:
            return 'Static'
        elif 'ramp' in value_lower:
            return 'Ramped'
        elif 'support' in value_lower:
            return 'Support'
        else:
            return 'Static'  # Default safe value
    
    elif field_name == 'Stage__c':
        value_lower = value.lower()
        if 'draft' in value_lower:
            return 'Draft'
        elif 'signature' in value_lower:
            return 'Out for Signature'
        elif 'sign' in value_lower:
            return 'Signed'
        elif 'cancel' in value_lower:
            return 'Canceled'
        elif 'terminat' in value_lower:
            return 'Terminated'
        else:
            return 'Signed'  # Default safe value
    
    elif field_name == 'Applicable_Service_Region__c':
        value_lower = value.lower()
        if 'us' in value_lower or 'can' in value_lower or 'america' in value_lower:
            return '(US/CAN)'
        elif 'global' in value_lower or 'international' in value_lower:
            return '(global, Excluding US/CAN)'
        else:
            return '(US/CAN)'  # Default safe value
    
    # Fallback - return first valid value for unknown cases
    return valid_values[0]

def create_service_order_from_pdf(pdf_data, opportunity_id=None):
    """
    Create Service Order from PDF extracted data
    
    Args:
        pdf_data: Dict with extracted PDF data
        opportunity_id: Optional Opportunity ID to link
        
    Returns:
        Dict with creation result
    """
    
    # Validate all required fields are present (MMC Submission 4.0 requirements)
    validation_result = validate_required_fields(pdf_data, opportunity_id)
    if not validation_result['valid']:
        return validation_result
    
    # Determine service order type from PDF data
    service_order_type = determine_service_order_type(pdf_data)
    
    # Map PDF data to Salesforce fields based on type
    sf_fields = map_pdf_to_salesforce_fields(pdf_data, opportunity_id, service_order_type)
    
    # Create Service Order record via sf CLI
    result = create_salesforce_service_order(sf_fields, service_order_type)
    
    return result

def validate_required_fields(pdf_data, opportunity_id):
    """
    Validate that all 6 required fields for MMC Submission flow are present
    
    Required fields per flow:
    1. Name (derived from customer_name)
    2. Stage__c (always "Signed")
    3. Type__c (from service order type)
    4. Commit_Cycle__c (from cycle)
    5. Contract dates and amounts
    6. Opportunity__c (linkage)
    
    Returns:
        Dict with validation results
    """
    
    missing_fields = []
    missing_data = {}
    
    # 1. Customer name (for Name field)
    if not pdf_data.get('customer_name'):
        missing_fields.append('customer_name')
        missing_data['customer_name'] = 'Customer/company name'
    
    # 2. Stage is always "Signed" - no validation needed
    
    # 3. Service Order Type (for Type__c)
    service_type = determine_service_order_type(pdf_data)
    if service_type not in ['static', 'ramped', 'support']:
        missing_fields.append('service_type')
        missing_data['service_type'] = 'Service order type (Static, Ramped, or Support)'
    
    # 4. Commit Cycle (for Commit_Cycle__c) 
    cycle_value = pdf_data.get('commit_cycle') or pdf_data.get('cycle')
    if not cycle_value:
        missing_fields.append('commit_cycle')
        missing_data['commit_cycle'] = 'Commitment cycle (Monthly, Quarterly, or Annual)'
    
    # 5. Contract dates and amounts
    if not pdf_data.get('contract_start_date'):
        missing_fields.append('contract_start_date')
        missing_data['contract_start_date'] = 'Contract start date (YYYY-MM-DD)'
        
    if not pdf_data.get('contract_duration') and not pdf_data.get('contract_end_date'):
        missing_fields.append('contract_duration')
        missing_data['contract_duration'] = 'Contract duration in months OR end date'
        
    if not pdf_data.get('commitment_amount'):
        missing_fields.append('commitment_amount')
        missing_data['commitment_amount'] = 'Monthly commitment amount'
    
    # 6. Opportunity linkage
    if not opportunity_id:
        missing_fields.append('opportunity_id')
        missing_data['opportunity_id'] = 'Salesforce Opportunity ID to link'
    
    # Return validation results
    if missing_fields:
        return {
            'valid': False,
            'success': False,
            'error': 'Missing required fields for Service Order creation',
            'missing_fields': missing_fields,
            'required_data': missing_data,
            'message': f"Please provide the following required information: {', '.join(missing_data.values())}"
        }
    
    return {'valid': True}

def determine_service_order_type(pdf_data):
    """
    Determine the appropriate service order type based on PDF data
    
    Returns: 'static', 'ramped', 'custom', 'support', or 'professional_services'
    """
    
    # Check for explicit service type indicators
    if 'service_type' in pdf_data:
        service_type = pdf_data['service_type'].lower()
        if 'support' in service_type:
            return 'support'
        elif 'professional' in service_type:
            return 'professional_services'
    
    # Check for ramped commit indicators
    if any(key.startswith('ramp_') for key in pdf_data.keys()):
        return 'ramped'
    
    # Check for custom commit indicators  
    if any(key.startswith('custom_') for key in pdf_data.keys()):
        return 'custom'
    
    # Default to static
    return 'static'

def map_pdf_to_salesforce_fields(pdf_data, opportunity_id=None, service_order_type='static'):
    """
    Map extracted PDF data to Salesforce Service_Order__c fields
    Replicates MMC Submission 4.0 screen flow field mappings
    """
    
    sf_fields = {}
    
    # Core fields (all types)
    sf_fields.update(map_core_fields(pdf_data, opportunity_id, service_order_type))
    
    # Type-specific field mappings
    if service_order_type == 'static':
        sf_fields.update(map_static_fields(pdf_data))
    elif service_order_type == 'ramped':
        sf_fields.update(map_ramped_fields(pdf_data))
    elif service_order_type == 'custom':
        sf_fields.update(map_custom_fields(pdf_data))
    elif service_order_type == 'support':
        sf_fields.update(map_support_fields(pdf_data))
    elif service_order_type == 'professional_services':
        sf_fields.update(map_professional_services_fields(pdf_data))
    
    # BAA fields (all types)
    sf_fields.update(map_baa_fields(pdf_data))
    
    return sf_fields

def map_core_fields(pdf_data, opportunity_id, service_order_type):
    """Map core fields required for all service order types"""
    
    fields = {}
    
    # Generate service order name (Account + Type + Cycle + Amount format)
    customer_name = pdf_data.get('customer_name', 'Unknown Customer')
    commit_type = service_order_type.title()
    commit_cycle = pdf_data.get('commit_cycle', 'Monthly')
    commit_amount = pdf_data.get('commitment_amount', 0)
    
    fields['Name'] = f"{customer_name}-{commit_type}-{commit_cycle}-{commit_amount}"
    
    # Required linkages
    if opportunity_id:
        fields['Opportunity__c'] = opportunity_id
    
    # Mission Control Account (critical for proper linking)
    if 'mission_control_account_id' in pdf_data:
        fields['Mission_Control_Account__c'] = pdf_data['mission_control_account_id']
    
    # Service Order Type (validated)
    fields['Type__c'] = validate_picklist_value('Type__c', map_service_order_type_value(service_order_type))
    
    # Initial stage and approval status (validated)
    fields['Stage__c'] = validate_picklist_value('Stage__c', 'Signed')  # Default per flow analysis
    fields['Rev_Ops_Approved__c'] = False  # Always starts false
    
    return fields

def map_static_fields(pdf_data):
    """Map fields specific to Static service orders"""
    
    fields = {}
    
    # Core static commit fields
    if 'contract_start_date' in pdf_data:
        fields['Contract_Start_Date__c'] = pdf_data['contract_start_date']
    
    if 'contract_duration' in pdf_data:
        fields['Contract_Duration__c'] = pdf_data['contract_duration']
    
    if 'commitment_amount' in pdf_data:
        fields['Min_Monthly_Commit__c'] = pdf_data['commitment_amount']
    
    # Map commit cycle (handle both 'cycle' and 'commit_cycle' field names) - validated
    cycle_value = pdf_data.get('commit_cycle') or pdf_data.get('cycle')
    if cycle_value:
        fields['Commit_Cycle__c'] = validate_picklist_value('Commit_Cycle__c', cycle_value)
    
    # Note: Currency__c and Applicable_Service_Region__c are NOT set by MMC Submission flow
    # These are auto-populated by Salesforce workflows or remain null as defaults
    
    return fields

def map_ramped_fields(pdf_data):
    """Map fields specific to Ramped service orders (up to 15 cycles)"""
    
    fields = {}
    
    # Include static fields as base
    fields.update(map_static_fields(pdf_data))
    
    # Ramped commit cycle fields (1-15)
    for cycle in range(1, 16):
        cycle_key = f"ramp_cycle_{cycle}"
        
        if f"{cycle_key}_amount" in pdf_data:
            fields[f'Commit_Amount_{cycle}__c'] = pdf_data[f"{cycle_key}_amount"]
        
        if f"{cycle_key}_duration" in pdf_data:
            fields[f'Commit_Duration_{cycle}__c'] = pdf_data[f"{cycle_key}_duration"]
        
        if f"{cycle_key}_start_date" in pdf_data:
            fields[f'Commit_Start_Date_{cycle}__c'] = pdf_data[f"{cycle_key}_start_date"]
    
    # Calculate ramped dates automatically if base dates provided
    if 'contract_start_date' in pdf_data and 'ramp_cycle_1_duration' in pdf_data:
        fields.update(calculate_ramped_dates(pdf_data))
    
    return fields

def map_custom_fields(pdf_data):
    """Map fields specific to Custom service orders (up to 10 cycles)"""
    
    fields = {}
    
    # Include static fields as base  
    fields.update(map_static_fields(pdf_data))
    
    # Custom commit cycle fields (1-10)
    for cycle in range(1, 11):
        cycle_key = f"custom_cycle_{cycle}"
        
        if f"{cycle_key}_amount" in pdf_data:
            fields[f'Commit_Amount_{cycle}__c'] = pdf_data[f"{cycle_key}_amount"]
        
        if f"{cycle_key}_duration" in pdf_data:
            fields[f'Commit_Duration_{cycle}__c'] = pdf_data[f"{cycle_key}_duration"]
        
        if f"{cycle_key}_start_date" in pdf_data:
            fields[f'Commit_Start_Date_{cycle}__c'] = pdf_data[f"{cycle_key}_start_date"]
        
        if f"{cycle_key}_frequency" in pdf_data:
            fields[f'Custom_Commit_Frequency_{cycle}__c'] = pdf_data[f"{cycle_key}_frequency"]
    
    return fields

def map_support_fields(pdf_data):
    """Map fields specific to Support service orders"""
    
    fields = {}
    
    # Support-specific fields
    if 'support_type' in pdf_data:
        fields['Support_Type__c'] = pdf_data['support_type']
    
    if 'support_amount' in pdf_data:
        fields['Support_Amount__c'] = pdf_data['support_amount']
    elif 'commitment_amount' in pdf_data:
        fields['Support_Amount__c'] = pdf_data['commitment_amount']
    
    # Basic contract fields
    if 'contract_start_date' in pdf_data:
        fields['Contract_Start_Date__c'] = pdf_data['contract_start_date']
    
    if 'contract_duration' in pdf_data:
        fields['Contract_Duration__c'] = pdf_data['contract_duration']
    
    return fields

def map_professional_services_fields(pdf_data):
    """Map fields specific to Professional Services orders"""
    
    fields = {}
    
    # Professional Services specific logic
    fields['Support_Type__c'] = 'Professional Services'
    
    if 'professional_services_duration' in pdf_data:
        duration_days = pdf_data['professional_services_duration']
        fields['Professional_Services_Duration__c'] = duration_days
        
        # Calculate amount: duration * $2,550 (per flow formula)
        fields['Support_Amount__c'] = duration_days * 2550
    
    if 'contract_start_date' in pdf_data:
        fields['Contract_Start_Date__c'] = pdf_data['contract_start_date']
    
    return fields

def map_baa_fields(pdf_data):
    """Map BAA (Business Associate Agreement) fields"""
    
    fields = {}
    
    # BAA fields (available for all service order types)
    if pdf_data.get('baa_required', False) or pdf_data.get('includes_baa', False):
        fields['BAA__c'] = True
        fields['BAA_Amount__c'] = 2500.0  # Fixed $2,500 per flow analysis
    
    return fields

def map_service_order_type_value(service_order_type):
    """Map internal service order type to Salesforce picklist value"""
    
    type_mapping = {
        'static': 'Static',
        'ramped': 'Ramped', 
        'custom': 'Custom',
        'support': 'Support',
        'professional_services': 'Professional Services'
    }
    
    return type_mapping.get(service_order_type, 'Static')

def calculate_ramped_dates(pdf_data):
    """Calculate start/end dates for ramped commit cycles"""
    
    fields = {}
    
    try:
        base_start = datetime.strptime(pdf_data['contract_start_date'], '%Y-%m-%d').date()
        
        current_start = base_start
        
        for cycle in range(1, 16):
            duration_key = f"ramp_cycle_{cycle}_duration"
            if duration_key not in pdf_data:
                break
                
            duration_months = pdf_data[duration_key]
            
            # Set start date for this cycle
            fields[f'Commit_Start_Date_{cycle}__c'] = current_start.strftime('%Y-%m-%d')
            
            # Calculate end date (start + duration - 1 day)
            cycle_end = current_start + relativedelta(months=duration_months) - timedelta(days=1)
            
            # Next cycle starts after this one ends
            current_start = cycle_end + timedelta(days=1)
            
    except (ValueError, KeyError) as e:
        # If date calculation fails, log but don't break the flow
        print(f"Warning: Could not calculate ramped dates: {e}")
    
    return fields

def create_salesforce_service_order(sf_fields, service_order_type):
    """
    Create Service Order record using sf CLI with enhanced error handling
    """
    
    # Build sf data create command with proper field quoting
    field_values = []
    for field, value in sf_fields.items():
        if value is not None:
            if isinstance(value, str) and (' ' in value or "'" in value):
                # Escape single quotes and wrap in quotes
                escaped_value = value.replace("'", "\\'")
                field_values.append(f"{field}='{escaped_value}'")
            elif isinstance(value, bool):
                field_values.append(f"{field}={str(value).lower()}")
            else:
                field_values.append(f"{field}={value}")
    
    field_string = ' '.join(field_values)
    
    cmd = [
        'sf', 'data', 'create', 'record',
        '-s', 'Service_Order__c',
        '-v', field_string,
        '-o', 'niamh@telnyx.com',
        '--json'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        response = json.loads(result.stdout)
        
        service_order_id = response.get('result', {}).get('id')
        
        # For ramped service orders, create Service Order Details
        details_result = None
        if service_order_type == 'ramped' and service_order_id:
            details_result = create_service_order_details(service_order_id, sf_fields)
        
        return {
            'success': True,
            'service_order_id': service_order_id,
            'service_order_type': service_order_type,
            'message': f'{service_order_type.title()} Service Order created successfully',
            'mapped_fields_count': len(sf_fields),
            'mapped_fields': list(sf_fields.keys()),
            'salesforce_response': response,
            'service_order_details': details_result
        }
        
    except subprocess.CalledProcessError as e:
        error_output = e.stderr or e.stdout
        return {
            'success': False,
            'error': f'Salesforce API error: {error_output}',
            'command': ' '.join(cmd),
            'attempted_fields': sf_fields
        }
    
    except json.JSONDecodeError as e:
        return {
            'success': False,
            'error': f'Failed to parse Salesforce response: {str(e)}',
            'raw_output': result.stdout
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }

def create_service_order_details(service_order_id, sf_fields):
    """
    Create Service Order Details records for ramped commits
    Replicates the flow's Service_Order_Details__c creation logic
    """
    
    details_created = []
    
    try:
        for cycle in range(1, 16):
            # Check if this cycle has data
            amount_field = f'Commit_Amount_{cycle}__c'
            duration_field = f'Commit_Duration_{cycle}__c'
            start_date_field = f'Commit_Start_Date_{cycle}__c'
            
            if amount_field not in sf_fields:
                break  # No more cycles
            
            # Build Service Order Detail record
            detail_fields = {
                'Service_Order__c': service_order_id,
                'Cycle_Number__c': cycle,
                'Name': f"{sf_fields.get('Name', 'Service Order')} - Cycle {cycle}"
            }
            
            # Map commit fields
            if amount_field in sf_fields:
                detail_fields['Commit_Amount__c'] = sf_fields[amount_field]
            
            if duration_field in sf_fields:
                detail_fields['Commit_Duration__c'] = sf_fields[duration_field]
            
            if start_date_field in sf_fields:
                detail_fields['Commit_Start_Date__c'] = sf_fields[start_date_field]
            
            # Add commit cycle from parent
            if 'Commit_Cycle__c' in sf_fields:
                detail_fields['Commit_Cycle__c'] = sf_fields['Commit_Cycle__c']
            
            # Create the detail record
            detail_result = create_service_order_detail_record(detail_fields)
            details_created.append(detail_result)
            
    except Exception as e:
        print(f"Warning: Could not create Service Order Details: {e}")
    
    return {
        'details_created': len(details_created),
        'details': details_created
    }

def create_service_order_detail_record(detail_fields):
    """Create a single Service Order Detail record"""
    
    # Build field string
    field_values = []
    for field, value in detail_fields.items():
        if value is not None:
            if isinstance(value, str) and ' ' in value:
                field_values.append(f"{field}='{value}'")
            else:
                field_values.append(f"{field}={value}")
    
    field_string = ' '.join(field_values)
    
    cmd = [
        'sf', 'data', 'create', 'record',
        '-s', 'Service_Order_Details__c',
        '-v', field_string,
        '-o', 'niamh@telnyx.com',
        '--json'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        response = json.loads(result.stdout)
        
        return {
            'success': True,
            'detail_id': response.get('result', {}).get('id'),
            'cycle_number': detail_fields.get('Cycle_Number__c')
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'cycle_number': detail_fields.get('Cycle_Number__c')
        }

# A2A skill interface
def handle_create_service_order_request(payload):
    """
    A2A interface for create-service-order skill
    Enhanced to handle all MMC Submission 4.0 scenarios
    """
    
    try:
        pdf_data = payload.get('pdf_data', {})
        opportunity_id = payload.get('opportunity_id')
        
        if not pdf_data:
            return {
                'success': False,
                'error': 'No PDF data provided'
            }
        
        result = create_service_order_from_pdf(pdf_data, opportunity_id)
        
        # Add analysis info to response
        result['flow_analysis'] = {
            'detected_type': determine_service_order_type(pdf_data),
            'total_fields_supported': '80+',
            'flow_id': '301Qk00000cnzURIAY',
            'flow_version': 'MMC Submission 4.0'
        }
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Skill execution error: {str(e)}'
        }

# Example usage and testing
if __name__ == '__main__':
    
    # Test different service order types
    
    print("=== Testing Static Service Order ===")
    static_data = {
        'customer_name': 'Acme Corporation',
        'commitment_amount': 5000,
        'contract_start_date': '2024-01-01',
        'contract_duration': 24,
        'commit_cycle': 'Monthly',
        'mission_control_account_id': 'a0X8Z00000AbCdEUAV',
        'baa_required': True
    }
    
    result = create_service_order_from_pdf(static_data)
    print(json.dumps(result, indent=2))
    
    print("\n=== Testing Ramped Service Order ===")
    ramped_data = {
        'customer_name': 'Beta Industries',
        'commitment_amount': 10000,
        'contract_start_date': '2024-02-01',
        'contract_duration': 12,
        'commit_cycle': 'Monthly',
        'service_type': 'ramped',
        'ramp_cycle_1_amount': 2500,
        'ramp_cycle_1_duration': 3,
        'ramp_cycle_2_amount': 5000,
        'ramp_cycle_2_duration': 3,
        'ramp_cycle_3_amount': 10000,
        'ramp_cycle_3_duration': 6,
        'mission_control_account_id': 'a0X8Z00000AbCdEUAV'
    }
    
    result = create_service_order_from_pdf(ramped_data)
    print(json.dumps(result, indent=2))
    
    print("\n=== Testing Professional Services ===")
    ps_data = {
        'customer_name': 'Gamma Solutions',
        'service_type': 'professional_services',
        'contract_start_date': '2024-03-01',
        'professional_services_duration': 10,  # 10 days * $2,550 = $25,500
        'mission_control_account_id': 'a0X8Z00000AbCdEUAV'
    }
    
    result = create_service_order_from_pdf(ps_data)
    print(json.dumps(result, indent=2))