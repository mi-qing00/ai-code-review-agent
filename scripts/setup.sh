#!/bin/bash
# Setup script for development environment

set -e

echo "🚀 Setting up AI Code Review Agent..."

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry is not installed. Installing..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install dependencies
echo "📦 Installing dependencies..."
poetry install

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from example..."
    cat > .env << EOF
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/code_review_db

# Redis
REDIS_URL=redis://localhost:6379/0

# GitHub
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
GITHUB_TOKEN=your_github_token_here

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# App Settings
LOG_LEVEL=INFO
ENVIRONMENT=development
EOF
    echo "⚠️  Please update .env with your actual credentials"
else
    echo "✅ .env file already exists"
fi

# Start Docker services
echo "🐳 Starting Docker services (PostgreSQL and Redis)..."
if command -v docker-compose &> /dev/null || command -v docker &> /dev/null; then
    docker-compose up -d || docker compose up -d
    echo "⏳ Waiting for services to be ready..."
    sleep 5
else
    echo "⚠️  Docker not found. Please start PostgreSQL and Redis manually"
fi

# Setup database
echo "🗄️  Setting up database..."
if command -v psql &> /dev/null; then
    PGPASSWORD=password psql -h localhost -U user -d code_review_db -f migrations/001_initial_schema.sql 2>/dev/null || \
    echo "⚠️  Could not run migration. Please run manually:"
    echo "   psql -d code_review_db -f migrations/001_initial_schema.sql"
else
    echo "⚠️  psql not found. Please run migration manually:"
    echo "   psql -d code_review_db -f migrations/001_initial_schema.sql"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update .env with your API keys and tokens"
echo "2. Run: poetry shell"
echo "3. Run: uvicorn app.main:app --reload"

