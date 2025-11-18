#!/bin/bash
# Health check script for Docker containers

set -e

# Check if service is specified
if [ -z "$1" ]; then
    echo "Usage: $0 <service_name>"
    exit 1
fi

SERVICE=$1

case $SERVICE in
    "web")
        # Check FastAPI health endpoint
        curl -f http://localhost:8000/health || exit 1
        ;;

    "worker")
        # Check if Celery worker is running
        celery -A app.core.celery_app inspect ping -d celery@$HOSTNAME || exit 1
        ;;

    "redis")
        # Check Redis
        redis-cli ping || exit 1
        ;;

    *)
        echo "Unknown service: $SERVICE"
        exit 1
        ;;
esac

echo "$SERVICE is healthy"
exit 0
