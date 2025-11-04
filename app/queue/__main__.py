"""Entry point for running the worker as a module: python -m app.queue.consumer"""

import asyncio
import sys

# Setup logging first - this is critical
from app.core.logging import setup_logging
setup_logging()

print("🔧 Initializing worker...", file=sys.stderr)

try:
    from app.queue.consumer import run_worker
    print("✅ Worker module imported successfully", file=sys.stderr)
except Exception as e:
    print(f"❌ Failed to import worker: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    print("🚀 Starting worker process...", file=sys.stderr)
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        print("\n⚠️  Worker stopped by user (Ctrl+C)", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error in worker: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
