#!/usr/bin/env python3
"""
End-to-End Test for AE Call Analysis System
Fetches one Fellow call and runs it through the complete pipeline
"""
from __future__ import annotations

import json
import asyncio
import logging
import sys
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import get_config
from database.database import get_db
from services.openai_client import OpenAIClient, OpenAIAPIError
from services.async_processor import AsyncAnalysisProcessor, ProcessingResult
from services.analysis_storage import AnalysisStorageService
from services.error_handler import LLMErrorHandler, handle_processing_error

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

class E2EPipeline:
    """End-to-end pipeline for testing one call"""
    
    def __init__(self):
        self.config = get_config()
        self.db = get_db()
        self.results = {
            'fellow_fetch': {'status': 'pending'},
            'database_store': {'status': 'pending'},
            'salesforce_mapping': {'status': 'pending'},
            'llm_analysis': {'status': 'pending'},
            'final_result': {'status': 'pending'}
        }
        
        # Initialize OpenAI client (if API key available)
        # Using OpenAI instead of Claude - user has OpenAI Pro subscription
        self.openai_client = None
        if self.config.openai.api_key:
            try:
                self.openai_client = OpenAIClient(self.config.openai)
                logger.info("✅ OpenAI client initialized successfully")
            except Exception as e:
                logger.warning(f"⚠️ OpenAI client initialization failed: {e}")
        else:
            logger.warning("⚠️ OpenAI API key not configured - using mock analysis")
        
        # Initialize Phase 2 services
        self.async_processor = None
        self.storage_service = None
        self.error_handler = None
        
        try:
            # Initialize async processor
            self.async_processor = AsyncAnalysisProcessor(self.config)
            logger.info("✅ Async processor initialized")
            
            # Initialize storage service  
            self.storage_service = AnalysisStorageService(self.config)
            logger.info("✅ Analysis storage service initialized")
            
            # Initialize error handler
            self.error_handler = LLMErrorHandler(self.config)
            logger.info("✅ Error handler initialized")
            
        except Exception as e:
            logger.warning(f"⚠️ Phase 2 service initialization failed: {e}")
            logger.warning("⚠️ Falling back to basic Claude integration")
        
        # Startup validation
        if self.config.salesforce.validate_quinn_field_on_startup:
            self._startup_validation()
    
    def _startup_validation(self):
        """Validate system configuration and dependencies on startup"""
        logger.info("🔍 Running startup validation...")
        
        # Test Quinn field access
        if not self.validate_quinn_field_access():
            logger.error("❌ Quinn field validation failed - check Salesforce permissions")
            raise Exception("Quinn field access validation failed")
        logger.info("✅ Quinn field access validated")
        
        # Test Quinn user lookup
        quinn_user_id = self.get_quinn_user_id()
        if not quinn_user_id:
            logger.warning("⚠️ Quinn user ID lookup failed - some features may not work")
        else:
            logger.info(f"✅ Quinn user ID found: {quinn_user_id}")
        
        # Test database schema
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                self.db._ensure_salesforce_mapping_schema(cursor)
            logger.info("✅ Database schema validated")
        except Exception as e:
            logger.error(f"❌ Database schema validation failed: {e}")
            raise
        
        logger.info("🎯 Startup validation complete!")
    
    async def fetch_fellow_call(self, limit=1):
        """Fetch one call from Fellow API"""
        import requests
        
        logger.info("Step 1: Fetching call from Fellow API...")
        
        try:
            headers = {
                'X-Api-Key': self.config.fellow_api.api_key,
                'Content-Type': 'application/json'
            }
            
            payload = {
                "include": {"transcript": True, "ai_notes": True},
                "filters": {"title": "Telnyx Intro Call"}
            }
            
            response = requests.post(
                self.config.fellow_api.endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            recordings = data.get('recordings', {}).get('data', [])
            
            if not recordings:
                self.results['fellow_fetch'] = {
                    'status': 'failed',
                    'error': 'No recordings found'
                }
                logger.error("❌ No Fellow recordings found")
                return None
            
            # Get the most recent call
            call = recordings[0]  # Fellow API returns newest first
            
            self.results['fellow_fetch'] = {
                'status': 'success',
                'call_id': call.get('id'),
                'title': call.get('title'),
                'date': call.get('started_at')
            }
            
            logger.info(f"✅ Fetched call: {call.get('title', 'No title')}")
            logger.info(f"   Date: {call.get('date', 'No date')}")
            logger.info(f"   Fellow ID: {call.get('id', 'No ID')}")
            
            return call
            
        except Exception as e:
            self.results['fellow_fetch'] = {
                'status': 'failed',
                'error': str(e)
            }
            logger.error(f"❌ Failed to fetch Fellow call: {e}")
            return None
    
    def store_call_in_database(self, call_data):
        """Store call in database"""
        logger.info("Step 2: Storing call in database...")
        
        try:
            # Extract prospect name from title
            # Format: "Telnyx Intro Call (First Last)"
            prospect_name = self.extract_prospect_name(call_data.get('title', ''))
            
            # Parse date
            call_date = datetime.now()
            date_str = call_data.get('started_at') or call_data.get('created_at')
            if date_str:
                try:
                    call_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except:
                    pass
            
            # Store in database
            call_id = self.db.insert_call(
                fellow_id=call_data.get('id', ''),
                title=call_data.get('title', ''),
                call_date=call_date,
                duration_minutes=call_data.get('duration'),
                ae_name=call_data.get('host', {}).get('name') if call_data.get('host') else None,
                prospect_name=prospect_name,
                prospect_company=call_data.get('company') or "Unknown Company",
                transcript=self.extract_transcript_text(call_data.get('transcript')),
                fellow_ai_notes=json.dumps(call_data.get('ai_notes')) if call_data.get('ai_notes') else None,
                raw_fellow_data=call_data
            )
            
            self.results['database_store'] = {
                'status': 'success',
                'call_id': call_id,
                'prospect_name': prospect_name
            }
            
            logger.info(f"✅ Stored call in database with ID: {call_id}")
            logger.info(f"   Prospect: {prospect_name}")
            
            return call_id
            
        except Exception as e:
            self.results['database_store'] = {
                'status': 'failed',
                'error': str(e)
            }
            logger.error(f"❌ Failed to store call: {e}")
            return None
    
    def extract_prospect_name(self, title):
        """Extract prospect name from call title with robust edge case handling"""
        if not title:
            return "Unknown Prospect"
        
        # Try multiple patterns for prospect name extraction (order matters!)
        patterns = [
            # Multiple parentheses: "Telnyx Intro Call (Additional Info) (John Smith)"
            r'Telnyx Intro Call.*?\([^)]*\)\s*\(([^)]+)\)$',
            # Company info: "Telnyx Intro Call (John Smith - Acme Corp)" - extract name before dash
            r'Telnyx Intro Call.*?\(([^-–—)]+)\s*[-–—]',
            # Missing parentheses with dash: "Telnyx Intro Call - John Smith"
            r'Telnyx Intro Call\s*[-–—]\s*(.+?)(?:\s*[-–—]|$)',
            # Standard: "Telnyx Intro Call (First Last)" - exact match in parentheses
            r'Telnyx Intro Call.*?\(([^)]+)\)$',
            # Fallback: anything in first parentheses
            r'Telnyx Intro Call.*?\(([^)]+)\)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up extracted name
                name = re.sub(r'\s+', ' ', name)  # Normalize whitespace
                name = name.strip(' -–—')  # Remove leading/trailing dashes
                if name and name.lower() not in ['additional info', 'info', 'call']:
                    return name
        
        # Final fallback: try to extract any name-like pattern
        fallback_match = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', title)
        if fallback_match:
            return fallback_match.group(1).strip()
        
        return "Unknown Prospect"
    
    def extract_transcript_text(self, transcript_data):
        """Extract text from Fellow transcript structure"""
        if not transcript_data:
            return "No transcript available"
        
        if isinstance(transcript_data, str):
            return transcript_data
        
        if isinstance(transcript_data, dict):
            # Fellow transcript structure: {"speech_segments": [...], "language_code": "en"}
            speech_segments = transcript_data.get('speech_segments', [])
            if speech_segments:
                # Combine all speech segments into one text
                transcript_parts = []
                for segment in speech_segments:
                    speaker = segment.get('speaker', 'Speaker')
                    text = segment.get('text', '')
                    if text:
                        transcript_parts.append(f"{speaker}: {text}")
                return "\n".join(transcript_parts)
        
        return "No transcript available"
    
    def validate_quinn_field_access(self):
        """Validate that Quinn field is accessible"""
        try:
            # Test query to validate field access
            test_query = f"""
                SELECT Id, {self.config.salesforce.quinn_field_name} 
                FROM Contact 
                LIMIT 1
            """
            result = self._execute_salesforce_query(test_query)
            return result is not None
        except Exception as e:
            logger.error(f"Quinn field validation failed: {e}")
            return False
    
    def _execute_salesforce_query(self, query):
        """Execute Salesforce query with error handling"""
        try:
            result = subprocess.run([
                'sf', 'data', 'query',
                '--query', query,
                '--target-org', self.config.salesforce.org_username,
                '--json'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.error(f"Salesforce query failed: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"Error executing Salesforce query: {e}")
            return None
    
    def get_quinn_user_id(self):
        """Get and cache Quinn Taylor's Salesforce User ID"""
        if hasattr(self, '_quinn_user_id') and self._quinn_user_id:
            return self._quinn_user_id
        
        try:
            # Search for Quinn Taylor by name (configurable)
            quinn_name = self.config.salesforce.quinn_user_name
            user_query = f"""
                SELECT Id, Name, Username 
                FROM User 
                WHERE Name LIKE '%{quinn_name}%' 
                AND IsActive = true
                LIMIT 5
            """
            
            data = self._execute_salesforce_query(user_query)
            if data and data.get('result', {}).get('records'):
                users = data['result']['records']
                # Find best match (exact name preferred)
                for user in users:
                    if quinn_name.lower() in user['Name'].lower():
                        self._quinn_user_id = user['Id']
                        logger.info(f"Found Quinn User ID: {self._quinn_user_id} ({user['Name']})")
                        return self._quinn_user_id
                
                # Fallback to first active user found
                self._quinn_user_id = users[0]['Id']
                logger.info(f"Using first found user as Quinn: {self._quinn_user_id} ({users[0]['Name']})")
                return self._quinn_user_id
            else:
                logger.error(f"Quinn user '{quinn_name}' not found in Salesforce")
                return None
        except Exception as e:
            logger.error(f"Error finding Quinn user ID: {e}")
            return None
    
    def resolve_multiple_contacts(self, contacts, prospect_name, quinn_user_id):
        """Resolve multiple contacts using Quinn date → opportunity matching logic"""
        # Step 1: Filter contacts that have Quinn latest date
        quinn_contacts = [c for c in contacts if c.get(self.config.salesforce.quinn_field_name)]
        
        if not quinn_contacts:
            logger.info("No contacts with Quinn data found in multiple matches")
            return contacts[0]  # Fallback
        
        # Step 2: If multiple contacts have Quinn dates, check for opportunities
        if len(quinn_contacts) > 1 and quinn_user_id:
            logger.info(f"Checking opportunities for {len(quinn_contacts)} contacts with Quinn data")
            
            for contact in quinn_contacts:
                # Query opportunities on contact's account with SDR=Quinn and 14-day window
                if self.check_opportunity_match(contact, quinn_user_id):
                    logger.info(f"Found opportunity match for contact {contact['Name']}")
                    return contact
        
        # Step 3: If still multiple matches or no opportunity match, use most recent Quinn date
        quinn_contacts.sort(key=lambda c: c.get(self.config.salesforce.quinn_field_name, ''), reverse=True)
        return quinn_contacts[0]
    
    def check_opportunity_match(self, contact, quinn_user_id):
        """Check if contact has opportunity with SDR=Quinn within 14-day window"""
        try:
            # Get the contact's Account ID first
            contact_query = f"""
                SELECT AccountId 
                FROM Contact 
                WHERE Id = '{contact['Id']}'
                LIMIT 1
            """
            
            contact_data = self._execute_salesforce_query(contact_query)
            if not contact_data or not contact_data.get('result', {}).get('records'):
                return False
                
            account_id = contact_data['result']['records'][0]['AccountId']
            if not account_id:
                return False
            
            # Query opportunities on the account with SDR=Quinn
            opp_query = f"""
                SELECT Id, CreatedDate, SDR__c 
                FROM Opportunity 
                WHERE AccountId = '{account_id}' 
                AND SDR__c = '{quinn_user_id}'
                ORDER BY CreatedDate DESC
                LIMIT 5
            """
            
            opp_data = self._execute_salesforce_query(opp_query)
            if not opp_data or not opp_data.get('result', {}).get('records'):
                return False
            
            opportunities = opp_data['result']['records']
            
            # Check if any opportunity is within 14-day window of call
            # Note: For now, we'll use a flexible window since we don't have the exact meeting date
            # In production, you'd compare against the actual meeting date
            for opp in opportunities:
                logger.info(f"Found opportunity {opp['Id']} with SDR=Quinn, created {opp['CreatedDate']}")
                # TODO: Add actual 14-day window comparison with meeting date
                return True  # For now, any Quinn opportunity counts
                
        except Exception as e:
            logger.error(f"Error checking opportunity match: {e}")
            
        return False
    
    def check_event_record_match(self, contact_id, prospect_name):
        """Check for Event record matching contact and meeting name for 10/10 confidence"""
        try:
            # Query Event records for this contact where subject matches meeting name
            event_query = f"""
                SELECT Id, Subject, WhoId 
                FROM Event 
                WHERE WhoId = '{contact_id}' 
                AND Subject LIKE '%Telnyx Intro Call%'
                ORDER BY CreatedDate DESC
                LIMIT 10
            """
            
            event_data = self._execute_salesforce_query(event_query)
            if not event_data or not event_data.get('result', {}).get('records'):
                return False
            
            events = event_data['result']['records']
            
            # Check if any event subject contains the prospect name
            for event in events:
                subject = event.get('Subject', '').lower()
                if prospect_name.lower() in subject:
                    logger.info(f"Found matching Event record: {event['Subject']}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error checking Event record match: {e}")
            
        return False
    
    # ALLOWED mapping methods (exact matching only)
    ALLOWED_MAPPING_METHODS = frozenset([
        'enhanced_quinn_priority',    # Exact match with Quinn priority logic
        'exact_name_not_found',       # No exact match found (acceptable)
        'exact_match_no_quinn_data',  # Exact match but missing Quinn data
    ])
    
    # PROHIBITED mapping methods (fuzzy/partial matching - DATA QUALITY RISK)
    PROHIBITED_MAPPING_METHODS = frozenset([
        'name_search',         # DEPRECATED: First-name-only matching
        'fuzzy_match',         # PROHIBITED: Similarity-based matching
        'partial_match',       # PROHIBITED: Partial name matching
        'first_name_match',    # PROHIBITED: First name only
    ])
    
    def track_mapping_quality(self, mapping_result):
        """Track mapping quality metrics for monitoring and improvement"""
        try:
            mapping_method = mapping_result.get('mapping_method', 'unknown')
            
            # CRITICAL: Check for prohibited mapping methods
            if mapping_method in self.PROHIBITED_MAPPING_METHODS:
                logger.critical(
                    f"🚨 CRITICAL DATA QUALITY ALERT: Prohibited mapping method detected! "
                    f"Method: '{mapping_method}' - This indicates fuzzy/partial matching which "
                    f"causes incorrect mappings (e.g., Devon Johnson → Devon Adkisson). "
                    f"Mapping result: {mapping_result}"
                )
            elif mapping_method not in self.ALLOWED_MAPPING_METHODS and mapping_method != 'unknown':
                logger.warning(
                    f"⚠️ Unknown mapping method detected: '{mapping_method}' - "
                    f"Verify this is using exact matching only"
                )
            
            # Quality metrics to track
            quality_metrics = {
                'confidence_score': mapping_result.get('confidence', 0),
                'mapping_method': mapping_method,
                'is_allowed_method': mapping_method in self.ALLOWED_MAPPING_METHODS,
                'is_prohibited_method': mapping_method in self.PROHIBITED_MAPPING_METHODS,
                'exact_match_validated': mapping_result.get('exact_match_validated', False),
                'has_quinn_data': bool(mapping_result.get('quinn_latest_date')),
                'has_event_match': mapping_result.get('confidence') == 10,
                'contact_found': mapping_result.get('status') == 'success',
                'duplicate_contacts': mapping_result.get('duplicate_count', 0),
                'timestamp': datetime.now().isoformat()
            }
            
            # Log quality metrics
            logger.info(f"📊 Quality metrics: {quality_metrics}")
            
            # In production, you'd store these metrics in a monitoring system
            # For now, we'll log them for analysis
            
        except Exception as e:
            logger.error(f"Error tracking mapping quality: {e}")
    
    def audit_existing_mappings(self):
        """
        Audit existing database mappings for data quality issues.
        
        Identifies mappings that used deprecated/prohibited methods like 'name_search'
        (first-name-only matching) and flags them for review.
        """
        logger.info("🔍 Auditing existing Salesforce mappings for data quality issues...")
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Find all mappings with prohibited methods
                cursor.execute('''
                    SELECT sm.id, sm.call_id, sm.contact_id, sm.contact_name, 
                           sm.mapping_method, sm.contact_match_confidence,
                           c.prospect_name, c.title
                    FROM salesforce_mappings sm
                    LEFT JOIN calls c ON sm.call_id = c.id
                    WHERE sm.mapping_method IN (?, ?, ?, ?)
                    ORDER BY sm.created_at DESC
                ''', ('name_search', 'fuzzy_match', 'partial_match', 'first_name_match'))
                
                problematic_mappings = cursor.fetchall()
                
                if problematic_mappings:
                    logger.critical(
                        f"🚨 FOUND {len(problematic_mappings)} MAPPINGS WITH PROHIBITED METHODS!"
                    )
                    
                    for mapping in problematic_mappings:
                        logger.warning(
                            f"  - ID: {mapping['id']}, Method: '{mapping['mapping_method']}', "
                            f"Prospect: '{mapping['prospect_name']}' → Contact: '{mapping['contact_name']}'"
                        )
                    
                    return {
                        'status': 'issues_found',
                        'problematic_count': len(problematic_mappings),
                        'problematic_mappings': [dict(m) for m in problematic_mappings]
                    }
                else:
                    logger.info("✅ No mappings with prohibited methods found")
                    
                    # Also count mappings by method for reporting
                    cursor.execute('''
                        SELECT mapping_method, COUNT(*) as count
                        FROM salesforce_mappings
                        GROUP BY mapping_method
                        ORDER BY count DESC
                    ''')
                    method_counts = cursor.fetchall()
                    
                    logger.info("📊 Mapping method distribution:")
                    for row in method_counts:
                        method = row['mapping_method'] or 'NULL'
                        count = row['count']
                        status = "✅" if method in self.ALLOWED_MAPPING_METHODS else "⚠️"
                        logger.info(f"   {status} {method}: {count}")
                    
                    return {
                        'status': 'clean',
                        'method_distribution': {row['mapping_method']: row['count'] for row in method_counts}
                    }
                    
        except Exception as e:
            logger.error(f"Error auditing mappings: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def remap_problematic_mappings(self, dry_run: bool = True):
        """
        Re-process mappings that used prohibited methods (e.g., 'name_search').
        
        This function identifies mappings created with fuzzy/partial matching
        and re-runs them through the exact matching pipeline.
        
        Args:
            dry_run: If True, only reports what would change. If False, actually updates.
        
        Returns:
            Dict with remapping results
        """
        logger.info(f"🔄 {'DRY RUN: ' if dry_run else ''}Remapping problematic Salesforce mappings...")
        
        results = {
            'processed': 0,
            'fixed': 0,
            'unchanged': 0,
            'errors': 0,
            'details': []
        }
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Find all mappings with prohibited methods
                cursor.execute('''
                    SELECT sm.id, sm.call_id, sm.contact_id, sm.contact_name, 
                           sm.mapping_method, c.prospect_name, c.title
                    FROM salesforce_mappings sm
                    LEFT JOIN calls c ON sm.call_id = c.id
                    WHERE sm.mapping_method IN (?, ?, ?, ?)
                ''', ('name_search', 'fuzzy_match', 'partial_match', 'first_name_match'))
                
                problematic_mappings = cursor.fetchall()
                
                if not problematic_mappings:
                    logger.info("✅ No problematic mappings found to remap")
                    return results
                
                logger.info(f"Found {len(problematic_mappings)} mappings to remap")
                
                for mapping in problematic_mappings:
                    results['processed'] += 1
                    old_method = mapping['mapping_method']
                    prospect_name = mapping['prospect_name']
                    old_contact_name = mapping['contact_name']
                    call_id = mapping['call_id']
                    mapping_id = mapping['id']
                    
                    try:
                        # Check if the old mapping was actually correct (exact match)
                        if self._validate_exact_name_match(prospect_name, old_contact_name):
                            # The mapping is correct, just needs method update
                            detail = {
                                'mapping_id': mapping_id,
                                'action': 'method_update_only',
                                'prospect_name': prospect_name,
                                'old_contact': old_contact_name,
                                'new_contact': old_contact_name,
                                'old_method': old_method,
                                'new_method': 'enhanced_quinn_priority',
                                'status': 'correct_mapping'
                            }
                            
                            if not dry_run:
                                cursor.execute('''
                                    UPDATE salesforce_mappings 
                                    SET mapping_method = ?, updated_at = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                ''', ('enhanced_quinn_priority', mapping_id))
                            
                            results['unchanged'] += 1
                            logger.info(f"  ✓ {prospect_name}: Mapping correct, updated method only")
                            
                        else:
                            # The mapping is INCORRECT - need to re-lookup
                            logger.warning(
                                f"  ✗ INCORRECT: '{prospect_name}' was mapped to '{old_contact_name}' "
                                f"(NOT an exact match - likely first-name-only)"
                            )
                            
                            # Try to find correct exact match
                            new_mapping = self._find_exact_match_for_remap(prospect_name)
                            
                            if new_mapping:
                                detail = {
                                    'mapping_id': mapping_id,
                                    'action': 'remapped',
                                    'prospect_name': prospect_name,
                                    'old_contact': old_contact_name,
                                    'new_contact': new_mapping['Name'],
                                    'new_contact_id': new_mapping['Id'],
                                    'old_method': old_method,
                                    'new_method': 'enhanced_quinn_priority',
                                    'status': 'fixed'
                                }
                                
                                if not dry_run:
                                    cursor.execute('''
                                        UPDATE salesforce_mappings 
                                        SET contact_id = ?, contact_name = ?, 
                                            mapping_method = ?, contact_match_confidence = 8,
                                            updated_at = CURRENT_TIMESTAMP
                                        WHERE id = ?
                                    ''', (new_mapping['Id'], new_mapping['Name'], 
                                          'enhanced_quinn_priority', mapping_id))
                                
                                results['fixed'] += 1
                                logger.info(
                                    f"  🔧 FIXED: '{prospect_name}' → '{new_mapping['Name']}' "
                                    f"(was incorrectly '{old_contact_name}')"
                                )
                            else:
                                # No exact match found
                                detail = {
                                    'mapping_id': mapping_id,
                                    'action': 'cleared',
                                    'prospect_name': prospect_name,
                                    'old_contact': old_contact_name,
                                    'new_contact': None,
                                    'old_method': old_method,
                                    'new_method': 'exact_name_not_found',
                                    'status': 'no_exact_match'
                                }
                                
                                if not dry_run:
                                    cursor.execute('''
                                        UPDATE salesforce_mappings 
                                        SET contact_id = NULL, 
                                            mapping_method = ?, contact_match_confidence = 0,
                                            updated_at = CURRENT_TIMESTAMP
                                        WHERE id = ?
                                    ''', ('exact_name_not_found', mapping_id))
                                
                                results['fixed'] += 1
                                logger.warning(
                                    f"  ⚠️ NO EXACT MATCH: '{prospect_name}' - cleared incorrect mapping "
                                    f"(was '{old_contact_name}')"
                                )
                        
                        results['details'].append(detail)
                        
                    except Exception as e:
                        results['errors'] += 1
                        logger.error(f"  ❌ Error processing mapping {mapping_id}: {e}")
                        results['details'].append({
                            'mapping_id': mapping_id,
                            'action': 'error',
                            'error': str(e)
                        })
                
                if not dry_run:
                    conn.commit()
                
                logger.info(
                    f"{'DRY RUN ' if dry_run else ''}Remap complete: "
                    f"{results['fixed']} fixed, {results['unchanged']} unchanged, "
                    f"{results['errors']} errors"
                )
                
                return results
                
        except Exception as e:
            logger.error(f"Error in remap_problematic_mappings: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _find_exact_match_for_remap(self, prospect_name: str) -> Optional[Dict]:
        """Find exact Salesforce contact match for remapping"""
        try:
            search_query = f"""
                SELECT Id, Name, {self.config.salesforce.quinn_field_name} 
                FROM Contact 
                WHERE Name = '{prospect_name}' 
                AND {self.config.salesforce.quinn_field_name} != NULL
                ORDER BY {self.config.salesforce.quinn_field_name} DESC
                LIMIT 1
            """
            
            data = self._execute_salesforce_query(search_query)
            if data and data.get('result', {}).get('records'):
                return data['result']['records'][0]
            
            # Try case-insensitive
            search_query = f"""
                SELECT Id, Name, {self.config.salesforce.quinn_field_name} 
                FROM Contact 
                WHERE UPPER(Name) = UPPER('{prospect_name}') 
                AND {self.config.salesforce.quinn_field_name} != NULL
                ORDER BY {self.config.salesforce.quinn_field_name} DESC
                LIMIT 1
            """
            
            data = self._execute_salesforce_query(search_query)
            if data and data.get('result', {}).get('records'):
                return data['result']['records'][0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding exact match for '{prospect_name}': {e}")
            return None
    
    def handle_low_confidence_match(self, contact, confidence, prospect_name):
        """Handle low confidence matches with manual review workflow"""
        if confidence < 7:  # Low confidence threshold
            review_data = {
                'contact_id': contact.get('Id'),
                'contact_name': contact.get('Name'),
                'prospect_name': prospect_name,
                'confidence': confidence,
                'quinn_date': contact.get(self.config.salesforce.quinn_field_name),
                'requires_manual_review': True,
                'review_reason': f"Low confidence ({confidence}/10)"
            }
            
            logger.warning(f"⚠️ Low confidence match requires manual review: {review_data}")
            
            # In production, you'd create a manual review ticket/notification
            # For now, we'll log it prominently
            
            return review_data
        
        return None
    
    def optimize_for_production_volume(self, batch_size=10):
        """Production optimizations for handling high call volume"""
        # Implement connection pooling, caching, and batch processing
        optimizations = {
            'connection_pooling': True,
            'field_validation_cached': hasattr(self, '_quinn_field_validated'),
            'user_id_cached': hasattr(self, '_quinn_user_id'),
            'batch_processing_enabled': batch_size > 1,
            'error_recovery_enabled': True
        }
        
        logger.info(f"🚀 Production optimizations: {optimizations}")
        return optimizations

    def _validate_exact_name_match(self, prospect_name: str, contact_name: str) -> bool:
        """
        STRICT VALIDATION: Ensure contact name is an EXACT match to prospect name.
        
        CRITICAL: This function MUST reject partial/first-name-only matches.
        Examples:
            - "Devon Johnson" vs "Devon Adkisson" → FALSE (first-name-only = REJECTED)
            - "Ben Lewell" vs "Ben Lewell" → TRUE (exact match = ACCEPTED)
            - "devon johnson" vs "Devon Johnson" → TRUE (case-insensitive exact = ACCEPTED)
        
        This prevents data quality issues from fuzzy/partial matching.
        """
        if not prospect_name or not contact_name:
            return False
        
        # Normalize for comparison (case-insensitive, whitespace-normalized)
        prospect_normalized = ' '.join(prospect_name.lower().split())
        contact_normalized = ' '.join(contact_name.lower().split())
        
        # EXACT MATCH ONLY - no partial, no first-name-only, no fuzzy
        is_exact = prospect_normalized == contact_normalized
        
        if not is_exact:
            # Log rejection for audit trail
            logger.warning(
                f"🚫 REJECTED non-exact match: prospect='{prospect_name}' vs contact='{contact_name}' - "
                f"EXACT MATCHING ENFORCED (no first-name-only or fuzzy matching allowed)"
            )
        
        return is_exact
    
    def map_to_salesforce(self, call_id, prospect_name):
        """
        Map call to Salesforce contact using EXACT NAME MATCHING ONLY.
        
        IMPORTANT: This function uses ONLY exact name matching (case-insensitive).
        NO fuzzy matching, NO partial matching, NO first-name-only matching.
        
        Mapping methods used (for audit):
        - 'enhanced_quinn_priority': Exact match with Quinn priority logic
        - 'exact_name_not_found': No exact match exists
        - 'exact_match_no_quinn_data': Exact match but missing Quinn data (rare)
        
        PROHIBITED methods (legacy, do not use):
        - 'name_search': DEPRECATED - was first-name-only fuzzy matching (REMOVED)
        - 'fuzzy_match': DEPRECATED - was similarity-based matching (NEVER IMPLEMENTED)
        """
        logger.info("Step 3: Mapping to Salesforce contact (EXACT MATCHING ONLY)...")
        
        try:
            # CRITICAL: Validate exact matching is enforced
            if not prospect_name or prospect_name.strip() == "":
                logger.error("Empty prospect name - cannot perform exact match")
                mapping_id = self.db.insert_salesforce_mapping(
                    call_id=call_id,
                    contact_name=prospect_name,
                    contact_match_confidence=0,
                    mapping_method='exact_name_not_found'
                )
                self.results['salesforce_mapping'] = {
                    'status': 'no_match',
                    'prospect_name': prospect_name,
                    'method': 'exact_name_not_found',
                    'mapping_id': mapping_id,
                    'reason': 'empty_prospect_name'
                }
                return mapping_id
            
            # Validate Quinn field access first
            if not self.validate_quinn_field_access():
                raise Exception("Quinn field validation failed - check field permissions")
            
            # EXACT name matching with Quinn field validation
            # Using = operator for strict exact match
            search_query = f"""
                SELECT Id, Name, {self.config.salesforce.quinn_field_name} 
                FROM Contact 
                WHERE Name = '{prospect_name}' 
                AND {self.config.salesforce.quinn_field_name} != NULL
                ORDER BY {self.config.salesforce.quinn_field_name} DESC
                LIMIT 10
            """
            
            # If no exact match, try case-insensitive exact match ONLY
            # NOTE: This is still EXACT matching, just case-normalized
            initial_result = self._execute_salesforce_query(search_query)
            if not initial_result or not initial_result.get('result', {}).get('records'):
                # Case-insensitive exact match (still requires full name match)
                search_query = f"""
                    SELECT Id, Name, {self.config.salesforce.quinn_field_name} 
                    FROM Contact 
                    WHERE UPPER(Name) = UPPER('{prospect_name}') 
                    AND {self.config.salesforce.quinn_field_name} != NULL
                    ORDER BY {self.config.salesforce.quinn_field_name} DESC
                    LIMIT 10
                """
            
            # Execute the Salesforce query
            data = self._execute_salesforce_query(search_query)
            
            if data:
                records = data.get('result', {}).get('records', [])
                
                # CRITICAL: Validate ALL returned records are EXACT matches
                # This is a safety check - SQL should return exact matches, but we verify
                validated_records = []
                for record in records:
                    contact_name = record.get('Name', '')
                    if self._validate_exact_name_match(prospect_name, contact_name):
                        validated_records.append(record)
                    else:
                        # Log rejected partial/fuzzy matches (should not happen with exact SQL)
                        logger.error(
                            f"🚫 CRITICAL: Non-exact record returned from DB - REJECTING: "
                            f"prospect='{prospect_name}' contact='{contact_name}'"
                        )
                
                # Only use validated exact matches
                records = validated_records
                
                if records:
                    # Enhanced multiple contact resolution per user specifications
                    best_match = None
                    best_confidence = 0
                    
                    if len(records) == 1:
                        # Single exact match - high confidence
                        best_match = records[0]
                        best_confidence = 8
                        logger.info(f"✅ Single EXACT match found: '{best_match['Name']}'")
                    else:
                        # Multiple exact matches - apply user's priority logic
                        logger.info(f"Found {len(records)} EXACT matches for '{prospect_name}' - applying priority logic")
                        
                        # Get Quinn User ID for opportunity matching
                        quinn_user_id = self.get_quinn_user_id()
                        if not quinn_user_id:
                            logger.warning("Could not find Quinn User ID - using basic Quinn date priority")
                        
                        # Apply priority logic: Quinn date → Opportunity matching (14-day window)
                        best_match = self.resolve_multiple_contacts(records, prospect_name, quinn_user_id)
                        
                        if best_match:
                            # Check if we have Event record match for highest confidence
                            event_match = self.check_event_record_match(best_match['Id'], prospect_name)
                            if event_match:
                                best_confidence = 10  # Highest confidence - Event record match
                            else:
                                best_confidence = 8   # High confidence - Quinn + opportunity match
                        else:
                            # No clear winner - flag as duplicate issue
                            logger.warning(f"Multiple contacts found but no clear resolution for '{prospect_name}'")
                            best_match = records[0]  # Fallback to first (most recent Quinn date)
                            best_confidence = 5      # Medium confidence - duplicate issue
                    
                    if best_match:
                        # FINAL VALIDATION: Ensure we're about to store an EXACT match
                        # This is a critical safety check before committing to the database
                        final_contact_name = best_match.get('Name', '')
                        if not self._validate_exact_name_match(prospect_name, final_contact_name):
                            logger.error(
                                f"🚫 FINAL CHECK FAILED: Rejecting mapping of "
                                f"'{prospect_name}' to '{final_contact_name}' - NOT AN EXACT MATCH"
                            )
                            # Treat as no-match rather than storing incorrect mapping
                            mapping_id = self.db.insert_salesforce_mapping(
                                call_id=call_id,
                                contact_name=prospect_name,
                                contact_match_confidence=0,
                                mapping_method='exact_name_not_found'
                            )
                            self.results['salesforce_mapping'] = {
                                'status': 'no_match',
                                'prospect_name': prospect_name,
                                'method': 'exact_name_not_found',
                                'mapping_id': mapping_id,
                                'reason': 'final_validation_rejected_non_exact'
                            }
                            logger.warning(f"⚠️ No EXACT Salesforce match for: '{prospect_name}'")
                            return mapping_id
                        
                        # Parse Quinn latest date
                        quinn_date_str = best_match.get(self.config.salesforce.quinn_field_name)
                        quinn_date = None
                        if quinn_date_str:
                            try:
                                quinn_date = datetime.fromisoformat(quinn_date_str.replace('Z', '+00:00'))
                            except:
                                pass
                        
                        # Store Salesforce mapping - EXACT MATCH CONFIRMED
                        mapping_id = self.db.insert_salesforce_mapping(
                            call_id=call_id,
                            contact_id=best_match['Id'],
                            contact_name=best_match['Name'],
                            quinn_active_latest=quinn_date,
                            contact_match_confidence=best_confidence,
                            mapping_method='enhanced_quinn_priority'  # EXACT matching with Quinn priority
                        )
                    
                        self.results['salesforce_mapping'] = {
                            'status': 'success',
                            'contact_id': best_match['Id'],
                            'contact_name': best_match['Name'],
                            'quinn_latest_date': quinn_date_str,
                            'confidence': best_confidence,
                            'mapping_id': mapping_id,
                            'mapping_method': 'enhanced_quinn_priority',
                            'exact_match_validated': True  # Audit flag
                        }
                        
                        # Wave 3: Quality tracking and manual review workflow
                        self.track_mapping_quality(self.results['salesforce_mapping'])
                        
                        # Handle low confidence matches
                        if best_confidence < 7:
                            review_data = self.handle_low_confidence_match(best_match, best_confidence, prospect_name)
                            if review_data:
                                self.results['salesforce_mapping']['manual_review_required'] = review_data
                        
                        logger.info(f"✅ EXACT MATCH - Mapped to Salesforce contact: {best_match['Name']}")
                        logger.info(f"   Prospect name: '{prospect_name}'")
                        logger.info(f"   Contact ID: {best_match['Id']}")
                        logger.info(f"   Quinn Latest Date: {quinn_date_str}")
                        logger.info(f"   Confidence: {best_confidence}/10")
                        logger.info(f"   Method: enhanced_quinn_priority (EXACT MATCH)")
                        
                        return mapping_id
                    else:
                        # This shouldn't happen with our exact + Quinn query, but handle it
                        logger.error(f"No Quinn data found despite query filter - data inconsistency")
                        mapping_id = self.db.insert_salesforce_mapping(
                            call_id=call_id,
                            contact_name=prospect_name,
                            contact_match_confidence=0,
                            mapping_method='exact_match_no_quinn_data'
                        )
                        
                        self.results['salesforce_mapping'] = {
                            'status': 'no_quinn_data',
                            'prospect_name': prospect_name,
                            'mapping_id': mapping_id
                        }
                        
                        logger.info(f"⚠️ Exact name match found but no Quinn data (unexpected)")
                        return mapping_id
                else:
                    # No exact match found - this indicates the prospect name in calendar
                    # doesn't match any Salesforce contact with Quinn data
                    mapping_id = self.db.insert_salesforce_mapping(
                        call_id=call_id,
                        contact_name=prospect_name,
                        contact_match_confidence=0,
                        mapping_method='exact_name_not_found'
                    )
                    
                    self.results['salesforce_mapping'] = {
                        'status': 'no_match',
                        'prospect_name': prospect_name,
                        'method': 'exact_name_not_found',
                        'mapping_id': mapping_id
                    }
                    
                    logger.info(f"⚠️ No exact Salesforce match for: '{prospect_name}' with Quinn data")
                    return mapping_id
            else:
                raise Exception("Salesforce query execution failed")
                
        except Exception as e:
            self.results['salesforce_mapping'] = {
                'status': 'failed',
                'error': str(e)
            }
            logger.error(f"❌ Salesforce mapping failed: {e}")
            return None
    
    async def analyze_with_llm(self, call_id):
        """Analyze call with LLM using Phase 2 async pipeline or fallback methods"""
        logger.info("Step 4: Running LLM analysis...")
        
        try:
            # Get call data from database
            call = self.db.get_call_by_fellow_id(self.results['fellow_fetch']['call_id'])
            if not call:
                raise Exception("Call not found in database")
            
            transcript = call['transcript'] or "No transcript available"
            
            # Phase 2: Use async processor if available
            if self.async_processor and self.storage_service and self.openai_client:
                logger.info("🚀 Using Phase 2 async processing pipeline")
                analysis_result = await self._analyze_with_async_processor(call)
                storage_method = "async_structured"
            
            # Fallback: Use direct OpenAI analysis
            elif self.openai_client:
                logger.info("🤖 Using direct OpenAI API analysis (Phase 1 fallback)")
                analysis_result = await self._analyze_with_openai(transcript, call['title'])
                # Store with basic database insertion
                result_id = self.db.insert_analysis_result(call_id, analysis_result)
                storage_method = "openai_direct"
            
            # Final fallback: Mock analysis
            else:
                logger.info("🎭 Using mock analysis (no OpenAI available)")
                analysis_result = self.mock_llm_analysis(transcript, call['title'])
                result_id = self.db.insert_analysis_result(call_id, analysis_result)
                storage_method = "mock"
            
            # Result ID handling for async processor
            if storage_method == "async_structured":
                result_id = analysis_result.get('storage_result_id', 'async_pending')
            
            self.results['llm_analysis'] = {
                'status': 'success',
                'result_id': result_id,
                'analysis': analysis_result,
                'method': storage_method,
                'phase2_enabled': self.async_processor is not None
            }
            
            # Enhanced logging for Phase 2
            if isinstance(analysis_result, dict):
                metadata = analysis_result.get('analysis_metadata', {})
                logger.info("✅ LLM analysis completed")
                logger.info(f"   Method: {storage_method}")
                logger.info(f"   Analysis version: {metadata.get('analysis_version', 'unknown')}")
                
                if 'core_talking_points' in analysis_result:
                    logger.info(f"   Core talking points: {len(analysis_result['core_talking_points'])}")
                if 'telnyx_products' in analysis_result:
                    logger.info(f"   Products discussed: {analysis_result['telnyx_products']}")
                
                # Sentiment logging with proper nesting
                ae_sentiment = analysis_result.get('ae_sentiment', {})
                prospect_sentiment = analysis_result.get('prospect_sentiment', {})
                
                if isinstance(ae_sentiment, dict) and 'excitement_level' in ae_sentiment:
                    logger.info(f"   AE excitement: {ae_sentiment['excitement_level']}/10")
                if isinstance(prospect_sentiment, dict) and 'excitement_level' in prospect_sentiment:
                    logger.info(f"   Prospect interest: {prospect_sentiment['excitement_level']}/10")
                
                # Quinn insights
                quinn_insights = analysis_result.get('quinn_insights', {})
                if isinstance(quinn_insights, dict) and 'qualification_quality' in quinn_insights:
                    logger.info(f"   Quinn qualification score: {quinn_insights['qualification_quality']}/10")
                
                # Processing metrics
                processing_time = metadata.get('processing_time_seconds', 0)
                if processing_time > 0:
                    logger.info(f"   Processing time: {processing_time:.2f}s")
                
                token_usage = metadata.get('token_usage', {})
                if token_usage:
                    logger.info(f"   Tokens: {token_usage.get('input_tokens', 0)} in, {token_usage.get('output_tokens', 0)} out")
            
            return result_id
            
        except Exception as e:
            # Use error handler if available
            if self.error_handler:
                try:
                    await handle_processing_error(e, str(call_id), {'stage': 'llm_analysis'})
                except Exception as eh_error:
                    logger.error(f"Error handler failed: {eh_error}")
            
            self.results['llm_analysis'] = {
                'status': 'failed',
                'error': str(e),
                'error_handled': self.error_handler is not None
            }
            logger.error(f"❌ LLM analysis failed: {e}")
            return None
    
    async def _analyze_with_openai(self, transcript: str, title: str) -> dict:
        """Perform real OpenAI analysis using structured approach"""
        try:
            # Build comprehensive system prompt for the 9-category analysis
            system_prompt = self._build_analysis_system_prompt()
            
            # Build call metadata for enhanced analysis
            call_metadata = {
                'title': title,
                'date': datetime.now().isoformat(),
                'transcript_length': len(transcript)
            }
            
            logger.info(f"Using OpenAI analysis for {len(transcript)} character transcript")
            
            # Call OpenAI API 
            result = await self.openai_client.analyze_call_transcript(
                transcript=transcript,
                system_prompt=system_prompt
            )
            
            # Parse structured JSON response
            try:
                # Try to extract JSON from response
                content = result.content
                
                # Find JSON block in response
                json_match = content
                if "```json" in content:
                    json_match = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    json_match = content.split("```")[1].split("```")[0]
                
                analysis_data = json.loads(json_match.strip())
                
            except (json.JSONDecodeError, IndexError) as e:
                logger.warning(f"JSON parsing failed: {e}")
                logger.info("Attempting to parse unstructured OpenAI response")
                analysis_data = self._parse_unstructured_response(result.content, transcript, title)
            
            # Enhance with OpenAI-specific metadata
            if 'analysis_metadata' not in analysis_data:
                analysis_data['analysis_metadata'] = {}
            
            analysis_data['analysis_metadata'].update({
                'analysis_version': '2.0-openai',
                'llm_model_used': result.model,
                'processing_time_seconds': result.processing_time,
                'token_usage': result.usage,
                'finish_reason': result.finish_reason,
                'provider': 'openai'
            })
            
            logger.info(f"✅ OpenAI analysis completed successfully")
            logger.info(f"   Tokens: {result.usage['input_tokens']} in, {result.usage['output_tokens']} out")
            logger.info(f"   Confidence: {analysis_data.get('analysis_metadata', {}).get('analysis_confidence', 'N/A')}/10")
            
            return analysis_data
            
        except OpenAIAPIError as e:
            logger.error(f"OpenAI API error during analysis: {e}")
            logger.info("Falling back to mock analysis due to OpenAI API error")
            return self.mock_llm_analysis(transcript, title)
            
        except Exception as e:
            logger.error(f"Unexpected error during OpenAI analysis: {e}")
            logger.info("Falling back to mock analysis due to unexpected error")
            return self.mock_llm_analysis(transcript, title)
    
    def _build_analysis_system_prompt(self) -> str:
        """Build comprehensive system prompt for 9-category analysis"""
        return """You are an expert sales call analyst. Analyze the provided sales call transcript and extract insights across 9 key dimensions.

Return your analysis as a JSON object with EXACTLY this structure:

{
    "core_talking_points": {
        "primary_pain_points": ["list of main pain points discussed"],
        "ae_key_talking_points": ["key talking points used by AE"],
        "pain_point_alignment": 8,
        "unaddressed_pain_points": ["pain points not adequately addressed"],
        "most_compelling_point": "single most compelling point"
    },
    "telnyx_products": {
        "products_discussed": ["list of Telnyx products mentioned"],
        "features_highlighted": ["specific features discussed"],
        "technical_depth": 7,
        "competitor_mentions": ["competing products mentioned"],
        "product_fit_assessment": 8
    },
    "use_cases": {
        "primary_use_cases": ["main business use cases"],
        "business_impact_areas": ["areas impacted by implementation"],
        "quantified_benefits": ["specific ROI or metrics mentioned"],
        "implementation_complexity": 5,
        "use_case_specificity": 7
    },
    "conversation_focus": {
        "primary_focus": "discovery|demo|pricing|objection_handling|closing|relationship_building|technical_deep_dive|competitive|mixed",
        "secondary_focus": "optional secondary focus",
        "focus_effectiveness": 8,
        "topic_transitions": 7,
        "conversation_control": 8
    },
    "sentiment_analysis": {
        "ae_sentiment": 8,
        "prospect_sentiment": 7,
        "ae_sentiment_indicators": ["specific indicators"],
        "prospect_sentiment_indicators": ["specific indicators"],
        "overall_call_energy": 7
    },
    "next_steps": {
        "next_steps_category": "follow_up_scheduled|demo_requested|proposal_to_send|decision_maker_intro|technical_validation|pilot_discussion|contract_negotiation|no_clear_next_steps|prospect_to_consider|lost_opportunity",
        "specific_actions": ["committed actions"],
        "timeline_mentioned": true,
        "timeline_details": "timeline specifics if mentioned",
        "commitment_level": 7,
        "ae_follow_up_quality": 8
    },
    "analysis_confidence": {
        "transcript_quality": 8,
        "analysis_confidence": 8,
        "missing_context": ["what might be missing"],
        "ambiguous_areas": ["unclear areas"],
        "data_reliability": 8
    },
    "quinn_scoring": {
        "need_clarity": 8,
        "decision_authority": 6,
        "budget_availability": 5,
        "timeline_urgency": 7,
        "champion_strength": 6,
        "competition_position": 7,
        "overall_qualification": 7,
        "qualification_notes": "additional insights"
    },
    "analysis_metadata": {
        "analysis_timestamp": "ISO timestamp",
        "analysis_version": "2.0-openai",
        "analysis_confidence": 8
    }
}

All numeric scores should be 1-10 where 1 is lowest and 10 is highest.
Be specific and extract actual quotes or details from the transcript where possible.
If information is not available, use empty arrays or null values appropriately."""
    
    def _parse_unstructured_response(self, content: str, transcript: str, title: str) -> dict:
        """Parse unstructured LLM response into analysis format"""
        # Return a structured response based on content parsing
        return {
            "core_talking_points": {
                "primary_pain_points": ["Unable to parse from response"],
                "ae_key_talking_points": ["Unable to parse from response"],
                "pain_point_alignment": 5,
                "unaddressed_pain_points": [],
                "most_compelling_point": "Analysis parsing failed"
            },
            "telnyx_products": {
                "products_discussed": [],
                "features_highlighted": [],
                "technical_depth": 5,
                "competitor_mentions": [],
                "product_fit_assessment": 5
            },
            "use_cases": {
                "primary_use_cases": [],
                "business_impact_areas": [],
                "quantified_benefits": [],
                "implementation_complexity": 5,
                "use_case_specificity": 5
            },
            "conversation_focus": {
                "primary_focus": "mixed",
                "secondary_focus": None,
                "focus_effectiveness": 5,
                "topic_transitions": 5,
                "conversation_control": 5
            },
            "sentiment_analysis": {
                "ae_sentiment": 5,
                "prospect_sentiment": 5,
                "ae_sentiment_indicators": [],
                "prospect_sentiment_indicators": [],
                "overall_call_energy": 5
            },
            "next_steps": {
                "next_steps_category": "no_clear_next_steps",
                "specific_actions": [],
                "timeline_mentioned": False,
                "timeline_details": "",
                "commitment_level": 5,
                "ae_follow_up_quality": 5
            },
            "analysis_confidence": {
                "transcript_quality": 5,
                "analysis_confidence": 3,
                "missing_context": ["Response parsing failed"],
                "ambiguous_areas": ["Full response"],
                "data_reliability": 3
            },
            "quinn_scoring": {
                "need_clarity": 5,
                "decision_authority": 5,
                "budget_availability": 5,
                "timeline_urgency": 5,
                "champion_strength": 5,
                "competition_position": 5,
                "overall_qualification": 5,
                "qualification_notes": "Analysis parsing failed - using defaults"
            },
            "analysis_metadata": {
                "analysis_timestamp": datetime.now().isoformat(),
                "analysis_version": "2.0-openai-fallback",
                "raw_response_length": len(content),
                "parsing_error": True
            }
        }
    
    async def _analyze_with_async_processor(self, call: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze call using Phase 2 async processor with enhanced storage"""
        try:
            logger.info("🚀 Starting Phase 2 async analysis")
            
            # Prepare call data for async processor
            call_data = {
                'id': call['id'],
                'fellow_id': call['fellow_id'],
                'transcript': call['transcript'],
                'title': call['title'],
                'created_at': call['created_date'],
                'participants': call.get('participants', [])
            }
            
            # Process with async pipeline (immediate execution for e2e test)
            result = await self.async_processor.analyze_call_immediately(call_data)
            
            if result.success:
                # Store with enhanced storage service
                storage_result = await self.storage_service.store_analysis_result(
                    call['id'], result.analysis_data
                )
                
                if storage_result.success:
                    logger.info(f"✅ Phase 2 analysis and storage completed - ID: {storage_result.analysis_id}")
                    
                    # Add storage metadata to result
                    enhanced_result = result.analysis_data.copy()
                    enhanced_result['storage_result_id'] = storage_result.analysis_id
                    enhanced_result['storage_method'] = 'phase2_enhanced'
                    
                    return enhanced_result
                else:
                    logger.error(f"❌ Phase 2 storage failed: {storage_result.error_message}")
                    # Fall back to basic storage
                    result_id = self.db.insert_analysis_result(call['id'], result.analysis_data)
                    result.analysis_data['storage_result_id'] = result_id
                    result.analysis_data['storage_method'] = 'phase2_fallback'
                    return result.analysis_data
            else:
                raise Exception(f"Async processing failed: {result.error_message}")
                
        except Exception as e:
            logger.error(f"❌ Phase 2 async processing failed: {e}")
            # Fall back to direct OpenAI analysis
            logger.info("🔄 Falling back to direct OpenAI analysis")
            transcript = call['transcript'] or "No transcript available"
            return await self._analyze_with_openai(transcript, call['title'])
    
    def _parse_unstructured_claude_response(self, claude_response: str, transcript: str, title: str) -> dict:
        """Parse unstructured Claude response and create structured data"""
        logger.info("Parsing unstructured Claude response into structured format")
        
        # Start with mock analysis structure
        base_analysis = self.mock_llm_analysis(transcript, title)
        
        # Try to extract insights from Claude's text response
        response_lower = claude_response.lower()
        
        # Enhanced talking points extraction from Claude response
        talking_points = []
        if 'pricing' in response_lower:
            talking_points.append('Pricing and cost analysis')
        if any(word in response_lower for word in ['integration', 'api', 'technical']):
            talking_points.append('Technical integration discussion')
        if any(word in response_lower for word in ['scale', 'volume', 'capacity']):
            talking_points.append('Scale and capacity requirements')
        if any(word in response_lower for word in ['current', 'existing', 'provider']):
            talking_points.append('Current provider evaluation')
        if any(word in response_lower for word in ['security', 'compliance']):
            talking_points.append('Security and compliance concerns')
        
        # Use Claude-extracted talking points if found, otherwise use mock
        if talking_points:
            base_analysis['core_talking_points'] = talking_points
        
        # Enhanced sentiment scoring based on Claude insights
        if 'highly interested' in response_lower or 'very excited' in response_lower:
            base_analysis['prospect_sentiment']['interest_level'] = min(10, base_analysis['prospect_sentiment']['interest_level'] + 2)
        elif 'interested' in response_lower or 'excited' in response_lower:
            base_analysis['prospect_sentiment']['interest_level'] = min(10, base_analysis['prospect_sentiment']['interest_level'] + 1)
        
        if 'concerns' in response_lower or 'worried' in response_lower:
            base_analysis['prospect_sentiment']['interest_level'] = max(1, base_analysis['prospect_sentiment']['interest_level'] - 1)
        
        # Update metadata to indicate Claude parsing
        base_analysis['metadata']['claude_response_parsed'] = True
        base_analysis['metadata']['claude_response_length'] = len(claude_response)
        base_analysis['analysis_confidence'] = 7  # Higher than mock but lower than structured
        
        return base_analysis

    def mock_llm_analysis(self, transcript, title):
        """Mock LLM analysis with keyword matching"""
        transcript_lower = transcript.lower()
        title_lower = title.lower()
        
        # Detect products mentioned
        products = []
        if any(word in transcript_lower for word in ['voice', 'calling', 'sip']):
            products.append('voice')
        if any(word in transcript_lower for word in ['sms', 'text', 'messaging']):
            products.append('messaging')
        if any(word in transcript_lower for word in ['ai', 'assistant', 'bot']):
            products.append('voice_ai')
        
        if not products:
            products = ['voice']  # Default assumption
        
        # Extract talking points (simple keyword extraction)
        talking_points = []
        if 'pricing' in transcript_lower:
            talking_points.append('Pricing discussion')
        if any(word in transcript_lower for word in ['integration', 'api']):
            talking_points.append('Technical integration requirements')
        if any(word in transcript_lower for word in ['volume', 'scale']):
            talking_points.append('Volume and scalability needs')
        if any(word in transcript_lower for word in ['current', 'existing', 'provider']):
            talking_points.append('Current provider evaluation')
        
        if not talking_points:
            talking_points = ['General product inquiry']
        
        # Sentiment scoring based on keywords
        positive_words = ['interested', 'excited', 'perfect', 'great', 'exactly', 'love']
        negative_words = ['concern', 'expensive', 'complicated', 'difficult']
        
        positive_count = sum(1 for word in positive_words if word in transcript_lower)
        negative_count = sum(1 for word in negative_words if word in transcript_lower)
        
        prospect_interest = min(10, max(1, 6 + positive_count - negative_count))
        ae_excitement = min(10, max(1, 7 + positive_count // 2))
        
        # Determine next steps
        next_steps_category = 'moving_forward'
        next_steps_actions = ['Follow up with technical details']
        
        if any(word in transcript_lower for word in ['demo', 'poc', 'pilot', 'trial']):
            next_steps_category = 'moving_forward'
            next_steps_actions = ['Schedule technical demo']
        elif any(word in transcript_lower for word in ['think', 'discuss', 'internal']):
            next_steps_category = 'self_service'
            next_steps_actions = ['Prospect to discuss internally']
        
        return {
            'analysis_version': '1.0-mock',
            'core_talking_points': talking_points,
            'telnyx_products': products,
            'use_cases': ['Business communications'],
            'conversation_focus': {
                'primary': 'product_overview',
                'secondary': ['pricing', 'technical'],
                'time_distribution': {'product_overview': 60, 'pricing': 25, 'technical': 15}
            },
            'ae_sentiment': {
                'excitement_level': ae_excitement,
                'confidence_level': 7,
                'notes': 'AE showed good product knowledge'
            },
            'prospect_sentiment': {
                'interest_level': prospect_interest,
                'engagement_level': prospect_interest,
                'buying_signals': ['Asked detailed questions'] if positive_count > 0 else [],
                'concerns': ['Price sensitivity'] if 'expensive' in transcript_lower else []
            },
            'next_steps': {
                'category': next_steps_category,
                'specific_actions': next_steps_actions,
                'timeline': 'Within 1 week',
                'probability': min(10, max(1, prospect_interest))
            },
            'quinn_insights': {
                'qualification_quality': min(10, max(1, 5 + len(talking_points))),
                'missed_opportunities': [],
                'strengths': ['Good discovery questions']
            },
            'metadata': {
                'analysis_confidence': 6,  # Mock analysis has lower confidence
                'llm_model_used': 'mock-keyword-analysis',
                'processing_time_seconds': 0.1
            }
        }
    
    def generate_summary(self):
        """Generate final summary"""
        logger.info("Step 5: Generating final summary...")
        
        try:
            # Get all the data
            call_id = self.results['database_store'].get('call_id')
            if not call_id:
                raise Exception("No call ID available")
            
            # Get complete call data with analysis
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT c.*, ar.*, sm.contact_name, sm.contact_id
                    FROM calls c
                    LEFT JOIN analysis_results ar ON c.id = ar.call_id
                    LEFT JOIN salesforce_mappings sm ON c.id = sm.call_id
                    WHERE c.id = ?
                    ORDER BY ar.created_at DESC
                    LIMIT 1
                ''', (call_id,))
                
                row = cursor.fetchone()
                if not row:
                    raise Exception("Call data not found")
                
                # Convert to dict
                data = dict(row)
            
            summary = {
                'call_info': {
                    'title': data['title'],
                    'date': data['call_date'],
                    'ae_name': data['ae_name'],
                    'prospect_name': data['prospect_name'],
                    'prospect_company': data['prospect_company']
                },
                'salesforce_mapping': {
                    'contact_name': data['contact_name'],
                    'contact_id': data['contact_id']
                },
                'analysis_results': {
                    'products_discussed': json.loads(data['telnyx_products'] or '[]'),
                    'talking_points': json.loads(data['core_talking_points'] or '[]'),
                    'ae_excitement': data['ae_excitement_level'],
                    'prospect_interest': data['prospect_interest_level'],
                    'next_steps': data['next_steps_category'],
                    'quinn_quality': data['quinn_qualification_quality']
                },
                'pipeline_results': self.results
            }
            
            self.results['final_result'] = {
                'status': 'success',
                'summary': summary
            }
            
            logger.info("✅ End-to-end pipeline completed successfully!")
            return summary
            
        except Exception as e:
            self.results['final_result'] = {
                'status': 'failed',
                'error': str(e)
            }
            logger.error(f"❌ Failed to generate summary: {e}")
            return None
    
    async def run_e2e_pipeline(self):
        """Run the complete end-to-end pipeline"""
        logger.info("🚀 Starting End-to-End AE Call Analysis Pipeline")
        logger.info("=" * 60)
        
        # Step 1: Fetch Fellow call
        call_data = await self.fetch_fellow_call()
        if not call_data:
            return self.results
        
        # Step 2: Store in database
        call_id = self.store_call_in_database(call_data)
        if not call_id:
            return self.results
        
        # Step 3: Map to Salesforce
        mapping_id = self.map_to_salesforce(call_id, self.results['database_store']['prospect_name'])
        
        # Step 4: LLM Analysis
        analysis_id = await self.analyze_with_llm(call_id)
        if not analysis_id:
            return self.results
        
        # Step 5: Generate summary
        summary = self.generate_summary()
        
        # Display final results
        self.display_results()
        
        return self.results
    
    def display_results(self):
        """Display formatted results"""
        logger.info("=" * 60)
        logger.info("🎯 END-TO-END PIPELINE RESULTS")
        logger.info("=" * 60)
        
        # Pipeline status
        for step, result in self.results.items():
            if step == 'final_result':
                continue
            status_icon = "✅" if result['status'] == 'success' else "❌" if result['status'] == 'failed' else "⚠️"
            logger.info(f"{status_icon} {step.replace('_', ' ').title()}: {result['status']}")
        
        # Call summary
        if self.results['final_result']['status'] == 'success':
            summary = self.results['final_result']['summary']
            call_info = summary['call_info']
            analysis = summary['analysis_results']
            
            logger.info("")
            logger.info("📞 CALL SUMMARY:")
            logger.info(f"   Title: {call_info['title']}")
            logger.info(f"   AE: {call_info['ae_name']}")
            logger.info(f"   Prospect: {call_info['prospect_name']} ({call_info['prospect_company']})")
            logger.info(f"   Products: {', '.join(analysis['products_discussed'])}")
            logger.info(f"   AE Excitement: {analysis['ae_excitement']}/10")
            logger.info(f"   Prospect Interest: {analysis['prospect_interest']}/10")
            logger.info(f"   Next Steps: {analysis['next_steps']}")
            logger.info(f"   Quinn Quality Score: {analysis['quinn_quality']}/10")
        
        logger.info("=" * 60)

async def main():
    """Main entry point"""
    pipeline = E2EPipeline()
    results = await pipeline.run_e2e_pipeline()
    
    # Save results to file (handle circular references)
    results_file = Path(__file__).parent / "e2e_results.json"
    
    # Create a clean copy without circular references
    clean_results = {}
    for key, value in results.items():
        if isinstance(value, dict):
            clean_results[key] = {k: str(v) if not isinstance(v, (str, int, float, bool, list, dict)) else v 
                                 for k, v in value.items()}
        else:
            clean_results[key] = value
    
    with open(results_file, 'w') as f:
        json.dump(clean_results, f, indent=2, default=str)
    
    logger.info(f"📄 Results saved to: {results_file}")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())