#!/bin/bash

# Figma Text API Server Startup Script
# This script activates the virtual environment and starts the FastAPI server

echo "🚀 Starting Figma Text API Server..."
echo "======================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating with placeholder values..."
    cat > .env << EOF
FIGMA_ACCESS_TOKEN=your_figma_access_token_here
FIGMA_FILE_KEY=your_figma_file_key_here
DATABASE_URL=sqlite+aiosqlite:///./mobile_app_data.db
HOST=0.0.0.0
PORT=8000
EOF
    echo "📝 Please edit .env with your real Figma credentials"
fi

# Activate virtual environment
source venv/bin/activate

# Check if required packages are installed
python -c "import fastapi, uvicorn, sqlalchemy, httpx, dotenv" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Initialize database
echo "🗄️  Initializing database..."
python -c "import database; import asyncio; asyncio.run(database.create_tables())"

echo "✅ Database ready"
echo "🌐 Starting server on http://0.0.0.0:8000"
echo "📖 API docs available at http://0.0.0.0:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo "======================================"

# Start the server
python main.py 