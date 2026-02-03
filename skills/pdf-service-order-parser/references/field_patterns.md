# Service Order Field Patterns

This document describes the common patterns and variations found in Telnyx Service Order documents for accurate parsing.

## Date Patterns

### MMC Commencement Date (Enhanced v3)
- **Pattern 1**: `starting ([A-Za-z]+ \d{1,2}, \d{4}) \(the "MMC Commencement Date"\)`
- **Pattern 2**: `([A-Za-z]+ \d{1,2}, \d{4}) \(the "MMC Commencement Date"\)`
- **Pattern 3**: `MMC Commencement Date[^"]*"([A-Za-z]+ \d{1,2}, \d{4})"`
- **Pattern 4**: `E\..*?Commitment.*?([A-Za-z]+ \d{1,2}, \d{4})` (section E search)
- **Examples**: "October 1, 2025", "May 1, 2025"
- **Notes**: Real documents often have date in section E context

### Contract Dates
- **Effective Date**: Referenced as "date last signed" but actual date usually in signature block
- **Initial Term**: Calculated as 36 months from MMC Commencement Date
- **Common formats**: "October 1, 2025", "10/1/2025", "2025-10-01"

## Currency Patterns

### OCR Artifacts to Clean
- **"+232 lines"**: Common OCR error that appears in dollar amounts
- **"lines"**: Sometimes appears instead of digits
- **Spaces in numbers**: "$70, 000.00" instead of "$70,000.00"

### Cleaning Strategy
1. Remove "+232 lines" prefix
2. Remove "$" and "," characters
3. Extract numeric values with regex: `(\d+(?:\.\d+)?)`
4. Convert to float

## Ramped Commitment Schedule

### Table Structure
```
RAMPED COMMITMENT
Commit Start Date    Minimum Monthly Commitment
October 1, 2025     $5,000.00
November 1, 2025    $20,000.00
...
```

### Parsing Pattern
- **Row Pattern**: `(\w+ \d{1,2}, \d{4})\s+\$([0-9,+\w\s]+)`
- **Section Delimiter**: Starts with "RAMPED COMMITMENT", ends before next section

## Applicable Services

### Service Types and Patterns
| Service | Pattern | Key |
|---------|---------|-----|
| Numbers | `Numbers\s+([YN])` | numbers |
| Voice (US/CAN) | `Voice \(US/CAN\)\s+([YN])` | voice_us_can |
| Voice (Global) | `Voice \(global.*?\)\s+([YN])` | voice_global |
| Messaging (US/CAN) | `Messaging \(US/CAN\)\s+([YN])` | messaging_us_can |
| Messaging (Global) | `Messaging \(global.*?\)\s+([YN])` | messaging_global |
| Identity Services | `Identity Services\s+([YN])` | identity_services |
| Call Control | `Call Control Services\s+([YN])` | call_control |
| Network | `Network\s+([YN])` | network |

### Notes
- Services marked "Y" count toward Minimum Monthly Commitment
- Services marked "N" are charged separately
- Found in "Service Description" section

## Customer Information

### Company Name
- **Pattern**: `Company Name:\s*([^\n]+)`
- **Location**: Usually in "General Order Details" section

### Address  
- **Pattern**: `Address:\s*([^\n]+)`
- **Notes**: May have billing address separate from service address

## Contract Terms

### Initial Term (Enhanced v3)
- **36 months**: `thirty-six \(36\) months|36 months`
- **12 months**: `one \(1\) year|twelve \(12\) months`
- **24 months**: `twenty-four \(24\) months`
- **Dynamic**: `(\d+) months` - extracts any number
- **Default**: 36 months if no pattern matches

### Renewal Terms
- **Standard**: 12 months automatic renewal
- **Pattern**: `twelve \(12\) months|12 months.*renewal|one \(1\) year.*renewal`

### Termination Notice
- **Standard**: 30 days written notice required
- **Pattern**: `thirty \(30\) days.*notice`

## Common Variations

### Document Sections
- "General Order Details" → Customer info
- "Service Description" → Applicable services  
- "Additional Terms and Conditions" → Contract terms
- "RAMPED COMMITMENT" → Commitment schedule

### Text Quality Issues
- OCR artifacts in dollar amounts
- Inconsistent spacing and formatting
- Mixed case in section headers
- Signature block placeholders (e.g., "[counterpartySignerName_wQ2Nypo]")

## Integration Notes

### For Commitment Manager API
- Use `mmc_commencement_date` as contract start
- Use `ramped_commitment_schedule` for billing validation
- Filter `applicable_services` for commitment calculations
- Use `initial_term_months` for contract end date calculation

### For Service Order Operations  
- Customer info maps to Salesforce account lookup
- Service flags determine billing rules
- Commitment schedule drives invoice validation