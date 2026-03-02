"""
Configuration settings for AE Call Analysis System
Loads settings from environment variables with sensible defaults

Supports Clawdbot OAuth integration for Claude API access.
"""

import os
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

def get_claude_cli_auth_token() -> Optional[str]:
    """
    Read OAuth token from Claude CLI credentials (~/.claude/.credentials.json).
    
    The Claude CLI (claude code) stores fresh OAuth tokens that are regularly
    refreshed during interactive use.
    
    Returns:
        str: OAuth access token or None if not found/expired
    """
    import time
    
    credentials_path = Path.home() / ".claude" / ".credentials.json"
    
    if not credentials_path.exists():
        logger.debug("Claude CLI credentials not found")
        return None
    
    try:
        with open(credentials_path, 'r') as f:
            creds = json.load(f)
        
        oauth = creds.get('claudeAiOauth', {})
        access_token = oauth.get('accessToken')
        expires_at = oauth.get('expiresAt', 0)
        current_time_ms = int(time.time() * 1000)
        
        if access_token and expires_at > current_time_ms:
            days_remaining = (expires_at - current_time_ms) // 86400000
            logger.info(f"✅ Found valid Claude CLI OAuth token (expires in {days_remaining} days)")
            return access_token
        elif access_token:
            logger.debug("Claude CLI token found but expired")
        
        return None
        
    except Exception as e:
        logger.debug(f"Error reading Claude CLI credentials: {e}")
        return None


def get_clawdbot_auth_token() -> Optional[str]:
    """
    Read Claude API token from Clawdbot's auth profiles.
    
    Looks for OAuth/token auth in ~/.clawdbot/agents/main/agent/auth-profiles.json
    Prioritizes OAuth tokens with valid expiry over simple tokens.
    
    Returns:
        str: OAuth access token (sk-ant-oat01-...) or None if not found
    """
    import time
    
    # Standard Clawdbot auth profile path
    auth_profile_path = Path.home() / ".clawdbot" / "agents" / "main" / "agent" / "auth-profiles.json"
    
    # Also check environment variable for custom path
    custom_path = os.getenv("CLAWDBOT_AUTH_PROFILES_PATH")
    if custom_path:
        auth_profile_path = Path(custom_path)
    
    if not auth_profile_path.exists():
        logger.debug(f"Clawdbot auth profiles not found at: {auth_profile_path}")
        return None
    
    try:
        with open(auth_profile_path, 'r') as f:
            auth_data = json.load(f)
        
        profiles = auth_data.get('profiles', {})
        usage_stats = auth_data.get('usageStats', {})
        current_time_ms = int(time.time() * 1000)
        
        # Strategy: Find the best valid token
        # Priority: OAuth with valid expiry > lastGood > any token
        
        best_token = None
        best_profile_name = None
        
        # First pass: Look for OAuth tokens with valid expiry
        for profile_name, profile in profiles.items():
            if 'anthropic' not in profile_name.lower():
                continue
            
            if profile.get('type') == 'oauth':
                expires = profile.get('expires', 0)
                access_token = profile.get('access')
                
                if access_token and expires > current_time_ms:
                    # Valid OAuth token with future expiry
                    logger.info(f"✅ Found valid OAuth token: {profile_name} (expires in {(expires - current_time_ms) // 86400000} days)")
                    return access_token
        
        # Second pass: Try lastGood profile
        last_good = auth_data.get('lastGood', {})
        preferred_profile_name = last_good.get('anthropic')
        
        if preferred_profile_name and preferred_profile_name in profiles:
            profile = profiles[preferred_profile_name]
            stats = usage_stats.get(preferred_profile_name, {})
            
            # Check if profile has recent auth failures
            last_failure = stats.get('lastFailureAt', 0)
            last_used = stats.get('lastUsed', 0)
            
            # Only use if last use was more recent than last failure
            if last_used >= last_failure:
                if profile.get('type') == 'oauth':
                    token = profile.get('access')
                    if token:
                        logger.info(f"✅ Using Clawdbot OAuth (lastGood): {preferred_profile_name}")
                        return token
                elif profile.get('type') == 'token':
                    token = profile.get('token')
                    if token:
                        logger.info(f"✅ Using Clawdbot token (lastGood): {preferred_profile_name}")
                        return token
        
        # Third pass: Any anthropic profile with a token
        for profile_name, profile in profiles.items():
            if 'anthropic' not in profile_name.lower():
                continue
            
            if profile.get('type') == 'token':
                token = profile.get('token')
                if token:
                    logger.info(f"✅ Using Clawdbot token (fallback): {profile_name}")
                    return token
        
        logger.debug("No valid Anthropic token found in Clawdbot auth profiles")
        return None
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Clawdbot auth profiles: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading Clawdbot auth profiles: {e}")
        return None


