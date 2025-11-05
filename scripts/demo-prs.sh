#!/bin/bash
# Script to create demo PRs for AI Code Review Agent showcase
# This script creates multiple PRs with intentional issues for demonstration

set -e

REPO_NAME="pr-review-demo"
GITHUB_APP_NAME="ai-code-review-agent-dev"
DEMO_DIR="../pr-review-demo"

echo "🚀 Creating demo PRs for AI Code Review Agent..."

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed."
    echo "   Install it from: https://cli.github.com/"
    exit 1
fi

# Check if gh is authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ GitHub CLI is not authenticated."
    echo "   Run: gh auth login"
    exit 1
fi

# Get current directory and GitHub username
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# Get GitHub username
GITHUB_USER=$(gh api user --jq .login 2>/dev/null || echo "")

if [ -z "$GITHUB_USER" ]; then
    echo "❌ Could not get GitHub username. Please check your GitHub CLI authentication."
    exit 1
fi

echo "📋 GitHub User: $GITHUB_USER"
echo "📋 Target Repository: $GITHUB_USER/$REPO_NAME"

# Create demo directory in parent directory (outside current project)
DEMO_DIR_ABS="$(cd "$PROJECT_DIR/.." && pwd)/$REPO_NAME"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Setting up demo repository directory..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if demo directory exists and is the correct repo
if [ -d "$DEMO_DIR_ABS" ]; then
    echo "📁 Demo directory exists: $DEMO_DIR_ABS"
    cd "$DEMO_DIR_ABS"
    
    # Check if it's a git repo and if remote matches
    if [ -d .git ]; then
        CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
        EXPECTED_REMOTE="https://github.com/$GITHUB_USER/$REPO_NAME.git"
        
        if [[ "$CURRENT_REMOTE" == *"$REPO_NAME"* ]]; then
            echo "✅ Found existing demo repository"
        else
            echo "⚠️  Directory exists but is not the demo repo. Removing and recreating..."
            cd "$PROJECT_DIR/.."
            rm -rf "$DEMO_DIR_ABS"
        fi
    fi
fi

# Create directory if it doesn't exist
if [ ! -d "$DEMO_DIR_ABS" ]; then
    echo "📁 Creating new demo directory: $DEMO_DIR_ABS"
    mkdir -p "$DEMO_DIR_ABS"
    cd "$DEMO_DIR_ABS"
    
    echo "📦 Initializing git repository..."
    git init
    echo "# AI Code Review Demo" > README.md
    git add README.md
    git commit -m "Initial commit" || true
    
    echo "📦 Creating GitHub repository: $REPO_NAME"
    gh repo create "$REPO_NAME" --public --description "Demo of AI Code Review Agent" --source=. --remote=origin --push || {
        echo "⚠️  Repository might already exist. Trying to use existing repo..."
        # Try to add remote if repo exists but remote not set
        if ! git remote get-url origin &> /dev/null; then
            git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"
            git push -u origin main || git push -u origin master || true
        fi
    }
else
    cd "$DEMO_DIR_ABS"
    echo "✅ Using existing demo repository"
fi

# Ensure we're on main branch
git checkout -b main 2>/dev/null || git checkout main || true
git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || true

echo "✅ Demo repository ready: $DEMO_DIR_ABS"

# Ensure we're in the demo directory
cd "$DEMO_DIR_ABS"

# Verify we're in the correct repo
CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
if [[ ! "$CURRENT_REMOTE" == *"$REPO_NAME"* ]]; then
    echo "❌ Error: Not in the correct repository!"
    echo "   Current remote: $CURRENT_REMOTE"
    echo "   Expected: *$REPO_NAME*"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 Creating Demo PR #1: Security Issues"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

git checkout -b demo/security-issues 2>/dev/null || git checkout demo/security-issues

cat > insecure_auth.py << 'EOF'
"""
Authentication module with intentional security vulnerabilities for demo purposes.
This code demonstrates common security issues that AI code review can detect.
"""

import hashlib
import os


def login(username, password):
    """
    Authenticate user - contains SQL injection vulnerability.
    
    ⚠️ SECURITY ISSUE: Direct string interpolation in SQL query
    """
    query = f"SELECT * FROM users WHERE name='{username}' AND pass='{password}'"
    # SQL injection vulnerability - attacker can inject malicious SQL
    return execute_query(query)


def hash_password(password):
    """
    Hash password using MD5 - weak and deprecated.
    
    ⚠️ SECURITY ISSUE: MD5 is cryptographically broken
    """
    return hashlib.md5(password.encode()).hexdigest()
    # Should use bcrypt, argon2, or PBKDF2 instead


def store_api_key(api_key):
    """
    Store API key in plain text.
    
    ⚠️ SECURITY ISSUE: Sensitive data stored in plain text
    """
    with open("api_keys.txt", "w") as f:
        f.write(api_key)
    # Should use environment variables or secure key management


def get_secret_key():
    """
    Hardcoded secret key.
    
    ⚠️ SECURITY ISSUE: Hardcoded secret in source code
    """
    return "my-secret-key-12345"
    # Should use environment variables or secure configuration
EOF

git add insecure_auth.py
git commit -m "Add authentication module with security issues (demo)" || true
git push origin demo/security-issues -f || true

gh pr create \
    --title "🔐 Demo: Security Issues" \
    --body "This PR contains intentional security vulnerabilities for demo purposes:

