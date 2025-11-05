# Railway Worker 服务配置问题

## 问题

Worker 服务在启动时被 Railway 发送 SIGTERM 停止，显示 "Stopping Container"。

## 原因

Railway 可能认为 worker 服务不健康，因为：
1. Worker 是后台服务，没有 HTTP 健康检查端点
2. Railway 默认会检查服务是否健康
3. 如果服务类型配置错误，Railway 可能期望 HTTP 端点

## 解决方案

### 方案 1: 确保 Worker 服务配置正确（推荐）

在 Railway Dashboard 中：

1. **进入 Worker 服务设置**
   - 选择 Worker 服务
   - 点击 "Settings"

2. **检查 Start Command**
   ```
   bash scripts/railway_start.sh
   ```

3. **检查环境变量**
   ```
   SERVICE_TYPE=worker
   ```
   **重要**: 确保 `PORT` 环境变量**不存在**（如果存在，删除它）

4. **检查 Restart Policy**
   - 设置为 **"Always"**（不是 "On Failure"）
   - 这确保 worker 会持续运行

5. **禁用健康检查（如果可用）**
   - 在 Railway Dashboard → Worker Service → Settings
   - 查找 "Health Check" 或 "Health Check Path" 设置
   - 如果存在，**禁用或清空**它
   - Worker 服务不需要 HTTP 健康检查

### 方案 2: 检查服务类型

确保 Worker 服务是独立的服务：

1. **检查服务列表**
   - Railway Dashboard → Your Project
   - 应该看到两个服务：
     - Web Service（有 PORT 环境变量）
     - Worker Service（没有 PORT，有 SERVICE_TYPE=worker）

2. **如果只有一个服务**
   - 需要创建第二个服务
   - New → Service → GitHub Repo
   - 选择同一个仓库
   - 配置不同的环境变量

### 方案 3: 验证配置

运行以下检查：

```bash
# 在 Railway Dashboard 中检查 Worker 服务的环境变量：
# ✅ SERVICE_TYPE=worker
# ❌ PORT 不应该存在（如果存在，删除它）

# 检查 Start Command:
# ✅ bash scripts/railway_start.sh
# 或
# ✅ python -m app.queue.consumer
```

## 验证 Worker 正常运行

检查日志应该看到：

```
✅ Worker initialized and ready
✅ Redis connection established
👷 Consumer worker-1 started in group review_workers
📋 Waiting for jobs from stream: review_jobs
🚀 Worker is running and ready to process jobs
```

**不应该看到**:
- ❌ "Stopping Container"
- ❌ "Received signal 15"
- ❌ "Worker stopped"（除非手动停止）

## 常见错误配置

### 错误 1: Worker 服务有 PORT 环境变量
**问题**: Railway 认为这是 web 服务，期望 HTTP 端点
**解决**: 删除 PORT 环境变量，只保留 SERVICE_TYPE=worker

### 错误 2: Worker 服务启用了健康检查
**问题**: Railway 尝试访问 HTTP 端点，但 worker 没有
**解决**: 禁用健康检查或配置正确的健康检查路径

### 错误 3: Restart Policy 设置为 "On Failure"
**问题**: Worker 停止后不会自动重启
**解决**: 设置为 "Always"

## 调试步骤

如果 worker 仍然被停止：

1. **检查 Railway 日志**
   - 查看完整的启动日志
   - 查找错误信息

2. **检查环境变量**
   - 确保 SERVICE_TYPE=worker
   - 确保没有 PORT 环境变量

3. **检查服务配置**
   - Start Command 是否正确
   - Restart Policy 是否为 "Always"

4. **手动测试**
   - 在本地运行: `python -m app.queue.consumer`
   - 确认代码可以正常运行

5. **联系 Railway 支持**
   - 如果问题持续，可能需要检查 Railway 的配置
   - 某些情况下，可能需要禁用健康检查

---

**注意**: Worker 服务是长期运行的后台进程，不应该有 HTTP 端点。Railway 应该允许这类服务运行，只要配置正确。

