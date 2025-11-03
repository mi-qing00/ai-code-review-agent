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
- [ ] Project setup (Poetry, FastAPI skeleton)
- [ ] PostgreSQL schema (`pull_requests`, `reviews` tables)
- [ ] Redis connection
- [ ] Environment config

**Deliverable:** Basic app with DB connections working

### Week 2: Webhook Integration
- [ ] GitHub webhook endpoint (`POST /webhooks/github`)
- [ ] Signature verification (HMAC SHA-256)
- [ ] Parse PR payloads
- [ ] Store PR metadata in PostgreSQL

**Deliverable:** Endpoint receives webhooks and stores data

### Week 3: Job Queue
- [ ] Redis Streams producer (enqueue jobs)
- [ ] Redis Streams consumer (worker loop)
- [ ] Job status tracking
- [ ] Worker lifecycle (startup/shutdown)

**Deliverable:** Jobs flow webhook → queue → worker

### Week 4: LLM Integration
- [ ] Fetch PR diff from GitHub API
- [ ] Call OpenAI with diff (simple prompt)
- [ ] Parse LLM response to structured comments
- [ ] Post review comments to GitHub
- [ ] Error handling (API failures, rate limits)

**Deliverable:** Full flow working end-to-end

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
- [ ] Deploy to Railway/Render
- [ ] Install on your repositories
- [ ] Review 50+ PRs across 3 projects
- [ ] Collect data: bugs found, false positives, costs
- [ ] Iterate on prompts based on feedback

**Deliverable:** Real usage metrics and examples

### Week 12: Documentation
- [ ] README (overview, architecture diagram, setup, examples)
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Architecture Decision Records (ADRs)
- [ ] Demo video (3-5 minutes)
- [ ] Clean commit history, CI badge, screenshots

**Deliverable:** Professional, demo-ready repository

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

## Project Timeline

- **Month 1:** Core system working end-to-end
- **Month 2:** Optimization (caching, concurrency, observability)
- **Month 3:** Testing, real usage, documentation

**Total:** 12 weeks to demo-ready portfolio project