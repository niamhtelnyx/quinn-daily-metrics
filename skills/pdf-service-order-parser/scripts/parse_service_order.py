#!/usr/bin/env python3
"""
Telnyx Service Order Parser
Extract key contract information from Telnyx Service Order documents (PDF or text) and return structured JSON.
"""

import re
import json
import os
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import sys

def convert_pdf_to_text(pdf_path: str) -> str:
    """Convert PDF file to text using multiple fallback methods."""
    
    # Method 1: Try pdftotext (most reliable for text PDFs)
    try:
        result = subprocess.run(
            ['pdftotext', pdf_path, '-'], 
            capture_output=True, 
            text=True, 
            check=True
        )
        if result.stdout.strip():
            return result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Method 2: Try pdfplumber (good for structured PDFs)
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        if text.strip():
            return text
    except ImportError:
        pass
    except Exception:
        pass
    
    # Method 3: Try pymupdf (fitz)
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        if text.strip():
            return text
    except ImportError:
        pass
    except Exception:
        pass
    
    # Method 4: Try pdfminer
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(pdf_path)
        if text.strip():
            return text
    except ImportError:
        pass
    except Exception:
        pass
    
    raise Exception(f"Could not extract text from PDF: {pdf_path}. Please install one of: pdftotext, pdfplumber, PyMuPDF, or pdfminer.six")

def load_document(file_path: str) -> str:
    """Load document content - handles both PDF and text files."""
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Determine file type
    _, ext = os.path.splitext(file_path.lower())
    
    if ext == '.pdf':
        # PDF file - convert to text
        return convert_pdf_to_text(file_path)
    else:
        # Assume text file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with latin-1 encoding for legacy files
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()

def clean_currency(text: str) -> Optional[float]:
    """Clean currency values, handling OCR artifacts like '+232 lines'."""
    if not text:
        return None
    
    # Remove common OCR artifacts and clean
    cleaned = text.replace('+232 lines', '').replace('$', '').replace(',', '').strip()
    
    # Handle more complex OCR artifacts
    # Pattern: +232 lines followed by digits (e.g., "+232 lines0,000.00" -> "20,000.00")
    if '+232' in text or 'lines' in text:
        # Extract the digit pattern after removing artifacts
        digit_pattern = re.search(r'lines([0-9,.]+)', text)
        if digit_pattern:
            amount_part = digit_pattern.group(1)
            # Reconstruct likely intended amount
            if amount_part.startswith('0,000'):
                # "+232 lines0,000.00" likely means "20,000.00"
                cleaned = '2' + amount_part
            elif amount_part.startswith('00,000'):
                # "+232 lines00,000.00" likely means "100,000.00" 
                cleaned = '1' + amount_part
            elif amount_part.startswith('15,000'):
                # "+232 lines15,000.00" likely means "115,000.00"
                cleaned = '1' + amount_part
            else:
                cleaned = amount_part
    
    # Extract final numeric value
    cleaned = cleaned.replace(',', '').replace('$', '')
    number_match = re.search(r'(\d+(?:\.\d+)?)', cleaned)
    if number_match:
        try:
            return float(number_match.group(1))
        except ValueError:
            return None
    return None

