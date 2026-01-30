#!/bin/bash

# Script para ejecutar tests

echo "=== Price Intelligence API - Test Runner ==="
echo ""

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Verificar pytest
if ! python -c "import pytest" 2>/dev/null; then
    echo "Installing pytest..."
    pip install pytest pytest-asyncio
fi

echo "Running unit tests..."
echo ""

# Ejecutar tests con verbose output
pytest tests/ -v --tb=short

echo ""
echo "=== Test Results Above ==="