@dataclass
class AuthResult:
    """Result of authentication token lookup"""
    token: Optional[str]
    mode: str  # direct | clawdbot | claude_cli | none
    source: str  # Human-readable description


def get_best_claude_token() -> AuthResult:
    """
    Get the best available Claude API token with auth mode tracking.
    
    Priority order:
    1. Environment variable (CLAUDE_API_KEY or ANTHROPIC_API_KEY) → "direct" mode
    2. Claude CLI OAuth token (~/.claude/.credentials.json) → "claude_cli" mode
    3. Clawdbot auth profiles (~/.clawdbot/agents/main/agent/auth-profiles.json) → "clawdbot" mode
    
    Returns:
        AuthResult with token, mode, and source description
    """
    # Priority 1: Direct API key (production mode)
    env_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if env_key:
        source_var = "CLAUDE_API_KEY" if os.getenv("CLAUDE_API_KEY") else "ANTHROPIC_API_KEY"
        logger.info(f"✅ [PRODUCTION] Using direct API key from ${source_var}")
        return AuthResult(
            token=env_key,
            mode="direct",
            source=f"Environment variable ${source_var}"
        )
    
    # Priority 2: Claude CLI OAuth (development mode - usually freshest)
    cli_token = get_claude_cli_auth_token()
    if cli_token:
        logger.info("✅ [DEVELOPMENT] Using Claude CLI OAuth token")
        return AuthResult(
            token=cli_token,
            mode="claude_cli",
            source="Claude CLI (~/.claude/.credentials.json)"
        )
    
    # Priority 3: Clawdbot OAuth (development mode)
    clawdbot_token = get_clawdbot_auth_token()
    if clawdbot_token:
        logger.info("✅ [DEVELOPMENT] Using Clawdbot OAuth token")
        return AuthResult(
            token=clawdbot_token,
            mode="clawdbot",
            source="Clawdbot auth profiles (~/.clawdbot/agents/main/agent/auth-profiles.json)"
        )
    
    # No auth available
    logger.warning("⚠️ No Claude API token found from any source")
    logger.warning("   Options:")
    logger.warning("   1. Set ANTHROPIC_API_KEY environment variable (production)")
    logger.warning("   2. Run 'claude auth login' to authenticate Claude CLI (development)")
    logger.warning("   3. Configure Clawdbot OAuth profiles (development)")
    return AuthResult(
        token=None,
        mode="none",
        source="No authentication configured"
    )


@dataclass
class DatabaseConfig:
    """Database configuration"""
    path: str = "ae_call_analysis.db"
    backup_retention_days: int = 30
    cleanup_interval_hours: int = 24

@dataclass
class FellowAPIConfig:
    """Fellow.app API configuration"""
    api_key: str = ""  # Set via FELLOW_API_KEY environment variable
    endpoint: str = "https://telnyx.fellow.app/api/v1/recordings"
    timeout_seconds: int = 30
    rate_limit_per_minute: int = 100
    retry_attempts: int = 3
    retry_delay_seconds: int = 5

@dataclass
class SalesforceConfig:
    """Salesforce integration configuration"""
    org_username: str = "niamh@telnyx.com"
    contact_search_limit: int = 10
    quinn_field_name: str = "D_T_Quinn_Active_Latest__c"
    quinn_user_name: str = "Quinn Taylor"
    timeout_seconds: int = 30
    validate_quinn_field_on_startup: bool = True

@dataclass
class ClaudeConfig:
    """Claude API configuration for call analysis
    
    Supports three authentication modes:
    - "direct": Production API key from environment variable
    - "clawdbot": Development OAuth via Clawdbot auth profiles
    - "claude_cli": Development OAuth via Claude CLI credentials
    - "none": No authentication available
    """
    api_key: str = ""
    model: str = "claude-3-sonnet-20241022"  
    max_tokens: int = 4000
    temperature: float = 0.1
    timeout: float = 60.0
    max_retries: int = 3
    auth_mode: str = "none"  # direct | clawdbot | claude_cli | none


