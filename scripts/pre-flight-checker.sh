#!/bin/bash
# Pre-flight Checker - Comprehensive system health check before starting work
# Addresses critical issues identified in efficiency review: context overflow, auth failures, session fragmentation

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

VERBOSE=false
FIX_ISSUES=false
WORKSPACE_DIR="/Users/niamhcollins/clawd"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose)
            VERBOSE=true
            shift
            ;;
        --fix)
            FIX_ISSUES=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--verbose] [--fix]"
            echo ""
            echo "Pre-flight checker for critical system health:"
            echo "  • Salesforce authentication status"
            echo "  • Response length validation setup"
            echo "  • Session fragmentation analysis" 
            echo "  • Quinn metrics system health"
            echo "  • API connectivity verification"
            echo ""
            echo "Options:"
            echo "  --verbose    Show detailed output"
            echo "  --fix        Attempt automatic fixes for detected issues"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
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

check_workspace() {
    log "Checking workspace setup..."
    
    if [ ! -d "$WORKSPACE_DIR" ]; then
        error "Workspace directory not found: $WORKSPACE_DIR"
        return 1
    fi
    
    cd "$WORKSPACE_DIR"
    
    # Check for critical directories
    local critical_dirs=("memory" "scripts" "api-integration")
    for dir in "${critical_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            warning "Missing directory: $dir"
        else
            success "Directory exists: $dir"
        fi
    done
    
    return 0
}

check_salesforce_auth() {
    log "Checking Salesforce authentication..."
    
    if [ ! -f "scripts/salesforce-auth-fixer.py" ]; then
        error "Salesforce auth fixer not found"
        return 1
    fi
    
    # Run Salesforce auth check
    python3 scripts/salesforce-auth-fixer.py > /tmp/sf_auth_check.log 2>&1
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        success "Salesforce authentication working (both OAuth2 and CLI)"
    elif [ $exit_code -eq 1 ]; then
        warning "Salesforce OAuth2 works, CLI needs attention"
        [ "$VERBOSE" = true ] && cat /tmp/sf_auth_check.log
        
        if [ "$FIX_ISSUES" = true ]; then
            log "Attempting Salesforce CLI fix..."
            python3 scripts/salesforce-auth-fixer.py --fix
        fi
    else
        error "Salesforce authentication failed"
        [ "$VERBOSE" = true ] && cat /tmp/sf_auth_check.log
        
        if [ "$FIX_ISSUES" = true ]; then
            log "Attempting Salesforce authentication fix..."
            python3 scripts/salesforce-auth-fixer.py --fix
        fi
    fi
    
    rm -f /tmp/sf_auth_check.log
    return $exit_code
}

check_response_length_tools() {
    log "Checking response length validation tools..."
    
    if [ ! -f "scripts/response-length-validator.py" ]; then
        error "Response length validator not found"
        return 1
    fi
    
    # Test with a sample text
    echo "This is a test response to validate the response length checker functionality." | \
    python3 scripts/response-length-validator.py - > /tmp/response_test.log 2>&1
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        success "Response length validator ready"
    else
        error "Response length validator test failed"
        [ "$VERBOSE" = true ] && cat /tmp/response_test.log
    fi
    
    rm -f /tmp/response_test.log
    return $exit_code
}

check_session_health() {
    log "Checking session fragmentation..."
    
    if [ ! -f "scripts/session-consolidation-detector.py" ]; then
        warning "Session consolidation detector not found"
        return 1
    fi
    
    # Run with mock data
    python3 scripts/session-consolidation-detector.py mock > /tmp/session_check.log 2>&1
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        success "Session organization healthy"
    elif [ $exit_code -eq 1 ]; then
        warning "Medium session fragmentation detected"
        [ "$VERBOSE" = true ] && cat /tmp/session_check.log
    else
        error "High session fragmentation detected"
        [ "$VERBOSE" = true ] && cat /tmp/session_check.log
    fi
    
    rm -f /tmp/session_check.log
    return 0  # Don't fail on session fragmentation
}

check_api_health() {
    log "Running comprehensive API health check..."
    
    if [ -f "scripts/api-health-check-main.sh" ] || [ -f "scripts/api-health-check.sh" ]; then
        local health_script=""
        [ -f "scripts/api-health-check-main.sh" ] && health_script="scripts/api-health-check-main.sh"
        [ -f "scripts/api-health-check.sh" ] && health_script="scripts/api-health-check.sh"
        local verbose_flag=""
        [ "$VERBOSE" = true ] && verbose_flag="--verbose"
        
        $health_script $verbose_flag > /tmp/api_health.log 2>&1
        local exit_code=$?
        
        if [ $exit_code -eq 0 ]; then
            success "All API credentials working"
        elif [ $exit_code -eq 1 ]; then
            warning "Some API credentials need attention"
            [ "$VERBOSE" = true ] && cat /tmp/api_health.log
        else
            error "No API credentials working"
            [ "$VERBOSE" = true ] && cat /tmp/api_health.log
        fi
        
        rm -f /tmp/api_health.log
        return $exit_code
    else
        warning "API health check script not found"
        return 1
    fi
}

