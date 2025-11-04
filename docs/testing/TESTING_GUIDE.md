# Testing Guide - Job Queue System

## 测试环境准备

### 1. 启动服务

```bash
# Terminal 1: 启动 FastAPI 应用
./scripts/start-dev.sh

# Terminal 2: 启动 Worker
./scripts/start-worker.sh

# 验证服务都在运行
curl http://localhost:8000/health
curl http://localhost:8000/api/health/queue
```

### 2. 检查数据库和 Redis

```bash
# 检查 PostgreSQL
docker exec code_review_postgres psql -U user -d code_review_db -c "SELECT COUNT(*) FROM pull_requests;"

# 检查 Redis
docker exec code_review_redis redis-cli PING
docker exec code_review_redis redis-cli XLEN review_jobs
```

---

## 测试场景

### 场景 1: 测试 Webhook 入队（Task 3.3）

#### 1.1 发送测试 Webhook

```bash
# 生成测试签名
SECRET="your_webhook_secret_here"  # 从 .env 文件获取
PAYLOAD='{"action":"opened","pull_request":{"number":999,"title":"Test PR"},"repository":{"full_name":"test/repo"}}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | sed 's/^.* //')
SIGNATURE="sha256=$SIGNATURE"

# 发送请求
curl -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: $SIGNATURE" \
  -H "X-GitHub-Event: pull_request" \
  -d "$PAYLOAD"
```

**预期结果：**
- 返回 200 OK
- 响应时间 < 200ms
- 响应包含 `job_id`

#### 1.2 验证作业已入队

```bash
# 检查 Redis Stream 长度
docker exec code_review_redis redis-cli XLEN review_jobs

# 查看队列中的消息
docker exec code_review_redis redis-cli XRANGE review_jobs - + COUNT 5
```

**预期结果：**
- Stream 长度 > 0
- 能看到刚入队的作业数据

#### 1.3 检查数据库状态

```bash
docker exec code_review_postgres psql -U user -d code_review_db -c \
  "SELECT id, pr_number, repo_full_name, status, job_id, enqueued_at FROM pull_requests ORDER BY created_at DESC LIMIT 5;"
```

**预期结果：**
- `status` = `queued`
- `job_id` 不为 NULL
- `enqueued_at` 有值

---

### 场景 2: 测试 Worker 处理（Task 3.4）

#### 2.1 观察 Worker 日志

Worker 终端应该显示：
```
[info] Starting consumer worker-1 in group review_workers
[info] Processing job <job_id> for PR #999 from test/repo (attempt 1)
[info] Job <job_id> completed successfully for PR #999
```

#### 2.2 验证作业被处理

```bash
# 检查数据库状态变化
docker exec code_review_postgres psql -U user -d code_review_db -c \
  "SELECT id, pr_number, status, processing_started_at, completed_at FROM pull_requests WHERE pr_number = 999;"
```

**预期结果：**
- `status` = `completed`
- `processing_started_at` 有值
- `completed_at` 有值

#### 2.3 检查 Redis Stream

```bash
# 检查 Consumer Group 状态
docker exec code_review_redis redis-cli XINFO GROUPS review_jobs

# 检查待处理消息
docker exec code_review_redis redis-cli XPENDING review_jobs review_workers
```

**预期结果：**
- 待处理消息数量为 0（已处理完成）

---

### 场景 3: 端到端测试（完整流程）

#### 3.1 发送多个 PR Webhooks

```bash
# 创建测试脚本
cat > test_webhooks.sh << 'EOF'
#!/bin/bash
SECRET="your_webhook_secret_here"
for i in {1..5}; do
  PAYLOAD="{\"action\":\"opened\",\"pull_request\":{\"number\":$i},\"repository\":{\"full_name\":\"test/repo\"}}"
  SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | sed 's/^.* //')
  curl -X POST http://localhost:8000/webhooks/github \
    -H "Content-Type: application/json" \
    -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
    -H "X-GitHub-Event: pull_request" \
    -d "$PAYLOAD" \
    -w "\nTime: %{time_total}s\n"
  sleep 0.5
done
EOF

chmod +x test_webhooks.sh
./test_webhooks.sh
```

**预期结果：**
- 所有请求都快速返回（< 200ms）
- 每个响应都有唯一的 `job_id`

#### 3.2 观察 Worker 处理

在 Worker 终端观察：
- 作业被顺序处理
- 每个作业都有日志记录
- 处理时间合理

#### 3.3 验证最终状态

```bash
# 等待所有作业处理完成（约 5-10 秒）
sleep 10

# 检查所有作业状态
docker exec code_review_postgres psql -U user -d code_review_db -c \
  "SELECT pr_number, status, enqueued_at, processing_started_at, completed_at FROM pull_requests WHERE repo_full_name = 'test/repo' ORDER BY pr_number;"
```

**预期结果：**
- 所有作业状态为 `completed`
- 时间戳正确记录

---

### 场景 4: 测试重试逻辑（Task 3.7）

#### 4.1 创建会失败的作业

修改 `app/queue/consumer.py` 中的 `process_job` 函数，临时添加：

```python
# 在 process_job 函数开头添加（仅用于测试）
if job_data.pr_number == 999:
    raise Exception("Test failure for retry logic")
```

#### 4.2 触发失败的作业

```bash
# 发送 PR #999 的 webhook
# ... (使用之前的 curl 命令)
```

#### 4.3 观察重试行为

Worker 日志应该显示：
```
[warning] Error processing job <job_id>: Test failure...
[info] Re-enqueued job <job_id> (attempt 1)
[info] Re-enqueued job <job_id> (attempt 2)
[error] Job <job_id> failed after 3 attempts, moved to dead letter
```

