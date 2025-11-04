#!/bin/bash
# Test script for LLM integration

set -e

echo "🧪 LLM Integration Test Script"
echo "================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test repository
TEST_REPO="kaitlynmi/pr-review-agent-test"
TEST_PR_NUMBER=1  # Update this based on your test PR

# Detect Python command (prefer poetry, fallback to python3)
if command -v poetry &> /dev/null; then
    PYTHON_CMD="poetry run python"
elif [ -f "pyproject.toml" ]; then
    # Try to use poetry if it exists in the shell
    PYTHON_CMD="poetry run python"
else
    PYTHON_CMD="python3"
    echo "⚠️  Using python3 directly. Make sure dependencies are installed."
fi

echo "🧪 LLM Integration Test Script"
echo "================================"
echo "Using: $PYTHON_CMD"
echo ""

echo -e "${YELLOW}Step 1: Verify Configuration${NC}"
echo "================================"
$PYTHON_CMD -c "
from app.core.config import settings
try:
    config = settings.get_llm_config()
    print(f\"✅ Provider: {config['provider']}\")
    print(f\"✅ Model: {config['model']}\")
    print(f\"✅ API Key: {config['api_key'][:20]}...\")
except Exception as e:
    print(f\"❌ Configuration error: {e}\")
    exit(1)
"
echo ""

echo -e "${YELLOW}Step 2: Test Zhipu Provider in Isolation${NC}"
echo "================================"
$PYTHON_CMD -c "
import asyncio
from app.llm.factory import get_llm_provider
from app.llm.models import DiffContext

async def test_provider():
    try:
        provider = get_llm_provider()
        print(f\"✅ Provider initialized: {provider.provider_name}\")
        
        # Test with a simple diff
        test_diff = '''--- a/test.py
+++ b/test.py
@@ -1,3 +1,3 @@
 def divide(a, b):
-    return a / b
+    return a / b  # Missing error handling
'''
        
        result = await provider.analyze_diff(test_diff)
        print(f\"✅ Analysis completed:\")
        print(f\"   - Comments: {len(result.comments)}\")
        print(f\"   - Tokens: {result.tokens_used}\")
        print(f\"   - Cost: \${result.cost:.4f}\")
        print(f\"   - Time: {result.processing_time:.2f}s\")
        
        if result.comments:
            print(f\"   - First comment: {result.comments[0].comment_text[:50]}...\")
        
        return True
    except Exception as e:
        print(f\"❌ Provider test failed: {e}\")
        import traceback
        traceback.print_exc()
        return False

result = asyncio.run(test_provider())
exit(0 if result else 1)
"
echo ""

echo -e "${YELLOW}Step 3: Test Response Parser${NC}"
echo "================================"
$PYTHON_CMD -c "
from app.llm.parser import parse_review_response

test_response = '''test.py:5 - Missing error handling for division by zero
test.py:10 - Variable name 'x' is not descriptive
utils.py:15 - Consider using context manager for file handling
'''

try:
    comments = parse_review_response(test_response)
    print(f\"✅ Parsed {len(comments)} comments\")
    for i, comment in enumerate(comments, 1):
        print(f\"   {i}. {comment.file_path}:{comment.line_number} - {comment.comment_text[:50]}\")
except Exception as e:
    print(f\"❌ Parser test failed: {e}\")
    exit(1)
"
echo ""

echo -e "${YELLOW}Step 4: Test GitHub Diff Fetching${NC}"
echo "================================"
echo "Testing with repo: $TEST_REPO, PR: $TEST_PR_NUMBER"
$PYTHON_CMD -c "
import asyncio
import os
from app.github.client import GitHubClient
from app.core.config import settings

async def test_github():
    token = os.getenv('GITHUB_TOKEN') or settings.github_token
    if not token or token == 'your_github_token_here':
        print('⚠️  GITHUB_TOKEN not set, skipping GitHub test')
        return False
    
    try:
        client = GitHubClient(token=token)
        print(f\"✅ GitHub client initialized\")
        
        diff_context = await client.fetch_pr_diff('$TEST_REPO', $TEST_PR_NUMBER)
        print(f\"✅ Diff fetched successfully:\")
        print(f\"   - Files changed: {len(diff_context.changed_files)}\")
        print(f\"   - Additions: {diff_context.additions}\")
        print(f\"   - Deletions: {diff_context.deletions}\")
        print(f\"   - Diff size: {len(diff_context.diff_text)} chars\")
        
        await client.close()
        return True
    except Exception as e:
        print(f\"❌ GitHub test failed: {e}\")
        import traceback
        traceback.print_exc()
        return False

result = asyncio.run(test_github())
exit(0 if result else 1)
"
echo ""

echo -e "${YELLOW}Step 5: End-to-End Test${NC}"
echo "================================"
echo "To test end-to-end:"
echo "1. Create a PR in https://github.com/$TEST_REPO"
echo "2. The webhook should trigger automatically"
echo "3. Check worker logs for processing"
echo "4. Check the PR for review comments"
echo ""

echo -e "${GREEN}✅ All isolated tests completed!${NC}"
echo ""
echo "Next steps:"
echo "1. Make sure worker is running: ./scripts/start-worker.sh"
echo "2. Create a test PR in the repository"
echo "3. Monitor worker logs for processing"
echo "4. Check GitHub PR for review comments"

