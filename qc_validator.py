#!/usr/bin/env python3
"""
Quality Control Validator for AE Call Analysis System
Filters out garbage posts before they reach #sales-calls

QUALITY GATES:
❌ Block if prospect_name is "Unknown Prospect" 
❌ Block if AE name is "Unknown AE"
❌ Block if AI summary contains JSON error messages
❌ Block if content is None/empty
❌ Block if analysis is mostly empty arrays
❌ Block if call title looks malformed
✅ Only post high-quality, actionable call intelligence
"""

import json
import re
import logging
from typing import Dict, List, Tuple, Any
from datetime import datetime

class QualityGate:
    """Individual quality gate with validation logic"""
    
    def __init__(self, name: str, description: str, blocking: bool = True):
        self.name = name
        self.description = description
        self.blocking = blocking
    
    def validate(self, call_data: Dict, analysis: Dict) -> Tuple[bool, str]:
        """Override in subclasses. Returns (passed, message)"""
        return True, "Base gate passed"

class ProspectNameGate(QualityGate):
    """Block posts with Unknown Prospect"""
    
    def __init__(self):
        super().__init__("prospect_name", "Prospect name must be valid", True)
    
    def validate(self, call_data: Dict, analysis: Dict) -> Tuple[bool, str]:
        prospect_name = call_data.get('prospect_name', '').strip()
        
        invalid_names = [
            'unknown prospect',
            'unknown',
            '',
            'prospect',
            'customer',
            'client',
            'n/a',
            'na',
            'telnyx'
        ]
        
        if prospect_name.lower() in invalid_names:
            return False, f"Invalid prospect name: '{prospect_name}'"
        
        # Check for placeholder patterns
        if re.match(r'^(prospect|customer|client)\s*\d*$', prospect_name.lower()):
            return False, f"Placeholder prospect name: '{prospect_name}'"
        
        # Must be at least 2 characters
        if len(prospect_name) < 2:
            return False, f"Prospect name too short: '{prospect_name}'"
        
        return True, "Prospect name is valid"

class AeNameGate(QualityGate):
    """Block posts with Unknown AE"""
    
    def __init__(self):
        super().__init__("ae_name", "AE name must be valid", True)
        
        # Known Telnyx AEs for validation
        self.valid_aes = [
            'niamh collins', 'ryan simkins', 'tyron pretorius',
            'kai luo', 'rob messier', 'danilo', 'gulsah', 'luke', 
            'khalil', 'jagoda', 'conor', 'mario', 'abdullah', 
            'edmond', 'brian', 'decliner slides'
        ]
    
    def validate(self, call_data: Dict, analysis: Dict) -> Tuple[bool, str]:
        ae_name = call_data.get('ae_name', '').strip()
        
        invalid_names = [
            'unknown ae',
            'unknown',
            '',
            'ae',
            'sales',
            'rep',
            'n/a',
            'na'
        ]
        
        if ae_name.lower() in invalid_names:
            return False, f"Invalid AE name: '{ae_name}'"
        
        # Check against known AEs (soft validation)
        if not any(valid_ae in ae_name.lower() for valid_ae in self.valid_aes):
            # Not blocking, but warn
            return True, f"AE name not in known list but allowed: '{ae_name}'"
        
        return True, "AE name is valid"

class ContentQualityGate(QualityGate):
    """Validate content quality and length"""
    
    def __init__(self):
        super().__init__("content_quality", "Content must be substantial", True)
    
    def validate(self, call_data: Dict, analysis: Dict) -> Tuple[bool, str]:
        content = call_data.get('content', '')
        
        if not content or content.strip() == '':
            return False, "Content is empty"
        
        # Minimum content length
        if len(content.strip()) < 100:
            return False, f"Content too short: {len(content)} characters"
        
        # Check for error patterns
        error_patterns = [
            r'error\s*:\s*\w+',
            r'exception\s*:\s*\w+',
            r'failed\s+to\s+\w+',
            r'null\s+reference',
            r'undefined\s+\w+',
            r'invalid\s+\w+',
            r'permission\s+denied',
            r'access\s+denied',
            r'not\s+found',
            r'404\s+error',
            r'500\s+error'
        ]
        
        content_lower = content.lower()
        for pattern in error_patterns:
            if re.search(pattern, content_lower):
                return False, f"Content contains error pattern: {pattern}"
        
        # Check for meaningful content (not just boilerplate)
        meaningful_indicators = [
            'discuss', 'meeting', 'call', 'conversation', 'talked', 
            'mentioned', 'said', 'explained', 'asked', 'question',
            'project', 'business', 'solution', 'requirement', 'need'
        ]
        
        if not any(indicator in content_lower for indicator in meaningful_indicators):
            return False, "Content appears to lack meaningful discussion"
        
        return True, "Content quality is acceptable"

