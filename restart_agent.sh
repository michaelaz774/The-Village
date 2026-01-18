#!/bin/bash

# Quick restart script for The Village LiveKit Agent

echo "🔄 Restarting LiveKit Agent..."
echo ""

# Find and kill existing agent process
pkill -f "python backend/voice/agent.py dev" 2>/dev/null
sleep 1

# Navigate to project root
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Start the agent
echo "🚀 Starting agent..."
python backend/voice/agent.py dev
