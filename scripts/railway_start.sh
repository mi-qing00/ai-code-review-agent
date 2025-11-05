#!/bin/bash
# Railway startup script that detects service type from environment

# If SERVICE_TYPE is set, use it; otherwise check if PORT is set (web service)
if [ -n "$SERVICE_TYPE" ]; then
    SERVICE=$SERVICE_TYPE
elif [ -n "$PORT" ]; then
    # If PORT is set, this is the web service
    SERVICE="web"
else
    # Default to worker if no PORT is set
    SERVICE="worker"
fi

case "$SERVICE" in
    web)
        echo "Starting web service..."
        exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
        ;;
    worker)
        echo "Starting worker service..."
        # Ensure unbuffered output for Railway logging
        export PYTHONUNBUFFERED=1
        exec python -m app.queue.consumer
        ;;
    *)
        echo "Unknown service type: $SERVICE"
        echo "Set SERVICE_TYPE=web or SERVICE_TYPE=worker"
        exit 1
        ;;
esac

