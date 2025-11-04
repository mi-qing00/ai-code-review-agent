# Worker 故障排除指南

## 问题：Worker 启动后立即退出

### 症状
- Worker 脚本运行后立即返回到命令提示符
- 没有错误消息
- 没有日志输出

### 可能的原因和解决方案

#### 1. 消息已被 Consumer Group 读取

**问题**: 如果消息已经被 consumer group 读取过，使用 `">"` 只会读取新消息，不会看到已读取的消息。

**检查**:
```bash
docker exec code_review_redis redis-cli XINFO GROUPS review_jobs
```

**解决方案**:
- Worker 现在会自动检查并处理 pending 消息
- 如果消息卡住，可以重置 consumer group:
```bash
# 删除并重新创建 consumer group
docker exec code_review_redis redis-cli XGROUP DESTROY review_jobs review_workers
```

#### 2. 日志没有显示

**问题**: 日志可能被缓冲或输出到 stderr。

**解决方案**:
- Worker 现在会同时输出到 stdout 和 stderr
- 检查启动脚本是否正确捕获输出

#### 3. 导入错误

**问题**: 模块导入失败但没有显示错误。

**检查**:
```bash
poetry run python -c "from app.queue.consumer import run_worker; print('OK')"
```

**解决方案**:
- 确保所有依赖已安装: `poetry install`
- 检查 Python 版本: `poetry run python --version`

#### 4. 配置问题

**问题**: 环境变量或配置缺失。

**检查**:
```bash
poetry run python -c "from app.core.config import settings; print(settings.redis_url)"
```

**解决方案**:
- 确保 `.env` 文件存在且配置正确
- 检查 Redis 连接字符串

## 测试 Worker

### 方法 1: 直接运行

```bash
poetry run python -m app.queue.consumer
```

应该看到：
```
🚀 Review worker starting...
👷 Consumer worker-1 started in group review_workers
📋 Waiting for jobs from stream: review_jobs
```

### 方法 2: 使用启动脚本

```bash
./scripts/start-worker.sh
```

### 方法 3: 检查 Worker 是否在处理消息

```bash
# Terminal 1: 启动 worker
./scripts/start-worker.sh

# Terminal 2: 发送测试 webhook
./scripts/test_queue.sh

# Terminal 3: 观察 worker 日志
# 应该看到处理消息的日志
```

## 常见问题

### Q: Worker 启动但没有处理消息

**A**: 检查：
1. 队列中是否有消息: `docker exec code_review_redis redis-cli XLEN review_jobs`
2. Consumer group 状态: `docker exec code_review_redis redis-cli XINFO GROUPS review_jobs`
3. 是否有 pending 消息: `docker exec code_review_redis redis-cli XPENDING review_jobs review_workers`

### Q: Worker 处理消息但状态没有更新

**A**: 检查数据库连接和权限：
```bash
docker exec code_review_postgres psql -U user -d code_review_db -c "SELECT * FROM pull_requests WHERE pr_number = 9348;"
```

### Q: 如何重置 Consumer Group

**A**: 
```bash
# 删除 consumer group
docker exec code_review_redis redis-cli XGROUP DESTROY review_jobs review_workers

# Worker 启动时会自动重新创建
```

### Q: 如何查看 Worker 日志

**A**: Worker 会输出到 stdout/stderr。如果使用启动脚本，日志会直接显示在终端。

## 调试技巧

1. **启用详细日志**: 在 `.env` 中设置 `LOG_LEVEL=DEBUG`
2. **检查 Redis 连接**: `docker exec code_review_redis redis-cli PING`
3. **查看流内容**: `docker exec code_review_redis redis-cli XRANGE review_jobs - +`
4. **检查 Consumer Group**: `docker exec code_review_redis redis-cli XINFO GROUPS review_jobs`