- SQL injection vulnerability in login function
- Weak MD5 password hashing
- Plain text API key storage
- Hardcoded secret key

**This is a demonstration PR. The AI Code Review Agent should detect these issues.**" \
    --base main || echo "⚠️  PR might already exist. Check GitHub repository."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 Creating Demo PR #2: Performance Issues"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

git checkout main
git checkout -b demo/performance-issues 2>/dev/null || git checkout demo/performance-issues

cat > slow_processor.py << 'EOF'
"""
Data processing module with intentional performance issues for demo purposes.
This code demonstrates performance problems that AI code review can detect.
"""


def find_duplicates(items):
    """
    Find duplicate items - O(n²) complexity.
    
    ⚠️ PERFORMANCE ISSUE: Inefficient nested loop
    """
    duplicates = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i] == items[j]:
                duplicates.append(items[i])
    return duplicates
    # Should use set() for O(n) complexity: return list(set(items))


def process_data(data):
    """
    Process data with inefficient membership check.
    
    ⚠️ PERFORMANCE ISSUE: list membership check is O(n)
    """
    result = []
    for item in data:
        if item not in result:  # O(n) operation inside loop = O(n²)
            result.append(item)
    return result
    # Should use set: result = list(dict.fromkeys(data))


def search_items(items, target):
    """
    Linear search in unsorted list.
    
    ⚠️ PERFORMANCE ISSUE: Should use binary search or hash table
    """
    for item in items:
        if item == target:
            return True
    return False
    # For sorted list: use bisect.bisect_left()
    # For unsorted: use set for O(1) lookup


def concatenate_strings(strings):
    """
    String concatenation in loop.
    
    ⚠️ PERFORMANCE ISSUE: String concatenation creates new objects
    """
    result = ""
    for s in strings:
        result += s  # Creates new string object each time
    return result
    # Should use: "".join(strings)
EOF

git add slow_processor.py
git commit -m "Add data processor with performance issues (demo)" || true
git push origin demo/performance-issues -f || true

gh pr create \
    --title "⚡ Demo: Performance Issues" \
    --body "This PR contains performance problems for demo purposes:

- O(n²) duplicate finding algorithm
- Inefficient list membership checks
- Linear search instead of hash table
- String concatenation in loop

**This is a demonstration PR. The AI Code Review Agent should detect these issues.**" \
    --base main || echo "⚠️  PR might already exist. Check GitHub repository."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 Creating Demo PR #3: Error Handling Issues"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

git checkout main
git checkout -b demo/error-handling 2>/dev/null || git checkout demo/error-handling

cat > calculator.py << 'EOF'
"""
Calculator module with intentional error handling issues for demo purposes.
This code demonstrates missing error handling that AI code review can detect.
"""

import json


def divide(a, b):
    """
    Division without zero check.
    
    ⚠️ ERROR HANDLING: No check for division by zero
    """
    return a / b  # Will raise ZeroDivisionError if b == 0


def parse_config(text):
    """
    Parse JSON without error handling.
    
    ⚠️ ERROR HANDLING: No try-except for JSON parsing
    """
    return json.loads(text)  # Will raise JSONDecodeError for invalid JSON


def get_item(items, index):
    """
    Access list item without bounds check.
    
    ⚠️ ERROR HANDLING: No check for index out of bounds
    """
    return items[index]  # Will raise IndexError if index >= len(items)


def open_file(path):
    """
    Open file without error handling.
    
    ⚠️ ERROR HANDLING: No handling for file not found or permission errors
    """
    with open(path, 'r') as f:
        return f.read()  # Will raise FileNotFoundError if path doesn't exist


def process_user_input(user_input):
    """
    Process input without validation.
    
    ⚠️ ERROR HANDLING: No input validation
    """
    number = int(user_input)  # Will raise ValueError for non-numeric input
    return number * 2
EOF

git add calculator.py
git commit -m "Add calculator with missing error handling (demo)" || true
git push origin demo/error-handling -f || true

gh pr create \
    --title "⚠️  Demo: Missing Error Handling" \
    --body "This PR has missing error handling for demo purposes:

- Division by zero not checked
- JSON parsing without try-except
- Array index out of bounds not validated
- File operations without error handling
- User input validation missing

**This is a demonstration PR. The AI Code Review Agent should detect these issues.**" \
    --base main || echo "⚠️  PR might already exist. Check GitHub repository."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Demo PRs created successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Next Steps"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Install GitHub App:"
echo "   https://github.com/apps/$GITHUB_APP_NAME"
echo "   - Click 'Configure' or 'Install App'"
echo "   - Select 'Only select repositories'"
echo "   - Add '$REPO_NAME' to allowed repositories"
echo "   - Click 'Install'"
echo ""
echo "⚠️  IMPORTANT: If you install the App AFTER running this script,"
echo "   existing PRs will NOT be automatically reviewed!"
echo ""
echo "   To trigger reviews for existing PRs:"
echo "   - Option 1: Close and reopen each PR (recommended)"
echo "   - Option 2: Push a new commit to each PR branch"
echo ""
REPO_URL="https://github.com/$GITHUB_USER/$REPO_NAME"
echo "🔗 Demo Repository: $REPO_URL"
echo "📁 Local Directory: $DEMO_DIR_ABS"
echo ""
echo "📝 Created PRs:"
echo "   - $REPO_URL/pulls"
echo ""

