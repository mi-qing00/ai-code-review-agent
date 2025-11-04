# AI Code Review Agent

Event-driven AI code review system that processes GitHub pull requests using webhooks, job queues, and LLM-powered analysis.

## 🎯 Project Overview

This project demonstrates backend SDE skills through:

- **Event-driven architecture** with GitHub webhooks and Redis Streams
- **Intelligent caching** using content-addressable storage
- **Comprehensive testing** (unit + integration + load testing)
- **Production-grade** system design with observability

## 🏗️ Architecture

```
GitHub Webhook → FastAPI → Redis Queue → Worker Pool → GitHub
                    ↓           ↓            ↓            ↑
                PostgreSQL   Cache      OpenAI API    Results
```

## 🛠️ Tech Stack

- **Backend:** Python 3.11 + FastAPI
- **Database:** PostgreSQL 15
- **Cache/Queue:** Redis 7 (Streams + TTL cache)
- **LLM:** OpenAI GPT-4 or Anthropic Claude
- **Testing:** pytest + pytest-asyncio + locust
- **Deployment:** Docker + Railway/Render

## 📋 Prerequisites

- Python 3.11+
- Poetry (for dependency management)
- PostgreSQL 15
- Redis 7

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
```

### 2. Setup Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
# - DATABASE_URL: PostgreSQL connection string
# - REDIS_URL: Redis connection string
# - GITHUB_WEBHOOK_SECRET: Secret for webhook verification
# - GITHUB_TOKEN: GitHub personal access token
# - OPENAI_API_KEY: OpenAI API key
```

### 3. Setup Database

```bash
# Create database
createdb code_review_db

# Run migrations
psql -d code_review_db -f migrations/001_initial_schema.sql
```

### 4. Run Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or using local Redis
redis-server
```

### 5. Start the Application

```bash
# Method 1: Using the development script (recommended - automatically starts Docker services)
./scripts/start-dev.sh

# Method 2: Using the simple start script (requires Docker services already running)
./start.sh

# Method 3: Manual start (requires Docker services already running)
# First, ensure Docker services are running:
docker-compose up -d

# Then start the application:
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Method 4: Activate Poetry shell first
poetry shell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**重要提示：** 
- 应用入口是 `app.main:app`，不是 `main:app`
- 推荐使用 `./scripts/start-dev.sh`，它会自动启动 Docker Compose 服务
- 如果使用其他方法，请确保 Docker 服务已运行：`docker-compose up -d`

The API will be available at `http://localhost:8000`

- **API docs:** `http://localhost:8000/docs`
- **Health check:** `http://localhost:8000/health`
- **Admin Dashboard:** `http://localhost:8000/api/admin/dashboard` 🎯
- **Queue metrics:** `http://localhost:8000/api/metrics`

### 6. Start the Worker (for processing jobs)

In a separate terminal, start the worker to process jobs from the queue:

```bash
# Start the worker
./scripts/start-worker.sh

# Or manually:
poetry run python -m app.queue.consumer
```

The worker will:
- Connect to Redis and read jobs from the stream
- Process PR review jobs asynchronously
- Update job status in the database
- Handle retries and failures gracefully

### 7. Testing

Run the automated test script:

```bash
./scripts/test_queue.sh
```

Or follow the manual testing guide: `docs/TESTING_GUIDE.md`

Quick test:
```bash
# 1. Send a test webhook
curl -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=..." \
  -H "X-GitHub-Event: pull_request" \
  -d '{"action":"opened","pull_request":{"number":123},"repository":{"full_name":"test/repo"}}'

# 2. Check queue metrics
curl http://localhost:8000/api/metrics

# 3. Check database
docker exec code_review_postgres psql -U user -d code_review_db -c "SELECT * FROM pull_requests;"
```

## 📁 Project Structure

```
.
├── app/
│   ├── api/           # API routes and endpoints
│   ├── core/          # Configuration and utilities
│   ├── db/            # Database connections
│   ├── models/        # Data models and schemas
│   ├── services/      # Business logic services
│   └── workers/       # Background workers
├── migrations/        # Database migrations
├── tests/             # Test suite
├── pyproject.toml     # Poetry dependencies
└── README.md
```

## 🔄 Development Roadmap

### Month 1: Core System
- [x] Project setup and foundation
- [ ] Webhook integration
- [ ] Job queue (Redis Streams)
- [ ] LLM integration

### Month 2: Optimization
- [ ] Content-addressable caching
- [ ] Concurrent processing
- [ ] Metrics & observability
- [ ] Error handling

### Month 3: Production Hardening
- [ ] Comprehensive testing
- [ ] Load testing
- [ ] Real usage deployment
- [ ] Documentation

## 🧪 Testing

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run load tests
poetry run locust -f tests/load_test.py
```

## 📊 Key Metrics

- **Throughput:** PRs processed per minute
- **Latency:** p50, p95, p99 processing time
- **Cache Hit Rate:** % of LLM calls avoided
- **Success Rate:** % of PRs successfully reviewed

## 📝 License

MIT

## 🤝 Contributing

This is a portfolio project. For questions or feedback, please open an issue.

