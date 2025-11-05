# AI Code Review Agent - Development Plan

## Project Overview

**Goal:** Demonstrate backend SDE skills through event-driven architecture, async processing, and production-grade system design.

**Core Showcases:**
1. Event-driven webhook processing with job queue
2. Intelligent content-addressable caching
3. Comprehensive testing (unit + integration + load)

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11 + FastAPI |
| Database | PostgreSQL 15 |
| Cache/Queue | Redis 7 (Streams + TTL cache) |
| LLM | OpenAI GPT-4 or Anthropic Claude |
| Testing | pytest + pytest-asyncio + locust |
| Deployment | Docker + Railway/Render |

---

## System Architecture

```
GitHub Webhook → FastAPI → Redis Queue → Worker Pool → GitHub
                    ↓           ↓            ↓            ↑
                PostgreSQL   Cache      OpenAI API    Results
```

---

## Month 1: Core System (Weeks 1-4)

### Week 1: Foundation
- [x] Project setup (Poetry, FastAPI skeleton)
  - ✅ Poetry configuration with all dependencies
  - ✅ FastAPI application structure
  - ✅ Project structure (app/, migrations/, tests/)
  - ✅ Docker Compose setup
  - ✅ Git repository initialized and pushed to GitHub
  - ✅ Start script created
- [x] PostgreSQL schema (`pull_requests`, `reviews` tables)
  - ✅ Database schema created in `migrations/001_initial_schema.sql`
  - ✅ All tables and indexes created
  - ✅ Schema applied to database
- [x] Redis connection
  - ✅ Redis client module created (`app/db/redis_client.py`)
  - ✅ Connection pool management implemented
- [x] Environment config
  - ✅ Pydantic settings configuration
  - ✅ Environment variables setup
  - ✅ `.env` file template created
  - ✅ Configuration documentation

**Progress:** 100% complete ✅
**Deliverable:** Basic app with DB connections working ✅
- ✅ Docker Compose integration in startup scripts
- ✅ Connection retry logic implemented
- ✅ Services automatically managed on startup

### Week 2: Webhook Integration
- [x] GitHub webhook endpoint (`POST /webhooks/github`)
  - ✅ Endpoint created at `/webhooks/github`
  - ✅ Handles POST requests with proper headers
- [x] Signature verification (HMAC SHA-256)
  - ✅ HMAC SHA-256 verification implemented
  - ✅ Constant-time comparison to prevent timing attacks
  - ✅ Optional verification for development
- [x] Parse PR payloads
  - ✅ Extracts PR number, repository name, action
  - ✅ Handles pull_request events (opened, synchronize, reopened)
  - ✅ Validates payload structure
- [x] Store PR metadata in PostgreSQL
  - ✅ Stores new PRs in database
  - ✅ Updates existing PRs on subsequent events
  - ✅ Uses asyncpg for async database operations
  - ✅ Comprehensive error handling

**Progress:** 100% complete ✅
**Deliverable:** Endpoint receives webhooks and stores data ✅
- ✅ GitHub App successfully configured and receiving events
- ✅ FastAPI endpoint working and processing webhooks

### Week 3: Job Queue
- [x] Redis Streams producer (enqueue jobs)
  - ✅ Producer implemented with XADD
  - ✅ Job data serialization to JSON
  - ✅ Error handling and logging
- [x] Redis Streams consumer (worker loop)
  - ✅ Consumer loop with XREADGROUP
  - ✅ Message processing and acknowledgment
  - ✅ Pending message handling
  - ✅ Blocking reads with timeout
- [x] Job status tracking
  - ✅ Database status updates at each stage
  - ✅ Timestamp tracking
  - ✅ Status transitions logged
- [x] Worker lifecycle (startup/shutdown)
  - ✅ Signal handlers (SIGINT, SIGTERM)
  - ✅ Graceful shutdown
  - ✅ Startup scripts
- [x] Error handling & retries
  - ✅ Max 3 retries with exponential backoff
  - ✅ Dead letter queue
- [x] Observability & monitoring
  - ✅ Metrics endpoint
  - ✅ Admin dashboard with HTML UI
  - ✅ Structured logging

**Progress:** 100% complete ✅
**Deliverable:** Jobs flow webhook → queue → worker ✅
- ✅ Webhook returns <200ms after enqueueing
- ✅ Worker processes jobs asynchronously
- ✅ Full job lifecycle tracking
- ✅ Admin dashboard for monitoring

### Week 4: LLM Integration
- [x] Fetch PR diff from GitHub API
  - ✅ GitHub client with App authentication
  - ✅ Diff fetching and preprocessing
- [x] Multi-provider LLM support (Claude, OpenAI, Zhipu)
  - ✅ Provider abstraction interface
  - ✅ Anthropic (Claude) provider
  - ✅ OpenAI provider
  - ✅ Zhipu provider (for development)
