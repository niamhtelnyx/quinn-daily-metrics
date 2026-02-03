#!/bin/bash

set -o nounset -o errexit -o xtrace

echo "Waiting for db..."
/app/files/wait-for-it.sh ${PRIMARY_DB__HOST}:${PRIMARY_DB__PORT} -t 10

if [[ ${CREATEDB:-false} == 'true' ]]; then
    echo "Setting up database..."
    cd /app/files
    python3 create_database.py
fi

cd /app
alembic upgrade head
