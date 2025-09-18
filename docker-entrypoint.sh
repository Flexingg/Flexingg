#!/bin/bash
set -e

# Wait for the database
if [ "$DB_HOST" ] && [ "$DB_PORT" ]; then
  echo "Waiting for database..."
  nc -z $DB_HOST $DB_PORT
fi

# Run migrations
python /app/Flexingg/manage.py makemigrations
python /app/Flexingg/manage.py migrate

# Collect static files
python /app/Flexingg/manage.py collectstatic --noinput

# Run the command passed to docker
exec "$@"