@dataclass
class TokenLimitsConfig:
    """Token limits configuration for context overflow prevention
    
    These settings control the bulletproof context overflow protection system.
    """
    # Safety margin - what percentage of context window to use (0.95 = 95%)
    safety_margin: float = 0.95
    
    # Minimum tokens to reserve for response
    min_output_reserve: int = 2000
    
    # Token buffer for message overhead
    overhead_buffer: int = 500
    
    # Enable automatic truncation when over limit
    auto_truncate: bool = True
    
    # Default truncation strategy: simple, smart_sections, speaker_aware, keyword_preserve
    truncation_strategy: str = "smart_sections"
    
    # Enable Claude fallback for very large transcripts
    enable_claude_fallback: bool = True
    
    # Log detailed token usage
    log_token_usage: bool = True
    
    # Alert threshold - warn when using more than this % of context
    alert_threshold: float = 0.85


@dataclass
class OpenAIConfig:
    """OpenAI API configuration for call analysis
    
    Uses OPENAI_API_KEY from environment variable.
    Recommended for users with OpenAI Pro subscriptions.
    
    Now includes bulletproof context overflow protection.
    """
    api_key: str = ""
    model: str = "gpt-4-turbo-preview"  # gpt-4, gpt-4-turbo, gpt-4o
    max_tokens: int = 4000
    temperature: float = 0.1
    timeout: float = 60.0
    max_retries: int = 3
    
    # Context overflow protection settings
    context_safety_margin: float = 0.95  # Use 95% of available context
    auto_truncate: bool = True           # Automatically truncate large transcripts
    enable_fallback: bool = True         # Enable Claude fallback for very large transcripts

@dataclass
class LLMConfig:
    """Language model configuration (legacy - kept for backwards compatibility)"""
    provider: str = "anthropic"  # openai, anthropic, local
    model: str = "claude-3-sonnet-20241022"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4000
    timeout_seconds: int = 60

@dataclass
class SlackConfig:
    """Slack integration configuration"""
    webhook_url: Optional[str] = None
    channel: str = "#ae-call-analysis"  # Default channel
    bot_token: Optional[str] = None
    enable_threading: bool = True
    daily_digest_time: str = "09:00"  # 9 AM CST

@dataclass
class ProcessingConfig:
    """Data processing configuration"""
    batch_size: int = 10
    max_concurrent_operations: int = 5
    analysis_timeout_seconds: int = 180
    enable_auto_processing: bool = True
    schedule_interval_minutes: int = 30

@dataclass
class QuinnLearningConfig:
    """Quinn learning system configuration"""
    enable_feedback_collection: bool = True
    minimum_confidence_threshold: float = 0.7
    retraining_sample_threshold: int = 50
    feedback_weight_multiplier: float = 1.5

