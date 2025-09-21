#!/bin/bash
set -e

# Wait for ports to be available (without lsof)
wait_for_port() {
    local port=$1
    local host=$2
    echo "Waiting for port $port on $host..."
    timeout=30
    while ! nc -z $host $port && [ $timeout -gt 0 ]; do
        echo "Port $port on $host is still not available, waiting... ($timeout seconds left)"
        sleep 1
        timeout=$((timeout-1))
    done
    if [ $timeout -eq 0 ]; then
        echo "Timeout waiting for port $port on $host"
        return 1
    fi
}

# Wait for database
echo "Waiting for database..."
wait_for_port 5432 db || exit 1

# Wait for Redis
echo "Waiting for Redis..."
wait_for_port 6379 redis || exit 1

# Run migrations if command is gunicorn (for web service)
if [ "$1" = "gunicorn" ]; then
    echo "Running migrations..."
    python /app/Flexingg/manage.py makemigrations
    python /app/Flexingg/manage.py migrate
    python /app/Flexingg/manage.py collectstatic --noinput
fi

# Set timezone from environment variable
export TZ=$TIMEZONE

# Execute the main command
exec "$@"