class AnalysisQualityGate(QualityGate):
    """Validate AI analysis quality"""
    
    def __init__(self):
        super().__init__("analysis_quality", "AI analysis must be substantial", True)
    
    def validate(self, call_data: Dict, analysis: Dict) -> Tuple[bool, str]:
        if not analysis:
            return False, "Analysis is empty"
        
        # Check for error in analysis
        if 'error' in analysis:
            return False, f"Analysis contains error: {analysis.get('error')}"
        
        # Check summary quality
        summary = analysis.get('summary', '')
        if not summary or len(summary.strip()) < 10:
            return False, "Summary is too short or empty"
        
        # Check for JSON error messages in summary
        json_error_patterns = [
            r'\{.*"error".*\}',
            r'json\s*parse\s*error',
            r'invalid\s*json',
            r'syntax\s*error',
            r'unexpected\s*token',
            r'malformed\s*json'
        ]
        
        summary_lower = summary.lower()
        for pattern in json_error_patterns:
            if re.search(pattern, summary_lower):
                return False, f"Summary contains JSON error: {pattern}"
        
        # Check if analysis has meaningful content
        key_fields = ['key_points', 'next_steps', 'pain_points']
        meaningful_content = 0
        
        for field in key_fields:
            field_data = analysis.get(field, [])
            if isinstance(field_data, list) and len(field_data) > 0:
                # Check if not just empty strings
                if any(str(item).strip() for item in field_data):
                    meaningful_content += 1
        
        if meaningful_content == 0:
            return False, "Analysis lacks meaningful insights (empty arrays)"
        
        return True, "Analysis quality is acceptable"

class TitleQualityGate(QualityGate):
    """Validate call title quality"""
    
    def __init__(self):
        super().__init__("title_quality", "Call title must be meaningful", True)
    
    def validate(self, call_data: Dict, analysis: Dict) -> Tuple[bool, str]:
        title = call_data.get('title', '').strip()
        
        if not title:
            return False, "Title is empty"
        
        # Check for malformed titles
        malformed_patterns = [
            r'^untitled',
            r'^document\s*\d*$',
            r'^file\s*\d*$',
            r'^copy\s+of',
            r'^\s*$',
            r'^test\s*\d*$',
            r'^draft\s*\d*$'
        ]
        
        title_lower = title.lower()
        for pattern in malformed_patterns:
            if re.match(pattern, title_lower):
                return False, f"Malformed title pattern: '{title}'"
        
        # Must contain some meaningful words
        if len(title) < 5:
            return False, f"Title too short: '{title}'"
        
        # Should contain indicators of a meeting/call
        meeting_indicators = [
            'call', 'meeting', 'sync', 'discussion', 'demo', 
            'presentation', 'follow up', 'followup', 'notes', 
            'gemini', 'zoom', 'teams', 'webex'
        ]
        
        if not any(indicator in title_lower for indicator in meeting_indicators):
            # Not blocking, but flag for review
            return True, f"Title may not be call-related but allowed: '{title}'"
        
        return True, "Title is acceptable"

