# Worker 状态说明

## ✅ Worker 现在可以正常运行了！

### 当前状态

从测试输出可以看到：
- ✅ Worker 成功启动
- ✅ Redis 连接正常
- ✅ Consumer group 创建成功
- ✅ Worker 正在等待消息（阻塞在 `XREADGROUP`）

### 为什么之前看不到输出？

1. **Worker 实际上在运行** - 只是没有输出到终端
2. **队列中可能有旧消息** - 已经被 consumer group 读取过，所以 `">"` 看不到
3. **Worker 在阻塞等待** - 这是正常的，说明它正在等待新消息

### 如何验证 Worker 正在工作

#### 方法 1: 发送新的 Webhook

```bash
# Terminal 1: 启动 worker（保持运行）
./scripts/start-worker.sh

# Terminal 2: 发送测试 webhook
./scripts/test_queue.sh
```

你应该看到：
- Worker 终端显示处理消息的日志
- 数据库状态从 `queued` → `processing` → `completed`

#### 方法 2: 检查 Worker 进程

```bash
# 检查 worker 是否在运行
ps aux | grep "app.queue.consumer" | grep -v grep

# 应该看到类似：
# python -m app.queue.consumer
```

#### 方法 3: 查看队列指标

```bash
curl http://localhost:8000/api/metrics | python3 -m json.tool
```

### 队列状态检查

```bash
# 检查队列长度
docker exec code_review_redis redis-cli XLEN review_jobs

# 检查 consumer group
docker exec code_review_redis redis-cli XINFO GROUPS review_jobs

# 查看流中的消息
docker exec code_review_redis redis-cli XRANGE review_jobs - + COUNT 5
```

### 预期行为

1. **Worker 启动时**:
   - 连接到 Redis ✅
   - 创建 consumer group（如果不存在）✅
   - 开始监听消息 ✅

2. **有新消息时**:
   - 读取消息
   - 更新状态为 `processing`
   - 处理作业
   - 更新状态为 `completed`
   - 确认消息（ACK）

3. **没有消息时**:
   - 阻塞等待（最多 5 秒）
   - 继续循环

### 如果 Worker 仍然立即退出

检查：
1. 是否有错误输出（现在应该能看到）
2. 检查日志级别设置
3. 运行：`poetry run python app/queue/consumer.py` 直接测试

### 测试完整流程

```bash
# 1. 启动 worker（Terminal 1）
./scripts/start-worker.sh

# 2. 发送测试 webhook（Terminal 2）
./scripts/test_queue.sh

# 3. 观察 worker 日志（Terminal 1）
# 应该看到：
# - "Processing job ..."
# - "Job ... completed successfully"

# 4. 检查数据库（Terminal 3）
docker exec code_review_postgres psql -U user -d code_review_db -c \
  "SELECT pr_number, status, enqueued_at, processing_started_at, completed_at FROM pull_requests ORDER BY created_at DESC LIMIT 5;"
```

### 当前队列状态

- **队列中有消息**: 1 条（PR #9348）
- **Consumer Group**: `review_workers` 已存在
- **Last delivered ID**: `1762215383399-0`
- **Pending messages**: 0（可能已被确认）

### 下一步

1. **发送新的 webhook** 创建新作业
2. **观察 worker 处理** 新消息
3. **验证完整流程** 从 webhook → queue → worker → database

