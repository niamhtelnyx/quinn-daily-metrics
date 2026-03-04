#!/bin/bash
# Unified Test Framework - Single command for all integration validation
# Usage: ./unified-test-framework.sh [--quick|--full] [--verbose]

set -e

# Configuration
TEST_MODE="quick"
VERBOSE=false
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            TEST_MODE="quick"
            shift
            ;;
        --full)
            TEST_MODE="full"
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Usage: $0 [--quick|--full] [--verbose]"
            exit 1
            ;;
    esac
done

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

error() {
    echo -e "${RED}❌${NC} $1"
}

run_test() {
    local test_name="$1"
    local test_command="$2"
    local required="$3"  # true/false
    
    log "Running: $test_name"
    
    if [ "$VERBOSE" = true ]; then
        echo "Command: $test_command"
    fi
    
    if eval "$test_command" >/dev/null 2>&1; then
        success "$test_name"
        return 0
    else
        if [ "$required" = "true" ]; then
            error "$test_name (REQUIRED)"
            return 1
        else
            warning "$test_name (OPTIONAL)"
            return 0
        fi
    fi
}

main() {
    log "🧪 Starting Unified Test Framework ($TEST_MODE mode)"
    echo ""
    
    local total_tests=0
    local passed_tests=0
    local failed_required=0
    
    # Phase 1: API Health Checks (Always Required)
    log "Phase 1: API Connectivity"
    
    tests=(
        "Salesforce OAuth2|test -n \"$SF_CLIENT_ID\" && test -n \"$SF_CLIENT_SECRET\"|true"
        "OpenAI API|test -n \"$OPENAI_API_KEY\"|false"
        "Fellow API|test -n \"$FELLOW_API_KEY\"|false"
        "Telnyx API|test -n \"$TELNYX_API_KEY\"|false"
    )
    
    for test_def in "${tests[@]}"; do
        IFS='|' read -r name command required <<< "$test_def"
        total_tests=$((total_tests + 1))
        if run_test "$name" "$command" "$required"; then
            passed_tests=$((passed_tests + 1))
        elif [ "$required" = "true" ]; then
            failed_required=$((failed_required + 1))
        fi
    done
    
    echo ""
    
    # Phase 2: Database Tests
    log "Phase 2: Database Connectivity"
    
    db_tests=(
        "SQLite Connection|python3 -c \"import sqlite3; sqlite3.connect(':memory:').execute('SELECT 1')\"|true"
        "Database Path Access|test -w \"\$(dirname \"\${DATABASE_PATH:-./test.db}\")\"|true"
    )
    
    for test_def in "${db_tests[@]}"; do
        IFS='|' read -r name command required <<< "$test_def"
        total_tests=$((total_tests + 1))
        if run_test "$name" "$command" "$required"; then
            passed_tests=$((passed_tests + 1))
        elif [ "$required" = "true" ]; then
            failed_required=$((failed_required + 1))
        fi
    done
    
    echo ""
    
    # Phase 3: Integration Tests (Full mode only)
    if [ "$TEST_MODE" = "full" ]; then
        log "Phase 3: Integration Tests"
        
        # Check for API health check script
        if [ -f "scripts/api-health-check-main.sh" ]; then
            total_tests=$((total_tests + 1))
            log "Running comprehensive API health check..."
            if scripts/api-health-check-main.sh >/dev/null 2>&1; then
                success "Comprehensive API Health Check"
                passed_tests=$((passed_tests + 1))
            else
                error "Comprehensive API Health Check (REQUIRED)"
                failed_required=$((failed_required + 1))
            fi
        fi
        
        # Check for specific integration files
        integration_tests=(
            "OAuth2 Template|test -f \"api-integration/scripts/oauth2-template.py\"|false"
            "Integration Pipeline|test -f \"api-integration/scripts/integration-pipeline.py\"|false"
            "Service Order Scripts|test -f \"scripts/service-order-automation.sh\"|false"
        )
        
        for test_def in "${integration_tests[@]}"; do
            IFS='|' read -r name command required <<< "$test_def"
            total_tests=$((total_tests + 1))
            if run_test "$name" "$command" "$required"; then
                passed_tests=$((passed_tests + 1))
            elif [ "$required" = "true" ]; then
                failed_required=$((failed_required + 1))
            fi
        done
        
        echo ""
    fi
    
    # Phase 4: File Organization Tests
    log "Phase 4: File Organization"
    
    org_tests=(
        "Memory Directory|test -d \"memory\"|true"
        "Scripts Directory|test -d \"scripts\"|true"
        "API Integration Skill|test -f \"api-integration/SKILL.md\"|false"
        "Today's Memory File|test -f \"memory/\$(date +%Y-%m-%d).md\"|false"
    )
    
    for test_def in "${org_tests[@]}"; do
        IFS='|' read -r name command required <<< "$test_def"
        total_tests=$((total_tests + 1))
        if run_test "$name" "$command" "$required"; then
            passed_tests=$((passed_tests + 1))
        elif [ "$required" = "true" ]; then
            failed_required=$((failed_required + 1))
        fi
    done
    
    echo ""
    
    # Summary
    log "🏁 Test Results Summary"
    echo "   Total Tests: $total_tests"
    echo "   Passed: $passed_tests"
    echo "   Failed (Required): $failed_required"
    echo "   Success Rate: $((passed_tests * 100 / total_tests))%"
    
    if [ "$failed_required" -eq 0 ]; then
        success "All required tests passed! System ready for integration work."
        
        # Provide next steps based on what's available
        echo ""
        echo "🚀 Available Tools:"
        [ -f "scripts/api-health-check-main.sh" ] && echo "   • API Health Check: ./scripts/api-health-check-main.sh"
        [ -f "scripts/validate-commitment.sh" ] && echo "   • Commitment Validator: ./scripts/validate-commitment.sh <org_id>"
        [ -f "scripts/service-order-automation.sh" ] && echo "   • Service Order Tools: ./scripts/service-order-automation.sh"
        [ -f "api-integration/SKILL.md" ] && echo "   • API Integration Skill: Available for complex projects"
        
        return 0
    else
        error "$failed_required required test(s) failed. Fix these before proceeding."
        
        # Provide specific guidance for common failures
        echo ""
        echo "🔧 Common Fixes:"
        echo "   • Missing API keys: Set environment variables (SF_CLIENT_ID, etc.)"
        echo "   • Directory issues: Run from workspace root (/Users/niamhcollins/clawd)"
        echo "   • Permission issues: Check script permissions (chmod +x)"
        
        return 1
    fi
}

main "$@"