- [x] Parse LLM response to structured comments
  - ✅ Response parser with code snippet support
  - ✅ Severity classification (critical, high, medium, low)
  - ✅ Issue grouping to avoid repetition
- [x] Post review comments to GitHub
  - ✅ GitHub App authentication
  - ✅ Comment formatting with severity badges
  - ✅ Code snippet support in comments
- [x] Error handling (API failures, rate limits)
  - ✅ Comprehensive error types
  - ✅ Retry logic in worker
- [x] Enhanced code review capabilities
  - ✅ Timeout detection for network requests
  - ✅ Database resource leak detection
  - ✅ Code quality improvement suggestions
  - ✅ Security vulnerability detection

**Deliverable:** Full flow working end-to-end ✅

---

## Month 2: Optimization (Weeks 5-8)

### Week 5: Content-Addressable Caching
- [ ] Cache key generation (SHA-256 hash)
- [ ] Check cache before LLM call
- [ ] Store results with 7-day TTL
- [ ] Track cache hit rate

**Deliverable:** Caching reduces redundant LLM calls

### Week 6: Concurrent Processing
- [ ] Bounded concurrency (asyncio semaphore, max 5)
- [ ] Token bucket rate limiter
- [ ] Exponential backoff for retries
- [ ] Handle GitHub API rate limits

**Deliverable:** System handles 50+ concurrent PRs

### Week 7: Metrics & Observability
- [ ] Structured logging (JSON format)
- [ ] Track: processing time, cache hit rate, API cost, errors
- [ ] Health check endpoint (check dependencies)
- [ ] Optional: Prometheus metrics

**Deliverable:** System is observable

### Week 8: Error Handling
- [ ] Retry logic for transient failures
- [ ] Dead letter queue for permanent failures
- [ ] Graceful shutdown
- [ ] Edge case handling (empty PR, binary files, huge PRs)

**Deliverable:** System handles failures gracefully

---

## Month 3: Production Hardening (Weeks 9-12)

### Week 9: Testing
- [ ] Unit tests (70%+ coverage)
- [ ] Integration tests (webhook → review flow)
- [ ] Mock external APIs (GitHub, OpenAI)
- [ ] Error scenario tests

**Deliverable:** Test suite passing with 70%+ coverage

### Week 10: Load Testing
- [ ] Write locust load test script
- [ ] Test 10, 50, 100 concurrent PRs
- [ ] Measure: throughput, latency (p50/p95/p99), error rate
- [ ] Optimize bottlenecks

**Deliverable:** System proven to handle 50+ PRs, <5s p95 latency

### Week 11: Real Usage
- [x] Deploy to Railway/Render
  - ✅ Railway web service deployed
  - ✅ Railway worker service deployed with health check
  - ✅ GitHub App webhook configured to Railway URL
  - ✅ Database auto-migrations working
  - ✅ Worker health check server integrated
- [ ] Install on your repositories (in progress)
- [ ] Review 50+ PRs across 3 projects
- [ ] Collect data: bugs found, false positives, costs
- [ ] Iterate on prompts based on feedback

**Progress:** 50% complete ✅
**Deliverable:** System deployed and running on Railway ✅

### Week 12: Documentation
- [x] README (overview, architecture diagram, setup, examples)
  - ✅ Project overview and architecture
  - ✅ Setup instructions
  - ✅ Tech stack documented
  - ✅ Project structure documented
- [ ] API documentation (OpenAPI/Swagger)
  - ✅ Auto-generated via FastAPI (available at /docs)
  - [ ] Custom documentation improvements needed
- [ ] Architecture Decision Records (ADRs)
- [ ] Demo video (3-5 minutes)
- [x] Clean commit history
  - ✅ Initial commit with proper structure
  - ✅ Documentation commit
- [ ] CI badge, screenshots

**Deliverable:** Professional, demo-ready repository (60% complete)

---

## Database Schema

```sql
-- Pull requests metadata
CREATE TABLE pull_requests (
  id SERIAL PRIMARY KEY,
  pr_number INT NOT NULL,
  repo_full_name VARCHAR(255) NOT NULL,
  status VARCHAR(50) NOT NULL,  -- pending, processing, completed, failed
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Review comments posted
CREATE TABLE reviews (
  id SERIAL PRIMARY KEY,
  pr_id INT REFERENCES pull_requests(id),
  file_path VARCHAR(500),
  line_number INT,
  comment_text TEXT,
  posted_at TIMESTAMP DEFAULT NOW()
);

-- Track feedback acceptance (optional, for learning)
CREATE TABLE review_feedback (
  id SERIAL PRIMARY KEY,
  review_id INT REFERENCES reviews(id),
  feedback_type VARCHAR(50),  -- accepted, ignored, helpful, unhelpful
  recorded_at TIMESTAMP DEFAULT NOW()
);
```

