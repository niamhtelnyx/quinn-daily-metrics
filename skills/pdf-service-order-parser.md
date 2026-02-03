---
name: pdf-service-order-parser  
description: Parse Telnyx Service Order documents (PDF/text) to extract key contract information like start dates, commitment schedules, applicable services, and customer details. Returns structured JSON for Commitment Manager validation and Service Order operations. Use when processing Service Orders for billing validation, contract setup, or commitment tracking.
---

# PDF Service Order Parser

Extract key contract information from Telnyx Service Order documents and return structured JSON data for integration with Commitment Manager and Service Order operations.

## Overview

This skill processes Telnyx Service Order documents to extract critical contract information including customer details, commitment schedules, applicable services, and contract terms. It handles common OCR artifacts and returns standardized JSON for seamless integration with existing service-order-ops and commitment-manager-ops workflows.

## When to Use

- Processing new Service Orders for contract setup
- Validating commitment schedules against billing data  
- Extracting customer and service information for Salesforce
- Converting Service Order PDFs into structured data for automation
- Supporting service-order-ops and commitment-manager-ops workflows

## Installation

For PDF processing, install at least one PDF library:
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

## Workflow

### Step 1: Parse Service Order (PDF or Text)
```bash
# Direct PDF processing (recommended)
python3 scripts/parse_service_order.py service-order.pdf

# Or text files
python3 scripts/parse_service_order.py service-order.txt
```

The script automatically detects file type and handles PDF conversion using multiple fallback methods:
1. **pdftotext** (system command - most reliable)
2. **pdfplumber** (Python library - good for structured data)  
3. **PyMuPDF** (fast processing)
4. **pdfminer** (fallback option)

### Step 3: Validate Output
The parser returns JSON optimized for Commitment Manager integration.

**Ramped Commitment Example:**
```json
{
  "start_date": "2025-10-01",
  "duration": 36,
  "cycle": "monthly",
  "type": "ramped",
  "commits": [
    {"start_date": "2025-10-01", "duration": 6, "amount": 20000.0},
    {"start_date": "2026-04-01", "duration": 9, "amount": 35000.0},
    {"start_date": "2027-01-01", "duration": 21, "amount": 55000.0}
  ]
}
```

**Static Commitment Example:**
```json
{
  "start_date": "2025-10-01",
  "duration": 36,
  "cycle": "monthly",
  "type": "static",
  "commits": [
    {"start_date": "2025-10-01", "duration": 36, "amount": 50000.0}
  ]
}
```

**Metadata Section (both types):**
```json
{
  "_metadata": {
    "customer_info": {"company_name": "PatientSync"},
    "applicable_services": {
      "voice_us_can": true,
      "messaging_global": true,
      "call_control": true,
      "network": true
    }
  }
}
```

### Step 4: Integration with Existing Skills

**For Commitment Manager validation:**
- Use `mmc_commencement_date` and `ramped_commitment_schedule` 
- Cross-reference with commitment-manager-ops skill for API validation

**For Service Order operations:**
- Use customer info for Salesforce account lookup
- Use service flags for billing rule setup
- Integrate with service-order-ops skill workflows

## Commitment Type Detection

### Ramped Commitments
- **Detection**: Service Order contains "RAMPED COMMITMENT" table
- **Output**: Multiple entries in `commits` array with calculated durations
- **Example**: $20K → $35K → $55K over contract term

### Static Commitments  
- **Detection**: No ramped table, single amount mentioned in Section E
- **Output**: Single entry in `commits` array covering full contract duration
- **Example**: $50K monthly for entire 36-month term

## Key Extracted Fields

### Contract Information
- **MMC Commencement Date**: When commitments start billing
- **Initial Term**: Contract length (typically 36 months)  
- **Renewal Terms**: Auto-renewal periods (typically 12 months)

### Customer Details  
- **Company Name**: Customer organization
- **Address**: Billing/service address

### Service Configuration
- **Applicable Services**: Which services count toward commitment (Y/N flags)
  - Voice (US/CAN, Global)
  - Messaging (US/CAN, Global) 
  - Identity Services
  - Call Control Services
  - Network

### Financial Terms
- **Commitment Amounts**: Monthly commitment values (cleaned of OCR artifacts)
- **Duration Calculation**: How many months each commitment level lasts
- **Effective Dates**: When each commitment level starts

## OCR Handling

The parser handles common OCR artifacts from PDF conversion:
- **"+232 lines" artifacts**: Removed from dollar amounts
- **Spacing issues**: "$70, 000.00" → $70,000.00  
- **Mixed formatting**: Standardized date formats

## Resources

### scripts/
- **`parse_service_order.py`**: Main parsing engine with PDF/text support
- **`requirements.txt`**: PDF processing library dependencies
- **Usage**: `python3 scripts/parse_service_order.py <file>` (PDF or text)

### references/  
- **`field_patterns.md`**: Detailed patterns and variations for parsing
- **Load when**: Troubleshooting parsing issues or extending field extraction

### assets/
- **`schema.json`**: JSON schema for validating output structure
- **Use for**: Programmatic validation of parsed results

## Integration Examples

### With service-order-ops
```python
# After parsing Service Order
parsed_data = parse_service_order(text)
customer = parsed_data['customer_info']['company_name']
mmc_date = parsed_data['contract_terms']['mmc_commencement_date']

# Use with existing Service Order operations
# (integrate with Salesforce lookup, webhook validation, etc.)
```

### With commitment-manager-ops
```python
# Extract commitment schedule for API validation  
schedule = parsed_data['ramped_commitment_schedule']
for commitment in schedule:
    # Validate against Commitment Manager API
    effective_date = commitment['effective_date']
    amount = commitment['amount']
```

## Error Handling

- **Invalid dates**: Returns null for unparseable dates
- **OCR artifacts**: Cleaning patterns handle common errors
- **Missing sections**: Gracefully handles incomplete documents
- **Malformed currency**: Extracts numeric values where possible