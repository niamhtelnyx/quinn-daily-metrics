#!/bin/bash

set -o nounset -o errexit -o xtrace

echo "Starting my-agentic-serviceservice-order-specialist service..."


# Wait for database to be ready
echo "Waiting for database..."
/app/files/wait-for-it.sh ${PRIMARY_DB__HOST}:${PRIMARY_DB__PORT} -t 30

# Create database if needed
if [[ "${CREATEDB:-false}" == 'true' ]]; then
    echo "Setting up database..."
    cd /app/files
    python3 create_database.py
fi

# Run database migrations
echo "Running database migrations..."
cd /app
alembic upgrade head


# Start the application
echo "Starting application server..."
if [[ "${HOT_RELOAD:-false}" == "true" ]]; then
    exec python3 -m my_agentic_serviceservice_order_specialist --reload
else
    exec python3 -m my_agentic_serviceservice_order_specialist
fi