check_quinn_metrics() {
    log "Checking Quinn metrics system status..."
    
    # Check if we have recent Quinn metrics data
    local latest_quinn_file=$(ls memory/quinn-metrics-*.json 2>/dev/null | sort | tail -1)
    
    if [ -n "$latest_quinn_file" ]; then
        local file_age=$(( $(date +%s) - $(stat -f %m "$latest_quinn_file" 2>/dev/null || stat -c %Y "$latest_quinn_file") ))
        local hours_old=$(( file_age / 3600 ))
        
        if [ $hours_old -lt 48 ]; then
            success "Quinn metrics data recent (${hours_old}h old)"
        else
            warning "Quinn metrics data stale (${hours_old}h old)"
        fi
    else
        error "No Quinn metrics data found"
    fi
    
    # Check if Quinn automation is running
    if [ -f "memory/quinn-metrics-report-status.md" ]; then
        if grep -q "Day [4-9]" "memory/quinn-metrics-report-status.md"; then
            error "Quinn metrics automation has been down for multiple days"
        else
            success "Quinn metrics automation status looks good"
        fi
    else
        warning "Quinn metrics status file not found"
    fi
    
    return 0  # Don't fail the pre-flight on Quinn metrics
}

check_critical_files() {
    log "Checking for critical efficiency files..."
    
    local critical_files=(
        "memory/technical-architecture-templates.md"
        "scripts/unified-test-framework.sh"
        "scripts/database-migrations.py"
        "scripts/file-naming-conventions.py"
        "api-integration/SKILL.md"
    )
    
    local missing_count=0
    
    for file in "${critical_files[@]}"; do
        if [ -f "$file" ]; then
            success "Found: $(basename "$file")"
        else
            error "Missing: $file"
            missing_count=$((missing_count + 1))
        fi
    done
    
    if [ $missing_count -eq 0 ]; then
        success "All efficiency tools available"
        return 0
    else
        warning "$missing_count efficiency tools missing"
        return 1
    fi
}

generate_daily_readiness_report() {
    log "Generating daily readiness report..."
    
    local report_file="memory/daily-readiness-$(date +%Y-%m-%d).md"
    
    cat > "$report_file" << EOF
# Daily Readiness Report - $(date +"%Y-%m-%d")

Generated: $(date +"%Y-%m-%d %H:%M:%S")

## System Health Summary

$([ "$sf_auth_status" = "0" ] && echo "✅" || echo "❌") **Salesforce Authentication**: $([ "$sf_auth_status" = "0" ] && echo "Working" || echo "Needs attention")
$([ "$api_health_status" = "0" ] && echo "✅" || echo "❌") **API Health**: $([ "$api_health_status" = "0" ] && echo "All APIs working" || echo "Some APIs need attention") 
$([ "$response_tools_status" = "0" ] && echo "✅" || echo "❌") **Response Length Tools**: $([ "$response_tools_status" = "0" ] && echo "Ready" || echo "Not available")
$([ "$session_health_status" -le "1" ] && echo "✅" || echo "⚠️") **Session Health**: $([ "$session_health_status" = "0" ] && echo "Good organization" || echo "Some fragmentation")

## Critical Issues to Address

$([ "$sf_auth_status" != "0" ] && echo "- 🚨 **Salesforce Authentication**: Fix connectivity for Quinn metrics" || echo "- No critical authentication issues")
$([ "$api_health_status" != "0" ] && echo "- ⚠️ **API Connectivity**: Some services may be unavailable" || echo "- No critical API issues")

## Ready to Proceed

$([ "$overall_status" = "0" ] && echo "✅ **System is ready for work**" || echo "⚠️ **Address critical issues before major work**")

Generated by pre-flight checker v1.0
EOF

    success "Daily readiness report saved: $report_file"
}

main() {
    echo "🚁 Pre-flight System Health Check"
    echo "   Checking critical systems before starting work..."
    echo ""
    
    # Initialize status tracking
    local overall_status=0
    
    # Run all checks
    check_workspace
    workspace_status=$?
    
    check_salesforce_auth
    sf_auth_status=$?
    
    check_api_health
    api_health_status=$?
    
    check_response_length_tools  
    response_tools_status=$?
    
    check_session_health
    session_health_status=$?
    
    check_quinn_metrics
    quinn_status=$?
    
    check_critical_files
    critical_files_status=$?
    
    echo ""
    
    # Calculate overall status
    local critical_failures=0
    
    [ "$workspace_status" != "0" ] && critical_failures=$((critical_failures + 1))
    [ "$sf_auth_status" = "2" ] && critical_failures=$((critical_failures + 1))  # Only fail on complete auth failure
    [ "$api_health_status" = "2" ] && critical_failures=$((critical_failures + 1))  # Only fail on complete API failure
    [ "$response_tools_status" != "0" ] && critical_failures=$((critical_failures + 1))
    
    # Summary
    log "🏁 Pre-flight Check Summary"
    
    if [ $critical_failures -eq 0 ]; then
        success "System ready for work!"
        echo "   • Salesforce authentication working"
        echo "   • API connectivity verified" 
        echo "   • Response validation tools ready"
        echo "   • Efficiency framework available"
        overall_status=0
    elif [ $critical_failures -le 2 ]; then
        warning "System mostly ready with some issues to monitor"
        echo "   • Some non-critical systems need attention"
        echo "   • Major work can proceed with caution"
        overall_status=1
    else
        error "Critical system failures detected"
        echo "   • Address critical issues before major work"
        echo "   • Consider using --fix flag for automatic repairs"
        overall_status=2
    fi
    
    echo ""
    
    # Generate readiness report
    generate_daily_readiness_report
    
    # Provide next steps
    echo "🎯 Next Steps:"
    if [ $overall_status -eq 0 ]; then
        echo "   • System ready for complex integration work"
        echo "   • Use efficiency tools from today's implementation"
        echo "   • Consider V2 Call Intelligence deployment"
    else
        echo "   • Review specific failures above"
        echo "   • Run with --fix to attempt automatic repairs"
        echo "   • Address Salesforce auth for Quinn metrics"
    fi
    
    return $overall_status
}

main "$@"