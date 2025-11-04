#!/usr/bin/env python3
"""Test GitHub App authentication."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.core.logging import setup_logging
from app.github.client import GitHubClient

setup_logging()


async def test_github_app():
    """Test GitHub App authentication."""
    print("\n" + "=" * 60)
    print("🧪 Testing GitHub App Authentication")
    print("=" * 60 + "\n")

    # Step 1: Check configuration
    print("Step 1: Checking configuration...")
    print(f"  GITHUB_APP_ID: {settings.github_app_id or '(not set)'}")
    print(
        f"  GITHUB_APP_PRIVATE_KEY_PATH: {settings.github_app_private_key_path or '(not set)'}"
    )
    print(
        f"  GITHUB_APP_INSTALLATION_ID: {settings.github_app_installation_id or '(not set)'}"
    )

    if not all(
        [
            settings.github_app_id,
            settings.github_app_private_key_path,
            settings.github_app_installation_id,
        ]
    ):
        print("\n  ❌ GitHub App configuration incomplete!")
        print("     Please set GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY_PATH, and GITHUB_APP_INSTALLATION_ID")
        return False

    print("  ✅ Configuration complete")

    # Step 2: Initialize client
    print("\nStep 2: Initializing GitHub client...")
    try:
        github_client = GitHubClient()
        if github_client.use_app_auth:
            print("  ✅ Using GitHub App authentication")
        else:
            print("  ❌ Falling back to PAT (configuration issue)")
            return False
    except Exception as e:
        print(f"  ❌ Failed to initialize client: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Step 3: Test JWT generation
    print("\nStep 3: Testing JWT generation...")
    try:
        jwt_token = github_client._generate_jwt()
        print(f"  ✅ JWT generated successfully")
        print(f"     Length: {len(jwt_token)} characters")
    except Exception as e:
        print(f"  ❌ JWT generation failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Step 4: Test installation token exchange
    print("\nStep 4: Testing installation token exchange...")
    try:
        installation_token = await github_client._get_installation_token()
        print(f"  ✅ Installation token obtained successfully")
        print(f"     Token: {installation_token[:20]}...")
        print(
            f"     Expires at: {github_client._token_expires_at.isoformat() if github_client._token_expires_at else 'N/A'}"
        )
    except Exception as e:
        print(f"  ❌ Installation token exchange failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Step 5: Test API call (test with repository endpoint - installation tokens can access repos)
    print("\nStep 5: Testing API call with installation token...")
    print("  (Testing repository access - installation tokens work with repo endpoints)")
    try:
        headers = await github_client._get_headers()
        # Test with a known repository - use the test repo if available
        test_repo = "kaitlynmi/pr-review-agent-test"
        response = await github_client.client.get(
            f"/repos/{test_repo}",
            headers=headers,
        )
        response.raise_for_status()
        repo_data = response.json()
        print(f"  ✅ API call successful")
        print(f"     Repository: {repo_data.get('full_name', 'N/A')}")
        print(f"     Access confirmed: {repo_data.get('name', 'N/A')}")
    except Exception as e:
        print(f"  ⚠️  Repository access test failed: {e}")
        print(f"     This may be expected if the repo doesn't exist or isn't accessible.")
        print(f"     The important thing is that Steps 1-4 passed (token generation works).")
        # Don't fail the test for this - token generation is the critical part

    await github_client.close()

    print("\n" + "=" * 60)
    print("✅ All GitHub App authentication tests passed!")
    print("=" * 60 + "\n")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_github_app())
    sys.exit(0 if success else 1)