class QCValidator:
    """Main Quality Control Validator"""
    
    def __init__(self, log_level=logging.INFO):
        self.logger = self._setup_logging(log_level)
        
        # Initialize quality gates
        self.gates = [
            ProspectNameGate(),
            AeNameGate(), 
            ContentQualityGate(),
            AnalysisQualityGate(),
            TitleQualityGate()
        ]
        
        self.validation_stats = {
            'total_validated': 0,
            'passed': 0,
            'failed': 0,
            'gate_failures': {}
        }
    
    def _setup_logging(self, log_level):
        """Setup logging for QC validation"""
        logger = logging.getLogger('qc_validator')
        logger.setLevel(log_level)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '[%(asctime)s] QC-%(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def validate_call(self, call_data: Dict, analysis: Dict) -> Tuple[bool, List[str], Dict[str, bool]]:
        """
        Validate a call against all quality gates
        
        Returns:
            (should_post, validation_messages, gate_results)
        """
        self.validation_stats['total_validated'] += 1
        
        messages = []
        gate_results = {}
        should_post = True
        
        prospect_name = call_data.get('prospect_name', 'Unknown')
        
        self.logger.info(f"🔍 Validating call: {prospect_name}")
        
        for gate in self.gates:
            try:
                passed, message = gate.validate(call_data, analysis)
                gate_results[gate.name] = passed
                
                if passed:
                    self.logger.debug(f"  ✅ {gate.name}: {message}")
                    messages.append(f"✅ {gate.name}: {message}")
                else:
                    self.logger.warning(f"  ❌ {gate.name}: {message}")
                    messages.append(f"❌ {gate.name}: {message}")
                    
                    if gate.blocking:
                        should_post = False
                    
                    # Track gate failure stats
                    self.validation_stats['gate_failures'][gate.name] = \
                        self.validation_stats['gate_failures'].get(gate.name, 0) + 1
                
            except Exception as e:
                self.logger.error(f"  💥 Error in {gate.name}: {str(e)}")
                messages.append(f"💥 {gate.name}: Error - {str(e)}")
                gate_results[gate.name] = False
                
                if gate.blocking:
                    should_post = False
        
        # Update stats
        if should_post:
            self.validation_stats['passed'] += 1
            self.logger.info(f"  ✅ PASSED: {prospect_name}")
        else:
            self.validation_stats['failed'] += 1
            self.logger.warning(f"  ❌ FAILED: {prospect_name}")
        
        return should_post, messages, gate_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return {
            **self.validation_stats,
            'success_rate': (
                self.validation_stats['passed'] / max(self.validation_stats['total_validated'], 1)
            ) * 100
        }
    
    def log_filtered_call(self, call_data: Dict, messages: List[str], reason: str = "quality_gate_failure"):
        """Log details of filtered out calls"""
        timestamp = datetime.now().isoformat()
        
        filtered_entry = {
            'timestamp': timestamp,
            'reason': reason,
            'prospect_name': call_data.get('prospect_name'),
            'ae_name': call_data.get('ae_name'),
            'title': call_data.get('title'),
            'call_date': call_data.get('call_date'),
            'source': call_data.get('source'),
            'validation_messages': messages,
            'content_preview': call_data.get('content', '')[:200] + "..." if call_data.get('content') else None
        }
        
        self.logger.info(f"📝 FILTERED CALL LOG: {json.dumps(filtered_entry, indent=2)}")
        
        # Also save to file for audit trail
        try:
            with open('qc_filtered_calls.jsonl', 'a') as f:
                f.write(json.dumps(filtered_entry) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to log filtered call to file: {e}")
    
    def should_post_to_slack(self, call_data: Dict, analysis: Dict) -> Tuple[bool, str]:
        """
        Main entry point for QC validation
        
        Returns:
            (should_post, summary_message)
        """
        should_post, messages, gate_results = self.validate_call(call_data, analysis)
        
        if not should_post:
            self.log_filtered_call(call_data, messages)
            
        # Create summary message
        passed_gates = sum(1 for passed in gate_results.values() if passed)
        total_gates = len(gate_results)
        
        summary = f"QC Validation: {passed_gates}/{total_gates} gates passed"
        
        if should_post:
            summary += " ✅ POSTING TO SLACK"
        else:
            failed_gates = [name for name, passed in gate_results.items() if not passed]
            summary += f" ❌ BLOCKED - Failed: {', '.join(failed_gates)}"
        
        return should_post, summary

# Convenience function for easy import
def validate_call_quality(call_data: Dict, analysis: Dict) -> Tuple[bool, str]:
    """
    Convenience function to validate call quality
    
    Returns:
        (should_post, summary_message)
    """
    validator = QCValidator()
    return validator.should_post_to_slack(call_data, analysis)

if __name__ == "__main__":
    # Test with sample data
    test_call = {
        'prospect_name': 'John Smith',
        'ae_name': 'niamh collins',
        'title': 'Sales call with John Smith - Gemini notes',
        'content': 'Great conversation about Telnyx API solutions. John mentioned they need SMS capabilities for their customer notification system. We discussed pricing and implementation timeline. Next steps: send proposal by Friday.',
        'call_date': '2024-03-04'
    }
    
    test_analysis = {
        'summary': 'Sales call discussing SMS API needs',
        'key_points': ['SMS API requirements', 'Customer notifications'],
        'next_steps': ['Send proposal by Friday'],
        'sentiment': 'positive'
    }
    
    should_post, message = validate_call_quality(test_call, test_analysis)
    print(f"Result: {should_post}")
    print(f"Message: {message}")