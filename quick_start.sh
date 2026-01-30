#!/bin/bash
# Quick Start Script for Pricing Intelligence System

echo "=================================="
echo "Pricing Intelligence System Setup"
echo "=================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt -q

echo "Installing Playwright browsers..."
playwright install chromium

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Available commands:"
echo ""
echo "1. Test internal data only (quick):"
echo "   python test_integration.py --quick"
echo ""
echo "2. Full integration test (with eBay scraping):"
echo "   python test_integration.py"
echo ""
echo "3. Start API server:"
echo "   ./start.sh"
echo ""
echo "4. Run unit tests:"
echo "   ./run_tests.sh"
echo ""
echo "5. View API docs (after starting server):"
echo "   http://localhost:8000/docs"
echo ""