#### 4.4 检查死信队列

```bash
# 检查死信队列
docker exec code_review_redis redis-cli XLEN review_jobs:dead_letter

# 查看死信消息
docker exec code_review_redis redis-cli XRANGE review_jobs:dead_letter - + COUNT 5
```

**预期结果：**
- 失败作业在重试 3 次后移动到死信队列
- 数据库状态为 `dead_letter`

---

### 场景 5: 测试优雅关闭（Task 3.5）

#### 5.1 启动 Worker 并处理作业

```bash
# 启动 worker
./scripts/start-worker.sh

# 发送一些作业
# ... (使用之前的测试脚本)
```

#### 5.2 在作业处理中中断

当 Worker 正在处理作业时，按 `Ctrl+C`

**预期结果：**
- Worker 显示 "Received signal, initiating graceful shutdown..."
- 等待当前作业完成（最多 10 秒）
- Worker 干净退出

#### 5.3 验证作业状态

```bash
# 检查是否有作业卡在 processing 状态
docker exec code_review_postgres psql -U user -d code_review_db -c \
  "SELECT * FROM pull_requests WHERE status = 'processing';"
```

**预期结果：**
- 没有作业卡在 processing 状态

---

### 场景 6: 测试指标端点（Task 3.8）

#### 6.1 查看队列指标

```bash
curl http://localhost:8000/api/metrics | jq
```

**预期结果：**
```json
{
  "queue": {
    "stream_length": 0,
    "pending_messages": 0,
    "consumer_groups": 1
  },
  "database": {
    "total_prs": 5,
    "queued": 0,
    "processing": 0,
    "completed": 5,
    "failed": 0,
    "dead_letter": 0
  }
}
```

#### 6.2 检查队列健康状态

```bash
curl http://localhost:8000/api/health/queue
```

**预期结果：**
```json
{
  "status": "healthy",
  "redis": "connected",
  "stream": "exists",
  "stream_length": 0
}
```

---

## 自动化测试脚本

### 完整测试脚本

```bash
#!/bin/bash
# test_queue_system.sh

set -e

echo "🧪 Testing Job Queue System"
echo "============================"

# 1. 检查服务运行
echo ""
echo "1. Checking services..."
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8000/api/health/queue | jq

# 2. 发送测试 webhook
echo ""
echo "2. Sending test webhook..."
SECRET=$(grep GITHUB_WEBHOOK_SECRET .env | cut -d '=' -f2)
PAYLOAD='{"action":"opened","pull_request":{"number":1000},"repository":{"full_name":"test/repo"}}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | sed 's/^.* //')

RESPONSE=$(curl -s -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
  -H "X-GitHub-Event: pull_request" \
  -d "$PAYLOAD")

echo "$RESPONSE" | jq
JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')

# 3. 等待处理
echo ""
echo "3. Waiting for job to be processed..."
sleep 5

# 4. 检查数据库
echo ""
echo "4. Checking database..."
docker exec code_review_postgres psql -U user -d code_review_db -c \
  "SELECT pr_number, status, job_id FROM pull_requests WHERE pr_number = 1000;"

# 5. 检查指标
echo ""
echo "5. Checking metrics..."
curl -s http://localhost:8000/api/metrics | jq

echo ""
echo "✅ Test completed!"
```

---

## 常见问题排查

### 问题 1: Webhook 返回慢

**检查：**
- Redis 连接是否正常
- Worker 是否在运行（不应该影响 webhook 速度）
- 查看应用日志

**解决方案：**
```bash
# 检查 Redis
docker exec code_review_redis redis-cli PING

# 检查 Worker 是否阻塞
# 如果 Worker 没运行，webhook 仍然应该快速返回
```

### 问题 2: 作业没有被处理

**检查：**
- Worker 是否运行
- Consumer Group 是否创建
- 查看 Worker 日志

**解决方案：**
```bash
# 检查 Consumer Group
docker exec code_review_redis redis-cli XINFO GROUPS review_jobs

# 手动创建 Consumer Group（如果需要）
docker exec code_review_redis redis-cli XGROUP CREATE review_jobs review_workers 0 MKSTREAM
```

### 问题 3: 作业卡在 processing 状态

**检查：**
- Worker 是否崩溃
- 是否有未确认的消息

**解决方案：**
```bash
# 检查待处理消息
docker exec code_review_redis redis-cli XPENDING review_jobs review_workers

# 重启 Worker（会重新处理未确认的消息）
```

### 问题 4: 数据库连接错误

**检查：**
- Docker 服务是否运行
- 数据库连接字符串是否正确

**解决方案：**
```bash
# 检查 Docker 服务
docker-compose ps

# 测试数据库连接
docker exec code_review_postgres psql -U user -d code_review_db -c "SELECT 1;"
```

---

## 性能测试

### 测试并发 Webhooks

```bash
# 使用 Apache Bench
ab -n 100 -c 10 -p payload.json -T application/json \
  -H "X-Hub-Signature-256: sha256=..." \
  -H "X-GitHub-Event: pull_request" \
  http://localhost:8000/webhooks/github
```

### 测试队列吞吐量

```bash
# 发送 100 个作业，观察处理速度
for i in {1..100}; do
  # ... send webhook
done

# 监控指标
watch -n 1 'curl -s http://localhost:8000/api/metrics | jq'
```

---

## 下一步

完成测试后，可以继续：
- Week 4: LLM 集成（实现实际的 PR 审查逻辑）
- 添加单元测试
- 添加集成测试
- 性能优化

