"""Entry point for running the worker as a module: python -m app.queue.consumer"""

import asyncio
import sys
import os

# Ensure unbuffered output for Railway logging
os.environ.setdefault('PYTHONUNBUFFERED', '1')

# Print to both stdout and stderr for visibility
def log(msg):
    print(msg, file=sys.stderr)
    print(msg, file=sys.stdout)
    sys.stdout.flush()
    sys.stderr.flush()

log("=" * 60)
log("🔧 Worker startup - Step 1: Initializing...")
log("=" * 60)

# Setup logging first - this is critical
try:
    log("📝 Setting up logging...")
    from app.core.logging import setup_logging
    setup_logging()
    log("✅ Logging setup complete")
except Exception as e:
    log(f"❌ Logging setup failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    log("📦 Importing worker module...")
    from app.queue.consumer import run_worker
    log("✅ Worker module imported successfully")
    log(f"   run_worker function: {run_worker}")
except Exception as e:
    log(f"❌ Failed to import worker: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    log("=" * 60)
    log("🚀 Starting worker process...")
    log("=" * 60)
    try:
        log("⚙️  Calling asyncio.run(run_worker())...")
        asyncio.run(run_worker())
        log("⚠️  asyncio.run() returned (unexpected)")
    except KeyboardInterrupt:
        log("\n⚠️  Worker stopped by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        log(f"❌ Fatal error in worker: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        log("=" * 60)
        log("🛑 Worker process ended")
        log("=" * 60)