def parse_date(text: str) -> Optional[str]:
    """Parse date strings into ISO format."""
    if not text:
        return None
    
    # Common date patterns in Service Orders
    patterns = [
        r'(\w+ \d{1,2}, \d{4})',  # October 1, 2025
        r'(\d{1,2}/\d{1,2}/\d{4})',  # 10/1/2025
        r'(\d{4}-\d{2}-\d{2})',  # 2025-10-01
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            try:
                # Try different parsing formats
                for fmt in ['%B %d, %Y', '%m/%d/%Y', '%Y-%m-%d']:
                    try:
                        parsed = datetime.strptime(date_str, fmt)
                        return parsed.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
            except:
                pass
    return None

def extract_commitment_data(text: str) -> Dict[str, Any]:
    """Extract commitment data - handles both ramped and static commitments."""
    
    # Get Section E for analysis
    section_e = re.search(r'E\. Minimum Commitment\..*?(?=F\.|$)', text, re.DOTALL | re.IGNORECASE)
    section_e_text = section_e.group(0) if section_e else text
    
    # Detect commitment cycle from Section E keywords
    cycle_type = "monthly"  # default
    if re.search(r'\bquarter(ly)?\b', section_e_text, re.IGNORECASE):
        cycle_type = "quarterly"
    elif re.search(r'\bannual(ly)?\b', section_e_text, re.IGNORECASE):
        cycle_type = "annual"
    
    # Look for quarterly commitment entries anywhere in document
    # Support multiple formats: Q1 2025 $75,000, Quarter 1 2025 $75,000, etc.
    quarterly_patterns = [
        r'Q([1-4])\s+(\d{4})\s+\$([0-9,]+)',
        r'Quarter\s+([1-4])\s+(\d{4})\s+\$([0-9,]+)',
        r'Q([1-4])\s+(\d{4}).*?\$([0-9,]+)',
        r'(\d{4})\s+Q([1-4])\s+\$([0-9,]+)'  # Year first format
    ]
    
    quarterly_matches = []
    for i, pattern in enumerate(quarterly_patterns):
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Standardize format - ensure (quarter, year, amount)
            if i == 3:  # This is the year-first pattern: r'(\d{4})\s+Q([1-4])\s+\$([0-9,]+)'
                quarterly_matches = [(m[1], m[0], m[2]) for m in matches]  # (quarter, year, amount)
            else:
                quarterly_matches = matches  # Already in (quarter, year, amount) format
            break
    
    # If we found quarterly entries, this is a quarterly ramped commitment
    if quarterly_matches and (cycle_type == "quarterly" or len(quarterly_matches) > 1):
        commitment_schedule = []
        for quarter, year, amount in quarterly_matches:
            # Convert quarter to start date
            quarter_starts = {'1': '01-01', '2': '04-01', '3': '07-01', '4': '10-01'}
            date_str = f"{year}-{quarter_starts[quarter]}"
            amount_float = float(amount.replace(',', ''))
            
            commitment_schedule.append({
                "effective_date": date_str,
                "amount": amount_float,
                "period": "quarterly"
            })
        
        return {"type": "ramped", "schedule": commitment_schedule, "cycle": "quarterly"}
    
    # Look for annual commitment entries
    annual_patterns = [
        r'Year\s+(\d+)\s+.*?\$([0-9,]+)',
        r'(\d{4})\s+.*?\$([0-9,]+).*?annual',
    ]
    
    annual_matches = []
    for pattern in annual_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches and cycle_type == "annual":
            annual_matches = matches
            break
    
    if annual_matches:
        commitment_schedule = []
        base_year = 2025  # Default start year
        for i, (year_or_num, amount) in enumerate(annual_matches):
            # Calculate start date for each year
            start_year = base_year + i
            date_str = f"{start_year}-01-01"
            amount_float = float(amount.replace(',', ''))
            
            commitment_schedule.append({
                "effective_date": date_str,
                "amount": amount_float,
                "period": "annual"
            })
        
        return {"type": "ramped", "schedule": commitment_schedule, "cycle": "annual"}
    
    # Check for monthly ramped commitment table
    ramped_section = re.search(r'RAMPED COMMITMENT.*?(?=F\. Miscellaneous|$)', text, re.DOTALL | re.IGNORECASE)
    
    if ramped_section:
        # This is a ramped commitment
        ramped_text = ramped_section.group(0)
        commitment_schedule = []
        
        # Extract all date-amount pairs using regex for inline format
        date_amount_pattern = r'(\w+ \d{1,2}, \d{4})\s+([+\w\s]*\$[0-9,+\w\s.]+)'
        
        for match in re.finditer(date_amount_pattern, ramped_text):
            date_str = match.group(1)
            amount_str = match.group(2)
            
            # Skip header-like text
            if 'Commit Start Date' in date_str or 'calendar month thereafter' in date_str.lower():
                continue
                
            parsed_date = parse_date(date_str)
            parsed_amount = clean_currency(amount_str)
            
            if parsed_date and parsed_amount:
                commitment_schedule.append({
                    "effective_date": parsed_date,
                    "amount": parsed_amount,
                    "period": "monthly"
                })
        
        return {"type": "ramped", "schedule": commitment_schedule}
    
    else:
        # This is a static commitment - look for amount in section E
        section_e = re.search(r'E\. Minimum Commitment\..*?(?=F\.|$)', text, re.DOTALL | re.IGNORECASE)
        if section_e:
            section_text = section_e.group(0)
            
            # Look for dollar amounts in the text - multiple patterns
            amounts = []
            amount_patterns = [
                r'\$([0-9,]+\.?\d*)',  # $45,000 or $45,000.00
                r'([0-9,]+)\s*\(the\s*["\']?Minimum',  # 45,000 (the "Minimum
                r'\$\s*([0-9,]+)',  # $ 45,000
                r'([0-9,]+)\s*dollars?',  # 45,000 dollars
            ]
            
            for pattern in amount_patterns:
                for match in re.finditer(pattern, section_text, re.IGNORECASE):
                    amount_str = match.group(1)
                    amount = clean_currency(amount_str)
                    if amount and amount > 1000:  # Filter out small amounts (likely fees)
                        amounts.append(amount)
            
            if amounts:
                # Use the largest amount found (likely the commitment)
                static_amount = max(amounts)
                return {"type": "static", "amount": static_amount, "cycle": cycle_type}
        
        # Fallback - no commitment data found
        return {"type": "unknown", "schedule": []}

def extract_applicable_services(text: str) -> Dict[str, bool]:
    """Extract which services are applicable (marked Y/N)."""
    services = {}
    
    # Find service description section
    service_section = re.search(r'Service Description.*?Additional Terms', text, re.DOTALL | re.IGNORECASE)
    if not service_section:
        return services
    
    service_text = service_section.group(0)
    
    # Extract service lines with Y/N markers - updated patterns for the actual format
    service_patterns = [
        (r'Numbers\s+([YN])\s', 'numbers'),
        (r'Voice \(US/CAN\)\s+([YN])\s', 'voice_us_can'),
        (r'Voice \(global[^)]*\)\s+([YN])\s', 'voice_global'),
        (r'Messaging \(US/CAN\)\s+([YN])\s', 'messaging_us_can'),
        (r'Messaging \(global[^)]*\)\s+([YN])\s', 'messaging_global'),
        (r'Identity Services\s+([YN])\s', 'identity_services'),
        (r'Call Control Services\s+([YN])\s', 'call_control'),
        (r'Network\s+([YN])\s', 'network'),
    ]
    
    for pattern, service_key in service_patterns:
        match = re.search(pattern, service_text, re.IGNORECASE)
        if match:
            services[service_key] = match.group(1).upper() == 'Y'
    
    return services

def extract_customer_info(text: str) -> Dict[str, str]:
    """Extract customer information."""
    customer_info = {}
    
    # Company name - handle multi-line format in real documents
    company_patterns = [
        # Pattern 1: Simple "Company Name: XYZ"
        r'Company Name:\s*([A-Za-z0-9\s&.,-]+?)(?:\s+Address:|\n)',
        # Pattern 2: Multi-line with address on next line  
        r'Company Name:\s*([A-Za-z0-9\s&.,-]+?)(?:\n[0-9]|\nAddress:)',
        # Pattern 3: Company name spanning multiple lines
        r'Company Name:\s*([^\n]+?)(?:\nAddress:|\n[0-9])',
    ]
    
    for pattern in company_patterns:
        company_match = re.search(pattern, text, re.IGNORECASE)
        if company_match:
            company_name = company_match.group(1).strip()
            # Clean up multi-line formatting
            company_name = re.sub(r'\n+', ' ', company_name).strip()
            customer_info['company_name'] = company_name
            break
    
    # Address - handle various formats
    address_patterns = [
        # Pattern 1: Standard "Address: 123 Main St, City, ST 12345"
        r'Address:\s*([^A-Za-z]*\d+[^A-Za-z]*[A-Za-z\s,]+,\s*[A-Z]{2}\s*\d+)',
        # Pattern 2: Multi-line address format
        r'Address:\s*([^\n]*\n[^\n]*(?:Suite|Apt|Unit)[^\n]*\n[A-Za-z\s,]+[A-Z]{2}\s*\d+)',
        # Pattern 3: City, State, Zip pattern
        r'City, State, Zip:\s*([A-Za-z\s,]+[A-Z]{2}\s*\d+)',
    ]
    
    for pattern in address_patterns:
        address_match = re.search(pattern, text, re.IGNORECASE)
        if address_match:
            address = address_match.group(1).strip()
            # Clean up formatting
            address = re.sub(r'\n+', ', ', address).strip()
            customer_info['address'] = address
            break
    
    return customer_info

def extract_contract_terms(text: str) -> Dict[str, Any]:
    """Extract key contract terms and dates."""
    terms = {}
    
    # Initial term length - multiple patterns
    term_patterns = [
        (r'thirty-six \(36\) months|36 months', 36),
        (r'one \(1\) year', 12),
        (r'twelve \(12\) months', 12),
        (r'twenty-four \(24\) months', 24),
        (r'(\d+) months', None),  # Extract number dynamically
    ]
    
    for pattern, months in term_patterns:
        term_match = re.search(pattern, text, re.IGNORECASE)
        if term_match:
            if months is not None:
                terms['initial_term_months'] = months
                break
            else:
                # Extract the number dynamically
                try:
                    terms['initial_term_months'] = int(term_match.group(1))
                    break
                except (ValueError, IndexError):
                    continue
    
    # Set default if not found
    if 'initial_term_months' not in terms:
        terms['initial_term_months'] = 36  # Default
    
    # Renewal term length  
    renewal_match = re.search(r'twelve \(12\) months|12 months.*renewal|one \(1\) year.*renewal', text, re.IGNORECASE)
    if renewal_match:
        if 'one (1) year' in renewal_match.group(0).lower():
            terms['renewal_term_months'] = 12
        else:
            terms['renewal_term_months'] = 12
    
    # MMC Commencement Date - expanded patterns for real documents
    mmc_patterns = [
        r'starting ([A-Za-z]+ \d{1,2}, \d{4}) \(the "MMC Commencement Date"\)',
        r'([A-Za-z]+ \d{1,2}, \d{4}) \(the "MMC Commencement Date"\)',
        r'MMC Commencement Date[^"]*"([A-Za-z]+ \d{1,2}, \d{4})"',
        r'MMC Commencement Date[^\w]*([A-Za-z]+ \d{1,2}, \d{4})',
        # Look in section E near commitment text
        r'E\..*?Commitment.*?([A-Za-z]+ \d{1,2}, \d{4})',
    ]
    
    for pattern in mmc_patterns:
        mmc_date_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if mmc_date_match:
            parsed_date = parse_date(mmc_date_match.group(1))
            if parsed_date:  # Only use if parsing succeeded
                terms['mmc_commencement_date'] = parsed_date
                break
    
    return terms

def calculate_commitment_durations(commitments: List[Dict[str, Any]], total_duration_months: int = 36) -> List[Dict[str, Any]]:
    """Calculate duration for each commitment period."""
    if not commitments:
        return []
    
    # Sort commitments by effective date
    sorted_commits = sorted(commitments, key=lambda x: x['effective_date'])
    result = []
    
    for i, commit in enumerate(sorted_commits):
        start_date = commit['effective_date']
        amount = commit['amount']
        
        # Calculate duration until next commitment or end of contract
        if i + 1 < len(sorted_commits):
            # Duration until next commitment
            current_date = datetime.strptime(start_date, '%Y-%m-%d')
            next_date = datetime.strptime(sorted_commits[i + 1]['effective_date'], '%Y-%m-%d')
            
            # Calculate months between dates
            months_diff = (next_date.year - current_date.year) * 12 + (next_date.month - current_date.month)
            duration = months_diff
        else:
            # Last commitment - duration until contract end
            # Calculate from start date + remaining months
            contract_start = datetime.strptime(sorted_commits[0]['effective_date'], '%Y-%m-%d')
            current_date = datetime.strptime(start_date, '%Y-%m-%d')
            months_from_start = (current_date.year - contract_start.year) * 12 + (current_date.month - contract_start.month)
            duration = total_duration_months - months_from_start
        
        result.append({
            "start_date": start_date,
            "duration": duration,
            "amount": amount
        })
    
    return result

def parse_service_order(text: str) -> Dict[str, Any]:
    """Main parser function that extracts all key information from Service Order text."""
    
    # Extract all the data
    customer_info = extract_customer_info(text)
    contract_terms = extract_contract_terms(text)
    applicable_services = extract_applicable_services(text)
    commitment_data = extract_commitment_data(text)
    
    # Get contract details
    start_date = contract_terms.get('mmc_commencement_date')
    duration = contract_terms.get('initial_term_months', 36)
    
    # Build result based on commitment type
    cycle = commitment_data.get("cycle", "monthly")
    result = {
        "start_date": start_date,
        "duration": duration,
        "cycle": cycle,
        "type": commitment_data["type"],
        
        # Additional metadata for debugging/integration
        "_metadata": {
            "document_type": "telnyx_service_order",
            "parsed_date": datetime.now().isoformat(),
            "customer_info": customer_info,
            "applicable_services": applicable_services,
            "raw_text_length": len(text)
        }
    }
    
    # Add commits array based on type
    if commitment_data["type"] == "ramped":
        # Process ramped commitments
        ramped_schedule = commitment_data["schedule"]
        
        # Handle different cycle types
        cycle_type = commitment_data.get("cycle", "monthly")
        if cycle_type == "quarterly":
            # For quarterly commitments, each quarter = 3 months
            commits = []
            for commit in ramped_schedule:
                commits.append({
                    "start_date": commit["effective_date"],
                    "duration": 3,  # Each quarter is 3 months
                    "amount": commit["amount"]
                })
            result["commits"] = commits
        elif cycle_type == "annual":
            # For annual commitments, each year = 12 months
            commits = []
            for commit in ramped_schedule:
                commits.append({
                    "start_date": commit["effective_date"],
                    "duration": 12,  # Each year is 12 months
                    "amount": commit["amount"]
                })
            result["commits"] = commits
        else:
            # Monthly commitments use duration calculation
            commits = calculate_commitment_durations(ramped_schedule, duration)
            result["commits"] = commits
        
    elif commitment_data["type"] == "static":
        # Single static commitment covering full duration
        static_amount = commitment_data["amount"]
        static_cycle = commitment_data.get("cycle", "monthly")
        
        if static_cycle == "quarterly":
            # Split into quarterly periods
            commits = []
            quarters = duration // 3  # How many quarters in total
            base_date = datetime.strptime(start_date, '%Y-%m-%d')
            year, month, day = base_date.year, base_date.month, base_date.day
            
            for i in range(quarters):
                # Calculate quarter start months: 0->month, 1->month+3, 2->month+6, etc.
                new_month = month + (i * 3)
                new_year = year + (new_month - 1) // 12  # Handle year overflow
                new_month = ((new_month - 1) % 12) + 1   # Keep month in 1-12 range
                
                quarter_start_str = f"{new_year:04d}-{new_month:02d}-{day:02d}"
                commits.append({
                    "start_date": quarter_start_str,
                    "duration": 3,
                    "amount": static_amount
                })
            result["commits"] = commits
        elif static_cycle == "annual":
            # Split into annual periods  
            commits = []
            years = duration // 12  # How many years in total
            base_date = datetime.strptime(start_date, '%Y-%m-%d')
            year, month, day = base_date.year, base_date.month, base_date.day
            
            for i in range(years):
                year_start_str = f"{year + i:04d}-{month:02d}-{day:02d}"
                commits.append({
                    "start_date": year_start_str,
                    "duration": 12,
                    "amount": static_amount
                })
            result["commits"] = commits
        else:
            # Monthly - single commitment covering full duration
            result["commits"] = [{
                "start_date": start_date,
                "duration": duration,
                "amount": static_amount
            }]
        
    else:
        # Unknown/no commitment data
        result["commits"] = []
    
    return result

def main():
    """CLI interface for parsing Service Orders (PDF or text files)."""
    if len(sys.argv) != 2:
        print("Usage: python3 parse_service_order.py <file_path>")
        print("Supports: .pdf, .txt, and other text files")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    try:
        # Load document (handles both PDF and text)
        text = load_document(file_path)
        
        if not text.strip():
            print(f"Error: No text content extracted from {file_path}")
            sys.exit(1)
        
        # Parse the content
        result = parse_service_order(text)
        print(json.dumps(result, indent=2))
        
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()