#!/bin/bash
set -e

echo "🚀 Starting NiceGUI + FastAPI"

# Activate virtualenv
source .venv/bin/activate

# Start FastAPI (background)
echo "⚡ Starting FastAPI on port 8000..."
uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8000 &

FASTAPI_PID=$!

# Wait for FastAPI to be ready (simple approach)
echo "⏳ Waiting for FastAPI to be ready..."
sleep 3  # Give FastAPI time to start

# Simple health check - try once
if command -v curl > /dev/null 2>&1; then
    if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
        echo "✅ FastAPI is ready!"
    else
        echo "⚠️  FastAPI may not be ready, but continuing..."
    fi
else
    # Fallback: just wait a bit longer
    sleep 2
    echo "⏭️  Continuing (curl not available for health check)"
fi

# Start NiceGUI (background)
echo "🎨 Starting NiceGUI on port 8080..."
python app.py &

NICEGUI_PID=$!

# Graceful shutdown
trap "echo '🛑 Stopping services...'; kill $FASTAPI_PID $NICEGUI_PID 2>/dev/null || true; exit" SIGINT SIGTERM

wait
