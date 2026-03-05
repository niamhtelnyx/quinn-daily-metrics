# PDF Service Order Parsing Guide

## Overview

This guide provides detailed instructions for parsing Telnyx Service Order documents (PDF/text) to extract key contract information for Commitment Manager integration.

## Installation Requirements

Install at least one PDF processing library:

```bash
# Recommended (lightweight and reliable)
pip install pdfplumber

# Alternative options
pip install PyMuPDF         # Fast processing
pip install pdfminer.six    # Fallback option

# System-level (most reliable for text PDFs)
brew install poppler        # macOS
# sudo apt-get install poppler-utils  # Ubuntu
```

## PDF Processing Methods

The parser uses multiple fallback methods for maximum reliability:

### 1. pdftotext (System Command - Most Reliable)
```bash
pdftotext -layout service-order.pdf output.txt
```
- Best for preserving table structure
- Handles complex layouts well
- System-level dependency

### 2. pdfplumber (Python Library)
```python
import pdfplumber
with pdfplumber.open(pdf_path) as pdf:
    text = ''
    for page in pdf.pages:
        text += page.extract_text()
```
- Good for structured data extraction
- Python-native, no system dependencies
- Excellent table handling

### 3. PyMuPDF (Fast Processing)
```python
import fitz  # PyMuPDF
doc = fitz.open(pdf_path)
text = ''
for page in doc:
    text += page.get_text()
```
- Very fast processing
- Good for simple text extraction
- Handles images and annotations

### 4. pdfminer (Fallback)
```python
from pdfminer.high_level import extract_text
text = extract_text(pdf_path)
```
- Reliable fallback option
- Good for difficult PDFs
- More basic feature set

## Commitment Type Detection

### Static Commitments
**Indicators:**
- No "RAMPED COMMITMENT" table present
- Single amount mentioned in Section E
- Consistent monthly amount throughout contract

**Example Text Patterns:**
```
Section E: Financial Terms
Monthly Commitment: $50,000.00
```

### Ramped Commitments  
**Indicators:**
- Contains "RAMPED COMMITMENT" table
- Multiple commitment amounts with dates
- Escalating commitment schedule

**Example Text Patterns:**
```
RAMPED COMMITMENT SCHEDULE:
Effective Date       Monthly Commitment
October 1, 2025      $20,000.00
April 1, 2026        $35,000.00  
January 1, 2027      $55,000.00
```

## Key Extraction Fields

### Contract Information
- **MMC Commencement Date**: When commitments start billing
- **Initial Term**: Contract length (typically 36 months)
- **Renewal Terms**: Auto-renewal periods

### Customer Details
- **Company Name**: Customer organization  
- **Address**: Billing/service address

### Service Configuration
- **Applicable Services**: Which services count toward commitment
  - Voice (US/CAN, Global)
  - Messaging (US/CAN, Global)
  - Identity Services
  - Call Control Services
  - Network

### Financial Terms
- **Commitment Amounts**: Monthly commitment values
- **Duration Calculation**: Months each commitment level lasts
- **Effective Dates**: When each commitment level starts

## OCR Artifact Handling

Common artifacts and cleanup patterns:

### Dollar Amount Cleanup
```python
# Remove OCR line artifacts
amount_text = amount_text.replace('+232 lines', '')

# Fix spacing issues  
amount_text = re.sub(r'\$(\d+),?\s*(\d+)\.(\d+)', r'$\1\2.\3', amount_text)

# Examples:
# "$70, 000.00" → "$70,000.00"
# "$50,000+232 lines.00" → "$50,000.00"
```

### Date Normalization
```python
# Handle various date formats
date_patterns = [
    r'(\w+)\s+(\d+),?\s+(\d{4})',  # "October 1, 2025"
    r'(\d{1,2})/(\d{1,2})/(\d{4})', # "10/1/2025"
    r'(\d{4})-(\d{2})-(\d{2})'      # "2025-10-01"
]
```

### Company Name Cleanup
```python
# Remove common OCR artifacts from company names
company_name = re.sub(r'\s+\d+\s+lines?', '', company_name)
company_name = re.sub(r'[^\w\s&,-]', '', company_name)
```

## Output JSON Format

### Static Commitment Example
```json
{
  "start_date": "2025-10-01",
  "duration": 36,
  "cycle": "monthly", 
  "type": "static",
  "commits": [
    {
      "start_date": "2025-10-01",
      "duration": 36,
      "amount": 50000.0
    }
  ],
  "_metadata": {
    "customer_info": {
      "company_name": "PatientSync"
    },
    "applicable_services": {
      "voice_us_can": true,
      "messaging_global": true,
      "call_control": true,
      "network": true
    },
    "contract_terms": {
      "mmc_commencement_date": "2025-10-01",
      "initial_term_months": 36,
      "renewal_term_months": 12
    }
  }
}
```

