#!/bin/bash
# Quick start script for Tauri MVP (development mode)
# Run from repo root: tauri-mvp/start-dev.sh

set -e

echo "=== Starting Living to Tell Tauri preview (development) ==="
echo ""

# Start backend in background
echo "[1/2] Starting FastAPI backend on :8000..."
cd backend
python run.py --dev &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
echo "Waiting for backend to start..."
for i in {1..10}; do
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo "✓ Backend ready"
        break
    fi
    sleep 1
done

# Start frontend
echo ""
echo "[2/2] Starting Vue frontend on :1420..."
echo "Open http://localhost:1420 in your browser"
echo ""
echo "Press Ctrl+C to stop both servers"
cd frontend
npm run dev

# Cleanup
kill $BACKEND_PID 2>/dev/null || true