---

## Key Code Patterns

### Webhook Signature Verification
```python
def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

### Job Queue (Redis Streams)
```python
# Producer
async def enqueue_job(pr_id: int):
    await redis.xadd("review_jobs", {"pr_id": pr_id})

# Consumer
async def consume_jobs():
    while True:
        messages = await redis.xread({"review_jobs": ">"}, count=1, block=5000)
        for stream, msg_list in messages:
            for msg_id, data in msg_list:
                await process_review(data["pr_id"])
```

### Content-Addressable Cache
```python
def get_cache_key(file_path: str, content: str) -> str:
    hash = hashlib.sha256(content.encode()).hexdigest()[:12]
    return f"review:{file_path}:{hash}"

# Check cache
cache_key = get_cache_key(file_path, content)
cached = await redis.get(cache_key)
if cached:
    return json.loads(cached)  # Cache hit

# Cache miss - call LLM and store
result = await analyze_with_llm(content)
await redis.setex(cache_key, 604800, json.dumps(result))  # 7 day TTL
```

### Bounded Concurrency
```python
class ReviewWorker:
    def __init__(self, max_concurrent: int = 5):
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_pr(self, pr_id: int):
        async with self.semaphore:
            await self._do_review(pr_id)
```

### Token Bucket Rate Limiter
```python
class RateLimiter:
    def __init__(self, tokens_per_second: int):
        self.tokens = tokens_per_second
        self.rate = tokens_per_second
        self.last_update = time.time()
    
    async def acquire(self):
        while self.tokens < 1:
            await self._refill()
            await asyncio.sleep(0.1)
        self.tokens -= 1
    
    async def _refill(self):
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
        self.last_update = now
```

---

## Success Criteria

### Functional Completeness
- ✅ Webhook → queue → process → post comment (end-to-end works)
- ✅ Caching reduces redundant API calls
- ✅ Handles 50+ concurrent PRs without failures

### Code Quality
- ✅ 70%+ test coverage
- ✅ Clean, documented code
- ✅ Professional README with architecture diagram

### Real Usage
- ✅ Used on 50+ actual PRs
- ✅ Concrete metrics (cost, latency, bugs found)
- ✅ Examples of bugs caught with screenshots

### Interview Readiness
- ✅ Can explain technical decisions clearly
- ✅ Can demo in <5 minutes
- ✅ Can discuss trade-offs and improvements

---

## Key Metrics to Track

### Performance
- **Throughput:** PRs processed per minute
- **Latency:** p50, p95, p99 processing time
- **Cache Hit Rate:** % of LLM calls avoided

### Cost
- **Total Spent:** $ across all PRs
- **Cost Per PR:** Average $ per review
- **Cache Savings:** $ saved by caching

### Reliability
- **Success Rate:** % of PRs successfully reviewed
- **Error Recovery:** % of failures auto-recovered

### Real Usage
- **PRs Reviewed:** Total count across repositories
- **Bugs Found:** Count with specific examples
- **False Positive Rate:** % of unhelpful comments

---

## Interview Talking Points

**Event-Driven Architecture:**  
"Built event-driven system using GitHub webhooks and Redis Streams. Webhook responses stay under 200ms by queuing long-running analysis asynchronously."

**Concurrency:**  
"Used asyncio with bounded concurrency (semaphore limiting 5 simultaneous PRs) to maximize throughput without overwhelming APIs. Measured p95 latency at 4.1s for 50 concurrent PRs."

**Caching:**  
"Implemented content-addressable caching using SHA-256 hashes. Same file content reuses cached analysis, reducing API costs by 65%."

**Resilience:**  
"Built token bucket rate limiter with exponential backoff. System auto-recovers 87% of transient failures through retry logic."

**Testing:**  
"Comprehensive test suite with pytest-asyncio, mocking external APIs. Load tested with locust proving 50+ concurrent PR capacity."

---

## What We're NOT Building

| Feature | Why Not |
|---------|---------|
| AST parsing | Too complex, LLM handles it |
| Priority queue | FIFO is sufficient |
| Event sourcing | Over-engineered for scope |
| Adaptive rate limiting | Fixed bucket is simpler |
| Multi-language support | Focus on Python/JS |

---

## Dependencies

```toml
# pyproject.toml (Poetry)
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = "^0.24.0"
asyncpg = "^0.29.0"  # PostgreSQL async driver
redis = "^5.0.0"
httpx = "^0.25.0"  # Async HTTP client
openai = "^1.3.0"  # or anthropic
pydantic = "^2.5.0"
python-dotenv = "^1.0.0"
structlog = "^23.2.0"

