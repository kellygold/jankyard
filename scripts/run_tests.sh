#!/bin/bash
# =============================================================================
# Jankyard Test Runner
# =============================================================================
# 
# This script runs the complete test suite to verify level progression fixes.
#
# Usage:
#   ./scripts/run_tests.sh          # Run all tests
#   ./scripts/run_tests.sh api      # Run only API tests
#   ./scripts/run_tests.sh e2e      # Run only E2E tests
#   ./scripts/run_tests.sh quick    # Run fast tests only (skip slow)
#
# Prerequisites:
#   pip install -r requirements-test.txt
#   playwright install chromium
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Jankyard Level Progression Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    # Check pytest
    if ! command -v pytest &> /dev/null; then
        echo -e "${RED}❌ pytest not found. Run: pip install -r requirements-test.txt${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ pytest installed${NC}"
    
    # Check playwright (only if running e2e)
    if [[ "$1" == "e2e" || "$1" == "" ]]; then
        if ! python -c "import playwright" 2>/dev/null; then
            echo -e "${RED}❌ playwright not found. Run: pip install playwright && playwright install chromium${NC}"
            exit 1
        fi
        echo -e "${GREEN}✓ playwright installed${NC}"
    fi
    
    echo ""
}

# Run API tests
run_api_tests() {
    echo -e "${BLUE}Running API Tests...${NC}"
    echo "Testing: /leaderboard/{challenge}/progress endpoint"
    echo ""
    
    pytest tests/api/ \
        -v \
        --tb=short \
        -m "api" \
        --ignore=tests/e2e/ \
        "$@"
    
    echo ""
    echo -e "${GREEN}✓ API tests complete${NC}"
}

# Run E2E tests
run_e2e_tests() {
    echo -e "${BLUE}Running E2E Tests...${NC}"
    echo "Testing: Browser-based level progression flows"
    echo ""
    
    # Check if server is running
    if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Server not running at localhost:8000${NC}"
        echo -e "${YELLOW}Starting server in background...${NC}"
        
        # Start server in background
        python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
        SERVER_PID=$!
        
        # Wait for server to be ready
        echo "Waiting for server..."
        for i in {1..30}; do
            if curl -s http://localhost:8000/health > /dev/null 2>&1; then
                echo -e "${GREEN}✓ Server ready${NC}"
                break
            fi
            sleep 1
        done
        
        CLEANUP_SERVER=true
    else
        echo -e "${GREEN}✓ Server already running${NC}"
        CLEANUP_SERVER=false
    fi
    
    # Run tests
    TEST_BASE_URL="http://localhost:8000" pytest tests/e2e/ \
        -v \
        --tb=short \
        -m "e2e" \
        "$@"
    
    # Cleanup
    if [ "$CLEANUP_SERVER" = true ]; then
        echo "Stopping test server..."
        kill $SERVER_PID 2>/dev/null || true
    fi
    
    echo ""
    echo -e "${GREEN}✓ E2E tests complete${NC}"
}

# Run all tests
run_all_tests() {
    echo -e "${BLUE}Running Complete Test Suite...${NC}"
    echo ""
    
    # API tests first (fast)
    run_api_tests "$@"
    
    echo ""
    echo -e "${BLUE}----------------------------------------${NC}"
    echo ""
    
    # E2E tests (slower)
    run_e2e_tests "$@"
}

# Run quick tests (skip slow)
run_quick_tests() {
    echo -e "${BLUE}Running Quick Tests (skipping slow)...${NC}"
    echo ""
    
    pytest tests/ \
        -v \
        --tb=short \
        -m "not slow" \
        "$@"
}

# Main
case "${1:-all}" in
    api)
        check_prerequisites api
        shift || true
        run_api_tests "$@"
        ;;
    e2e)
        check_prerequisites e2e
        shift || true
        run_e2e_tests "$@"
        ;;
    quick)
        check_prerequisites quick
        shift || true
        run_quick_tests "$@"
        ;;
    all|*)
        check_prerequisites
        if [ "$1" = "all" ]; then shift || true; fi
        run_all_tests "$@"
        ;;
esac

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  All tests completed!${NC}"
echo -e "${GREEN}========================================${NC}"