### Ramped Commitment Example
```json
{
  "start_date": "2025-10-01",
  "duration": 36,
  "cycle": "monthly",
  "type": "ramped", 
  "commits": [
    {
      "start_date": "2025-10-01", 
      "duration": 6,
      "amount": 20000.0
    },
    {
      "start_date": "2026-04-01",
      "duration": 9, 
      "amount": 35000.0
    },
    {
      "start_date": "2027-01-01",
      "duration": 21,
      "amount": 55000.0  
    }
  ],
  "_metadata": {
    "ramped_commitment_schedule": [
      {
        "effective_date": "2025-10-01",
        "monthly_commitment": 20000.0,
        "duration_months": 6
      },
      {
        "effective_date": "2026-04-01", 
        "monthly_commitment": 35000.0,
        "duration_months": 9
      },
      {
        "effective_date": "2027-01-01",
        "monthly_commitment": 55000.0,
        "duration_months": 21
      }
    ]
  }
}
```

## Duration Calculation

For ramped commitments, calculate duration for each level:

```python
def calculate_ramped_durations(schedule, total_months):
    """Calculate duration for each commitment level."""
    durations = []
    
    for i, commitment in enumerate(schedule):
        if i == len(schedule) - 1:
            # Last commitment gets remaining months
            previous_total = sum(durations)
            remaining = total_months - previous_total
            durations.append(remaining)
        else:
            # Calculate months until next commitment
            current_date = datetime.strptime(commitment['effective_date'], '%Y-%m-%d')
            next_date = datetime.strptime(schedule[i+1]['effective_date'], '%Y-%m-%d')
            
            # Calculate month difference
            months_diff = (next_date.year - current_date.year) * 12 + (next_date.month - current_date.month)
            durations.append(months_diff)
    
    return durations
```

## Integration with Service Order Operations

### Extracted Data Usage

```python
# After parsing Service Order PDF
parsed_data = parse_service_order(pdf_path)

# Customer lookup for validation
customer_name = parsed_data['_metadata']['customer_info']['company_name']
mmc_date = parsed_data['_metadata']['contract_terms']['mmc_commencement_date']

# Commitment schedule for Salesforce setup
if parsed_data['type'] == 'ramped':
    commitment_schedule = parsed_data['_metadata']['ramped_commitment_schedule']
    # Create Service_Order_Details__c records
else:
    # Single commitment for static SO
    commitment_amount = parsed_data['commits'][0]['amount']
```

### Service Order Field Mapping

```python
# Map parsed data to Salesforce fields
so_fields = {
    'Contract_Start_Date__c': parsed_data['start_date'],
    'Contract_Duration__c': parsed_data['duration'],
    'Min_Monthly_Commit__c': parsed_data['commits'][0]['amount'],  # Static only
}

# For ramped commitments, create detail records
if parsed_data['type'] == 'ramped':
    for commitment in parsed_data['commits']:
        detail_fields = {
            'Service_Order__c': so_id,
            'Commit_Start_Date__c': commitment['start_date'],
            'Commit_Amount__c': commitment['amount'],
            'Commit_Duration__c': commitment['duration']
        }
```

## Error Handling

### Common Issues and Solutions

1. **Invalid Dates**: Return null for unparseable dates
2. **OCR Artifacts**: Apply cleaning patterns before extraction
3. **Missing Sections**: Gracefully handle incomplete documents  
4. **Malformed Currency**: Extract numeric values where possible
5. **Multiple Tables**: Identify correct commitment table

### Validation Checks

```python
def validate_parsed_data(data):
    """Validate extracted data for completeness and consistency."""
    errors = []
    
    # Check required fields
    if not data.get('start_date'):
        errors.append("Missing start date")
    
    if not data.get('commits') or len(data['commits']) == 0:
        errors.append("No commitment amounts found")
    
    # Validate commitment amounts
    for commit in data.get('commits', []):
        if not commit.get('amount') or commit['amount'] <= 0:
            errors.append(f"Invalid commitment amount: {commit.get('amount')}")
    
    # Validate dates are parseable
    try:
        datetime.strptime(data['start_date'], '%Y-%m-%d')
    except:
        errors.append(f"Invalid start date format: {data['start_date']}")
    
    return errors
```

## Usage Examples

### Basic PDF Processing
```bash
python scripts/pdf_parser.py service-order.pdf
```

### With Custom Output
```bash
python scripts/pdf_parser.py service-order.pdf --output parsed_data.json
```

### Integration with SO Operations
```bash
# Parse PDF and validate customer
python scripts/pdf_parser.py service-order.pdf > parsed.json
customer=$(cat parsed.json | jq -r '._metadata.customer_info.company_name')
python scripts/service_order_operations.py lookup "$customer"
```