class AECallAnalysisConfig:
    """Main configuration class"""
    
    def __init__(self):
        # Project paths
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / "data"
        self.logs_dir = self.project_root / "logs"
        
        # Create directories
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
        # Load configurations
        self.database = self._load_database_config()
        self.fellow_api = self._load_fellow_config()
        self.salesforce = self._load_salesforce_config()
        self.claude = self._load_claude_config()
        self.openai = self._load_openai_config()
        self.token_limits = self._load_token_limits_config()  # NEW: Token limits config
        self.llm = self._load_llm_config()
        self.slack = self._load_slack_config()
        self.processing = self._load_processing_config()
        self.quinn_learning = self._load_quinn_learning_config()
        
        # Environment
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration"""
        db_path = os.getenv("AE_DB_PATH", str(self.data_dir / "ae_call_analysis.db"))
        
        return DatabaseConfig(
            path=db_path,
            backup_retention_days=int(os.getenv("AE_DB_RETENTION_DAYS", "30")),
            cleanup_interval_hours=int(os.getenv("AE_DB_CLEANUP_HOURS", "24"))
        )
    
    def _load_fellow_config(self) -> FellowAPIConfig:
        """Load Fellow API configuration"""
        # Use the API key we found in the existing system
        api_key = os.getenv("FELLOW_API_KEY")
        
        return FellowAPIConfig(
            api_key=api_key,
            endpoint=os.getenv("FELLOW_ENDPOINT", "https://telnyx.fellow.app/api/v1/recordings"),
            timeout_seconds=int(os.getenv("FELLOW_TIMEOUT", "30")),
            rate_limit_per_minute=int(os.getenv("FELLOW_RATE_LIMIT", "100")),
            retry_attempts=int(os.getenv("FELLOW_RETRY_ATTEMPTS", "3")),
            retry_delay_seconds=int(os.getenv("FELLOW_RETRY_DELAY", "5"))
        )
    
    def _load_salesforce_config(self) -> SalesforceConfig:
        """Load Salesforce configuration"""
        return SalesforceConfig(
            org_username=os.getenv("SF_USERNAME", "niamh@telnyx.com"),
            contact_search_limit=int(os.getenv("SF_CONTACT_LIMIT", "10")),
            quinn_field_name=os.getenv("SF_QUINN_FIELD", "D_T_Quinn_Active_Latest__c"),
            quinn_user_name=os.getenv("SF_QUINN_USER_NAME", "Quinn Taylor"),
            timeout_seconds=int(os.getenv("SF_TIMEOUT", "30")),
            validate_quinn_field_on_startup=os.getenv("SF_VALIDATE_QUINN_STARTUP", "true").lower() == "true"
        )
    
    def _load_claude_config(self) -> ClaudeConfig:
        """
        Load Claude API configuration with hybrid authentication.
        
        Authentication modes:
        - PRODUCTION: Set ANTHROPIC_API_KEY or CLAUDE_API_KEY → "direct" mode
        - DEVELOPMENT: Clawdbot/Claude CLI OAuth → "clawdbot" or "claude_cli" mode
        
        This hybrid approach allows:
        - Production deployments with direct API keys
        - Development without console.anthropic.com setup (uses existing OAuth)
        - Team flexibility (each dev chooses their preferred method)
        """
        auth_result = get_best_claude_token()
        
        # Log authentication mode clearly
        if auth_result.mode == "direct":
            logger.info("━" * 50)
            logger.info("🔑 CLAUDE AUTH: PRODUCTION MODE")
            logger.info(f"   Source: {auth_result.source}")
            logger.info("━" * 50)
        elif auth_result.mode in ("clawdbot", "claude_cli"):
            logger.info("━" * 50)
            logger.info("🔐 CLAUDE AUTH: DEVELOPMENT MODE")
            logger.info(f"   Method: {auth_result.mode}")
            logger.info(f"   Source: {auth_result.source}")
            logger.info("   Note: OAuth token - no API key needed!")
            logger.info("━" * 50)
        else:
            logger.warning("━" * 50)
            logger.warning("⚠️ CLAUDE AUTH: NO AUTHENTICATION")
            logger.warning("   Analysis features will be unavailable")
            logger.warning("━" * 50)
        
        return ClaudeConfig(
            api_key=auth_result.token or "",
            model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
            max_tokens=int(os.getenv("CLAUDE_MAX_TOKENS", "4000")),
            temperature=float(os.getenv("CLAUDE_TEMPERATURE", "0.1")),
            timeout=float(os.getenv("CLAUDE_TIMEOUT", "60.0")),
            max_retries=int(os.getenv("CLAUDE_MAX_RETRIES", "3")),
            auth_mode=auth_result.mode
        )
    
    def _load_openai_config(self) -> OpenAIConfig:
        """
        Load OpenAI API configuration from environment.
        
        Recommended for users with OpenAI Pro subscriptions who want
        to bypass Anthropic authentication complexity.
        
        Now includes bulletproof context overflow protection settings.
        """
        api_key = os.getenv("OPENAI_API_KEY", "")
        
        if api_key:
            logger.info("━" * 50)
            logger.info("🤖 OPENAI: API KEY CONFIGURED")
            logger.info(f"   Key prefix: {api_key[:10]}...")
            logger.info("   Context overflow protection: ENABLED")
            logger.info("━" * 50)
        else:
            logger.info("━" * 50)
            logger.info("⚠️ OPENAI: NO API KEY")
            logger.info("   Set OPENAI_API_KEY to enable OpenAI analysis")
            logger.info("━" * 50)
        
        return OpenAIConfig(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4000")),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.1")),
            timeout=float(os.getenv("OPENAI_TIMEOUT", "60.0")),
            max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "3")),
            context_safety_margin=float(os.getenv("OPENAI_CONTEXT_SAFETY_MARGIN", "0.95")),
            auto_truncate=os.getenv("OPENAI_AUTO_TRUNCATE", "true").lower() == "true",
            enable_fallback=os.getenv("OPENAI_ENABLE_FALLBACK", "true").lower() == "true"
        )
    
    def _load_token_limits_config(self) -> TokenLimitsConfig:
        """
        Load token limits configuration for context overflow prevention.
        
        These settings control the bulletproof protection system that prevents
        "Context overflow: prompt too large" errors.
        """
        return TokenLimitsConfig(
            safety_margin=float(os.getenv("TOKEN_SAFETY_MARGIN", "0.95")),
            min_output_reserve=int(os.getenv("TOKEN_MIN_OUTPUT_RESERVE", "2000")),
            overhead_buffer=int(os.getenv("TOKEN_OVERHEAD_BUFFER", "500")),
            auto_truncate=os.getenv("TOKEN_AUTO_TRUNCATE", "true").lower() == "true",
            truncation_strategy=os.getenv("TOKEN_TRUNCATION_STRATEGY", "smart_sections"),
            enable_claude_fallback=os.getenv("TOKEN_ENABLE_CLAUDE_FALLBACK", "true").lower() == "true",
            log_token_usage=os.getenv("TOKEN_LOG_USAGE", "true").lower() == "true",
            alert_threshold=float(os.getenv("TOKEN_ALERT_THRESHOLD", "0.85"))
        )
    
    def _load_llm_config(self) -> LLMConfig:
        """Load LLM configuration"""
        return LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "openai"),
            model=os.getenv("LLM_MODEL", "gpt-4"),
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000")),
            timeout_seconds=int(os.getenv("LLM_TIMEOUT", "120"))
        )
    
    def _load_slack_config(self) -> SlackConfig:
        """Load Slack configuration"""
        return SlackConfig(
            webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
            channel=os.getenv("SLACK_CHANNEL", "#ae-call-analysis"),
            bot_token=os.getenv("SLACK_BOT_TOKEN"),
            enable_threading=os.getenv("SLACK_THREADING", "true").lower() == "true",
            daily_digest_time=os.getenv("SLACK_DIGEST_TIME", "09:00")
        )
    
    def _load_processing_config(self) -> ProcessingConfig:
        """Load processing configuration"""
        return ProcessingConfig(
            batch_size=int(os.getenv("PROCESSING_BATCH_SIZE", "10")),
            max_concurrent_operations=int(os.getenv("PROCESSING_MAX_CONCURRENT", "5")),
            analysis_timeout_seconds=int(os.getenv("PROCESSING_ANALYSIS_TIMEOUT", "180")),
            enable_auto_processing=os.getenv("PROCESSING_AUTO_ENABLE", "true").lower() == "true",
            schedule_interval_minutes=int(os.getenv("PROCESSING_SCHEDULE_MINUTES", "30"))
        )
    
    def _load_quinn_learning_config(self) -> QuinnLearningConfig:
        """Load Quinn learning configuration"""
        return QuinnLearningConfig(
            enable_feedback_collection=os.getenv("QUINN_FEEDBACK_ENABLE", "true").lower() == "true",
            minimum_confidence_threshold=float(os.getenv("QUINN_CONFIDENCE_THRESHOLD", "0.7")),
            retraining_sample_threshold=int(os.getenv("QUINN_RETRAIN_THRESHOLD", "50")),
            feedback_weight_multiplier=float(os.getenv("QUINN_FEEDBACK_WEIGHT", "1.5"))
        )
    
    def get_log_config(self) -> dict:
        """Get logging configuration"""
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                },
                "detailed": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "level": self.log_level,
                    "class": "logging.StreamHandler",
                    "formatter": "standard"
                },
                "file": {
                    "level": "INFO",
                    "class": "logging.FileHandler",
                    "filename": str(self.logs_dir / "ae_call_analysis.log"),
                    "formatter": "detailed"
                }
            },
            "loggers": {
                "ae_call_analysis": {
                    "handlers": ["console", "file"],
                    "level": self.log_level,
                    "propagate": False
                }
            }
        }
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Required API keys
        if not self.fellow_api.api_key:
            errors.append("Fellow API key is required")
        
        if not self.claude.api_key:
            errors.append("Claude API key is required for LLM analysis")
        
        if not self.llm.api_key and self.llm.provider in ["openai", "anthropic"]:
            errors.append(f"LLM API key is required for provider: {self.llm.provider}")
        
        # Database path
        if not self.database.path:
            errors.append("Database path is required")
        
        # Salesforce username
        if not self.salesforce.org_username:
            errors.append("Salesforce username is required")
        
        return errors
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary for serialization"""
        return {
            "environment": self.environment,
            "debug": self.debug,
            "log_level": self.log_level,
            "database": {
                "path": self.database.path,
                "backup_retention_days": self.database.backup_retention_days,
                "cleanup_interval_hours": self.database.cleanup_interval_hours
            },
            "fellow_api": {
                "endpoint": self.fellow_api.endpoint,
                "timeout_seconds": self.fellow_api.timeout_seconds,
                "rate_limit_per_minute": self.fellow_api.rate_limit_per_minute,
                "retry_attempts": self.fellow_api.retry_attempts,
                "retry_delay_seconds": self.fellow_api.retry_delay_seconds
                # Note: API key excluded for security
            },
            "salesforce": {
                "org_username": self.salesforce.org_username,
                "contact_search_limit": self.salesforce.contact_search_limit,
                "quinn_field_name": self.salesforce.quinn_field_name,
                "timeout_seconds": self.salesforce.timeout_seconds
            },
            "claude": {
                "model": self.claude.model,
                "max_tokens": self.claude.max_tokens,
                "temperature": self.claude.temperature,
                "timeout": self.claude.timeout,
                "max_retries": self.claude.max_retries
                # Note: API key excluded for security
            },
            "openai": {
                "model": self.openai.model,
                "max_tokens": self.openai.max_tokens,
                "temperature": self.openai.temperature,
                "timeout": self.openai.timeout,
                "max_retries": self.openai.max_retries,
                "context_safety_margin": self.openai.context_safety_margin,
                "auto_truncate": self.openai.auto_truncate,
                "enable_fallback": self.openai.enable_fallback
                # Note: API key excluded for security
            },
            "token_limits": {
                "safety_margin": self.token_limits.safety_margin,
                "min_output_reserve": self.token_limits.min_output_reserve,
                "overhead_buffer": self.token_limits.overhead_buffer,
                "auto_truncate": self.token_limits.auto_truncate,
                "truncation_strategy": self.token_limits.truncation_strategy,
                "enable_claude_fallback": self.token_limits.enable_claude_fallback,
                "log_token_usage": self.token_limits.log_token_usage,
                "alert_threshold": self.token_limits.alert_threshold
            },
            "llm": {
                "provider": self.llm.provider,
                "model": self.llm.model,
                "temperature": self.llm.temperature,
                "max_tokens": self.llm.max_tokens,
                "timeout_seconds": self.llm.timeout_seconds
                # Note: API key excluded for security
            },
            "slack": {
                "channel": self.slack.channel,
                "enable_threading": self.slack.enable_threading,
                "daily_digest_time": self.slack.daily_digest_time
                # Note: Webhook URL and token excluded for security
            },
            "processing": {
                "batch_size": self.processing.batch_size,
                "max_concurrent_operations": self.processing.max_concurrent_operations,
                "analysis_timeout_seconds": self.processing.analysis_timeout_seconds,
                "enable_auto_processing": self.processing.enable_auto_processing,
                "schedule_interval_minutes": self.processing.schedule_interval_minutes
            },
            "quinn_learning": {
                "enable_feedback_collection": self.quinn_learning.enable_feedback_collection,
                "minimum_confidence_threshold": self.quinn_learning.minimum_confidence_threshold,
                "retraining_sample_threshold": self.quinn_learning.retraining_sample_threshold,
                "feedback_weight_multiplier": self.quinn_learning.feedback_weight_multiplier
            }
        }

# Global configuration instance
config = AECallAnalysisConfig()

def get_config() -> AECallAnalysisConfig:
    """Get global configuration instance"""
    return config