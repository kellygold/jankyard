#!/bin/bash
# Startup script for Jankyard.ai

echo "🧟‍♂️ Starting Jankyard.ai..."
echo ""

# Check if we're in the right directory
if [ ! -d "backend" ]; then
    echo "❌ Error: Please run this script from the jankyard root directory"
    exit 1
fi

# Navigate to backend
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp .env.example .env
    echo "⚙️  Please edit backend/.env with your database credentials"
    echo ""
fi

# Initialize database
echo "🗄️  Initializing database..."
python init_db.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Starting server on http://localhost:8000"
echo "   Press Ctrl+C to stop"
echo ""

# Start the server
python app/main.py
