#!/bin/bash

# Script para iniciar el servidor de desarrollo

echo "=== Price Intelligence API - Startup Script ==="
echo ""

# Verificar si el entorno virtual existe
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activar entorno virtual
echo "Activating virtual environment..."
source venv/bin/activate

# Verificar si las dependencias están instaladas
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies already installed"
fi

# Verificar si existe el archivo .env
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your eBay credentials"
fi

# Verificar si existe el CSV de datos internos
if [ ! -f "data/internal_data.csv" ]; then
    echo "⚠️  Internal data CSV not found"
    if [ -f "data/sample_internal_data.csv" ]; then
        echo "Copying sample data..."
        cp data/sample_internal_data.csv data/internal_data.csv
    fi
fi

echo ""
echo "=== Starting API Server ==="
echo "API will be available at: http://localhost:8000"
echo "API documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Ejecutar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
