#!/bin/bash
# Setup script to install dependencies for testing

set -e

echo "🔧 Setting up test environment..."
echo "================================"
echo ""

# Check if poetry is available
if command -v poetry &> /dev/null; then
    echo "✅ Poetry found: $(poetry --version)"
    echo ""
    echo "Installing dependencies with Poetry..."
    poetry install
    echo ""
    echo "✅ Dependencies installed!"
    echo ""
    echo "You can now run tests with:"
    echo "  ./scripts/test_llm_integration.sh"
    echo "  poetry run python scripts/test_end_to_end.py <repo> <pr_number>"
else
    echo "❌ Poetry not found in PATH"
    echo ""
    echo "Please either:"
    echo "  1. Install Poetry: curl -sSL https://install.python-poetry.org | python3 -"
    echo "  2. Or add Poetry to your PATH"
    echo ""
    echo "Alternatively, you can install dependencies manually:"
    echo "  pip install pydantic-settings anthropic httpx openai"
    exit 1
fi

