#!/usr/bin/env python3
"""
Test script for Hybrid Authentication System

Verifies that the AE Call Analysis system can:
1. Detect and use direct API keys (production mode)
2. Fall back to Clawdbot OAuth (development mode)
3. Fall back to Claude CLI OAuth (development mode)
4. Report auth mode correctly
"""

import os
import sys
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import (
    AECallAnalysisConfig, 
    get_best_claude_token, 
    get_clawdbot_auth_token,
    get_claude_cli_auth_token,
    ClaudeConfig,
    AuthResult
)
from services.claude_client import ClaudeClient


def test_auth_detection():
    """Test that authentication sources are detected correctly"""
    print("\n" + "=" * 60)
    print("TEST: Authentication Source Detection")
    print("=" * 60)
    
    # Test individual auth sources
    print("\n1. Checking environment variables...")
    env_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if env_key:
        print(f"   ✅ Found: ${('CLAUDE_API_KEY' if os.getenv('CLAUDE_API_KEY') else 'ANTHROPIC_API_KEY')}")
        print(f"   Prefix: {env_key[:15]}...")
    else:
        print("   ⚪ Not set (will try fallback methods)")
    
    print("\n2. Checking Claude CLI credentials...")
    cli_token = get_claude_cli_auth_token()
    if cli_token:
        print(f"   ✅ Found valid OAuth token")
        print(f"   Prefix: {cli_token[:15]}...")
    else:
        print("   ⚪ Not available or expired")
    
    print("\n3. Checking Clawdbot auth profiles...")
    clawdbot_token = get_clawdbot_auth_token()
    if clawdbot_token:
        print(f"   ✅ Found valid token")
        print(f"   Prefix: {clawdbot_token[:15]}...")
    else:
        print("   ⚪ Not available or no valid profiles")
    
    print("\n4. Testing get_best_claude_token()...")
    result = get_best_claude_token()
    print(f"   Mode: {result.mode}")
    print(f"   Source: {result.source}")
    if result.token:
        print(f"   Token prefix: {result.token[:15]}...")
    else:
        print("   Token: None")
    
    return result


def test_config_loading():
    """Test that configuration loads with correct auth mode"""
    print("\n" + "=" * 60)
    print("TEST: Configuration Loading")
    print("=" * 60)
    
    config = AECallAnalysisConfig()
    
    print(f"\nClaude Config:")
    print(f"  auth_mode: {config.claude.auth_mode}")
    print(f"  model: {config.claude.model}")
    print(f"  max_tokens: {config.claude.max_tokens}")
    print(f"  has_api_key: {bool(config.claude.api_key)}")
    
    return config


async def test_client_initialization(config: AECallAnalysisConfig):
    """Test Claude client initialization and connection"""
    print("\n" + "=" * 60)
    print("TEST: Claude Client Initialization")
    print("=" * 60)
    
    if not config.claude.api_key:
        print("\n⚠️ No authentication available - skipping client test")
        return None
    
    try:
        client = ClaudeClient(config.claude)
        
        print("\n✅ Client initialized successfully")
        
        stats = client.get_stats()
        print(f"\nClient Stats:")
        print(f"  auth_mode: {stats['auth_mode']}")
        print(f"  auth_mode_label: {stats['auth_mode_label']}")
        print(f"  is_production: {stats['is_production']}")
        print(f"  is_development: {stats['is_development']}")
        print(f"  model: {stats['model']}")
        
        return client
        
    except Exception as e:
        print(f"\n❌ Client initialization failed: {e}")
        return None


async def test_connection(client: ClaudeClient):
    """Test actual API connection"""
    print("\n" + "=" * 60)
    print("TEST: API Connection")
    print("=" * 60)
    
    if client is None:
        print("\n⚠️ No client available - skipping connection test")
        return
    
    result = await client.test_connection()
    
    print(f"\nConnection Test Result:")
    print(f"  success: {result['success']}")
    print(f"  auth_mode: {result['auth_mode']}")
    print(f"  model: {result['model']}")
    if result['error']:
        print(f"  error: {result['error']}")


def print_summary(auth_result: AuthResult, config: AECallAnalysisConfig):
    """Print final summary"""
    print("\n" + "=" * 60)
    print("HYBRID AUTHENTICATION SUMMARY")
    print("=" * 60)
    
    mode_icons = {
        "direct": "🔑",
        "clawdbot": "🔐",
        "claude_cli": "🔐", 
        "none": "⚠️"
    }
    
    mode_labels = {
        "direct": "PRODUCTION (Direct API Key)",
        "clawdbot": "DEVELOPMENT (Clawdbot OAuth)",
        "claude_cli": "DEVELOPMENT (Claude CLI OAuth)",
        "none": "NO AUTHENTICATION"
    }
    
    icon = mode_icons.get(auth_result.mode, "❓")
    label = mode_labels.get(auth_result.mode, auth_result.mode)
    
    print(f"\n{icon} Mode: {label}")
    print(f"📍 Source: {auth_result.source}")
    
    if auth_result.mode == "direct":
        print("\n✅ Production-ready configuration")
        print("   Using direct Anthropic API key")
    elif auth_result.mode in ("clawdbot", "claude_cli"):
        print("\n✅ Development configuration")
        print("   Using OAuth token - no console.anthropic.com setup needed!")
        print("   To switch to production: export ANTHROPIC_API_KEY='sk-ant-api03-...'")
    else:
        print("\n❌ No authentication configured")
        print("   See options above to configure authentication")


async def main():
    """Run all hybrid auth tests"""
    print("\n" + "🔧" * 30)
    print("AE CALL ANALYSIS - HYBRID AUTHENTICATION TEST")
    print("🔧" * 30)
    
    # Test 1: Auth detection
    auth_result = test_auth_detection()
    
    # Test 2: Config loading
    config = test_config_loading()
    
    # Test 3: Client initialization
    client = await test_client_initialization(config)
    
    # Test 4: Connection (optional - uses API)
    if client and os.getenv("TEST_CONNECTION", "false").lower() == "true":
        await test_connection(client)
    elif client:
        print("\n💡 Tip: Set TEST_CONNECTION=true to test actual API connection")
    
    # Summary
    print_summary(auth_result, config)
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
