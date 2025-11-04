#!/usr/bin/env python3
"""End-to-end test script for the code review agent."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.core.logging import setup_logging
from app.github.client import GitHubClient
from app.llm.factory import get_llm_provider

setup_logging()


async def test_end_to_end(repo_full_name: str, pr_number: int):
    """Test complete review flow."""
    print(f"\n{'='*60}")
    print(f"🧪 End-to-End Test: {repo_full_name} PR #{pr_number}")
    print(f"{'='*60}\n")

    github_client = None
    try:
        # Step 1: Verify configuration
        print("Step 1: Verifying configuration...")
        try:
            llm_config = settings.get_llm_config()
            print(f"  ✅ LLM Provider: {llm_config['provider']}")
            print(f"  ✅ Model: {llm_config['model']}")
        except Exception as e:
            print(f"  ❌ Configuration error: {e}")
            return False

        # Step 2: Verify GitHub App configuration
        print(f"\nStep 2: Verifying GitHub authentication...")
        if (
            settings.github_app_id
            and settings.github_app_private_key_path
            and settings.github_app_installation_id
        ):
            print(f"  ✅ GitHub App configured:")
            print(f"     - App ID: {settings.github_app_id}")
            print(f"     - Key Path: {settings.github_app_private_key_path}")
            print(f"     - Installation ID: {settings.github_app_installation_id}")
        else:
            print(f"  ⚠️  GitHub App not fully configured, will use PAT (may have limited permissions)")
            missing = []
            if not settings.github_app_id:
                missing.append("GITHUB_APP_ID")
            if not settings.github_app_private_key_path:
                missing.append("GITHUB_APP_PRIVATE_KEY_PATH")
            if not settings.github_app_installation_id:
                missing.append("GITHUB_APP_INSTALLATION_ID")
            print(f"     Missing: {', '.join(missing)}")

        # Step 3: Fetch PR diff
        print(f"\nStep 3: Fetching PR diff from GitHub...")
        github_client = GitHubClient()
        try:
            diff_context = await github_client.fetch_pr_diff(repo_full_name, pr_number)
            print(f"  ✅ Diff fetched:")
            print(f"     - Files: {len(diff_context.changed_files)}")
            print(f"     - Additions: {diff_context.additions}")
            print(f"     - Deletions: {diff_context.deletions}")
            print(f"     - Diff size: {len(diff_context.diff_text)} chars")
            if diff_context.changed_files:
                print(f"     - Files: {', '.join(diff_context.changed_files[:3])}")
        except Exception as e:
            print(f"  ❌ Failed to fetch diff: {e}")
            return False

        # Step 4: Analyze with LLM
        print(f"\nStep 4: Analyzing diff with LLM...")
        try:
            llm_provider = get_llm_provider()
            print(f"  ✅ Using provider: {llm_provider.provider_name} ({llm_provider.model})")

            review_result = await llm_provider.analyze_diff(
                diff_text=diff_context.diff_text,
                context=diff_context,
            )

            print(f"  ✅ Analysis completed:")
            print(f"     - Comments: {len(review_result.comments)}")
            print(f"     - Tokens: {review_result.tokens_used}")
            print(f"     - Cost: ${review_result.cost:.4f}")
            print(f"     - Time: {review_result.processing_time:.2f}s")

            if review_result.comments:
                print(f"\n  📝 Review comments:")
                for i, comment in enumerate(review_result.comments[:5], 1):
                    print(
                        f"     {i}. {comment.file_path}:{comment.line_number} "
                        f"({comment.severity}): {comment.comment_text[:60]}..."
                    )
                if len(review_result.comments) > 5:
                    print(f"     ... and {len(review_result.comments) - 5} more")
        except Exception as e:
            print(f"  ❌ LLM analysis failed: {e}")
            import traceback

            traceback.print_exc()
            return False

        # Step 5: Post comments (optional - comment out to skip)
        print(f"\nStep 5: Posting comments to GitHub...")
        post_comments = input("  Post comments to GitHub? (y/N): ").strip().lower() == "y"

        if post_comments and review_result.comments:
            try:
                post_result = await github_client.post_review_comments(
                    repo_full_name=repo_full_name,
                    pr_number=pr_number,
                    comments=review_result.comments,
                )
                print(f"  ✅ Posted {post_result.get('posted_count', 0)} comments")
            except Exception as e:
                print(f"  ⚠️  Failed to post comments: {e}")
                print(f"     (This is okay for testing - review was generated successfully)")
        else:
            print(f"  ⏭️  Skipping comment posting")

        print(f"\n{'='*60}")
        print(f"✅ End-to-end test completed successfully!")
        print(f"{'='*60}\n")
        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        if github_client:
            await github_client.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_end_to_end.py <repo_full_name> <pr_number>")
        print("Example: python test_end_to_end.py kaitlynmi/pr-review-agent-test 1")
        sys.exit(1)

    repo_full_name = sys.argv[1]
    pr_number = int(sys.argv[2])

    success = asyncio.run(test_end_to_end(repo_full_name, pr_number))
    sys.exit(0 if success else 1)

