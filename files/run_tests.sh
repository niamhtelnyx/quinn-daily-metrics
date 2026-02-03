#!/bin/sh

set -e



MIN_COVERAGE=0
PARALLEL_PROCESSES=2
PROJECT_NAME=my_agentic_serviceservice_order_specialist
TEST_PATH=tests

echo ""
echo "Style check"
echo "-----------------------------"
ruff format $PROJECT_NAME $TEST_PATH --check -q
echo "style: OK!"

echo ""
echo "Linter check"
echo "-----------------------------"
ruff check $PROJECT_NAME $TEST_PATH -q
echo "linter: OK!"

echo ""
echo "Type check"
echo "-----------------------------"
# Use PYTHON_INTERPRETER env var if set, otherwise auto-detect
PYREFLY_INTERPRETER_ARG=""
if [ -n "$PYTHON_INTERPRETER" ]; then
    PYREFLY_INTERPRETER_ARG="--python-interpreter-path=$PYTHON_INTERPRETER"
fi

# Disable progress bar in CI environments
if [ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_HOME" ]; then
    unset PYTHONPATH  # Disable PYTHONPATH in CI environment to avoid warning messages
    TERM=dumb CI=true pyrefly check -j 2 --summary=none --color=never $PYREFLY_INTERPRETER_ARG $PROJECT_NAME $TEST_PATH
else
    # In local development, show progress
    pyrefly check $PROJECT_NAME $TEST_PATH -j 2 --summary=none $PYREFLY_INTERPRETER_ARG
fi
echo "type check: OK!"

echo ""
echo "Tests"
echo "-----------------------------"
pytest --numprocesses=$PARALLEL_PROCESSES --dist=loadscope --exitfirst --cov=$PROJECT_NAME --cov-fail-under=$MIN_COVERAGE --cov-report=term $TEST_PATH
echo "tests: OK!"
