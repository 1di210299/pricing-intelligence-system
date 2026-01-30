#!/bin/bash
# Start both backend and frontend

echo "🚀 Starting Pricing Intelligence System"
echo ""

# Check if backend is already running
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "✅ Backend already running on port 8000"
else
    echo "🔧 Starting backend..."
    cd "$(dirname "$0")"
    source venv/bin/activate 2>/dev/null || true
    python -m app.main > logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo "✅ Backend started (PID: $BACKEND_PID)"
    sleep 3
fi

# Start frontend
echo "🎨 Starting frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

npm run dev &
FRONTEND_PID=$!

echo ""
echo "=================================="
echo "✅ System Started Successfully!"
echo "=================================="
echo ""
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for Ctrl+C
trap "echo ''; echo '🛑 Stopping servers...'; kill $FRONTEND_PID 2>/dev/null; exit 0" INT
wait