[tool.poetry.dev-dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.1.0"
locust = "^2.17.0"
respx = "^0.20.0"  # HTTP mocking
```

---

## 📈 项目进度

**最后更新:** 2025-11-04

### 总体进度

| 阶段 | 完成度 | 状态 |
|------|--------|------|
| Week 1: Foundation | 100% | ✅ 完成 |
| Week 2: Webhook Integration | 100% | ✅ 完成 |
| Week 3: Job Queue | 100% | ✅ 完成 |
| Week 4: LLM Integration | 100% | ✅ 完成 |
| Week 5-8: Optimization | 0% | 🔄 待开始 |
| Week 9-12: Production Hardening | 0% | 🔄 待开始 |

**总体完成度:** ~33% (Week 1-4 完成，Week 5-12 待开始)

### 详细完成情况

#### Week 1: Foundation (100% ✅)
- ✅ Poetry 配置和依赖管理
- ✅ FastAPI 应用骨架和项目结构
- ✅ Docker Compose 配置（PostgreSQL 15, Redis 7）
- ✅ PostgreSQL schema 和迁移文件
- ✅ 数据库和 Redis 连接模块
- ✅ 环境配置（Pydantic Settings）
- ✅ 结构化日志（structlog）
- ✅ Git 仓库初始化和 GitHub 推送
- ✅ 启动脚本和 Docker 服务自动管理
- ✅ 连接重试逻辑

#### Week 2: Webhook Integration (100% ✅)
- ✅ GitHub webhook 端点 (`POST /webhooks/github`)
- ✅ HMAC SHA-256 签名验证
- ✅ PR payload 解析和验证
- ✅ PR 元数据存储到 PostgreSQL
- ✅ GitHub App 配置和事件接收
- ✅ 错误处理和日志记录

#### Week 3: Job Queue (100% ✅)
- ✅ Redis Streams producer (XADD)
- ✅ Redis Streams consumer (XREADGROUP)
- ✅ Job 状态跟踪和数据库更新
- ✅ Worker 生命周期管理（信号处理、优雅关闭）
- ✅ 错误处理和重试逻辑（最多 3 次，指数退避）
- ✅ Dead letter queue
- ✅ 管理仪表板（HTML UI）
- ✅ Metrics 端点和可观测性

#### Week 4: LLM Integration (100% ✅)
- ✅ 多提供商 LLM 抽象（Claude, OpenAI, Zhipu）
- ✅ GitHub App 认证（JWT + installation token）
- ✅ PR diff 获取和预处理
- ✅ LLM 响应解析（严重性分类、代码片段、问题分组）
- ✅ 评论发布到 GitHub PR（带严重性徽章和代码片段）
- ✅ 增强的代码审查能力：
  - ✅ 网络请求超时检测
  - ✅ 数据库资源泄漏检测
  - ✅ 代码质量改进建议
  - ✅ 安全漏洞检测
- ✅ 端到端流程测试

### 已知问题和解决方案

#### ✅ 数据库连接问题（已解决）
**问题:** 应用启动时无法连接到 PostgreSQL  
**解决方案:**
- ✅ 添加连接重试逻辑（5 次重试，每次间隔 2 秒）
- ✅ 创建启动脚本自动管理 Docker Compose 服务
- ✅ `start.sh` 和 `scripts/start-dev.sh` 自动启动并等待 Docker 服务就绪

**使用方法:**
```bash
# 推荐方式：自动启动 Docker 服务
./scripts/start-dev.sh

# 或使用简单启动脚本
./start.sh
```

### 关键指标

#### 代码统计
- **总文件数:** 25+
- **代码行数:** ~4,000+
- **测试覆盖率:** 0% (待开始)

#### 功能完成度
- **基础设施:** 100% ✅
- **Webhook 集成:** 100% ✅
- **Job Queue 系统:** 100% ✅
- **LLM 集成:** 100% ✅
- **核心功能:** 100% (完整端到端流程) ✅
- **测试:** 0% (待开始)
- **文档:** 85%
- **管理仪表板:** 100% ✅

### 相关链接

- **GitHub 仓库:** https://github.com/kaitlynmi/ai-code-review-agent
- **本地应用:** http://localhost:8000
- **API 文档:** http://localhost:8000/docs
- **管理仪表板:** http://localhost:8000/admin

---

## Project Timeline

- **Month 1:** Core system working end-to-end (Week 1: 100%, Week 2: 100%, Week 3: 100%, Week 4: 100% ✅)
- **Month 2:** Optimization (caching, concurrency, observability) (0%)
- **Month 3:** Testing, real usage, documentation (0%)

**Total:** 12 weeks to demo-ready portfolio project (33% complete)