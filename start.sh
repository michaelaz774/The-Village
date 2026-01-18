#!/bin/bash

# Start script for The Village backend services
# This runs both the FastAPI server and the LiveKit agent

# Activate virtual environment
source venv/bin/activate

# Function to cleanup on exit
cleanup() {
    echo "Shutting down services..."
    kill $FASTAPI_PID $AGENT_PID 2>/dev/null
    exit
}

trap cleanup EXIT INT TERM

# Start FastAPI in background
echo "Starting FastAPI server on port 8111..."
uvicorn backend.main:app --host 0.0.0.0 --port 8111 --reload &
FASTAPI_PID=$!

# Wait a moment for FastAPI to start
sleep 2

# Start LiveKit Agent in background
echo "Starting LiveKit Agent..."
python backend/voice/agent.py dev &
AGENT_PID=$!

echo ""
echo "✅ Services started!"
echo "   FastAPI: http://localhost:8111"
echo "   Agent: Running"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for both processes
wait
