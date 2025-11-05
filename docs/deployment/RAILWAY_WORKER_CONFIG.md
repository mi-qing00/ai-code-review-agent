# Railway Worker 服务配置问题

## 问题

### 问题 1: Worker 服务在启动时被停止

Worker 服务在启动时被 Railway 发送 SIGTERM 停止，显示 "Stopping Container"。

### 问题 2: Railway 日志不显示

部署后，Railway 日志中看不到 "Starting container" 或任何输出。

## 原因

### Worker 被停止的原因

Railway 可能认为 worker 服务不健康，因为：
1. Worker 是后台服务，没有 HTTP 健康检查端点
2. Railway 默认会检查服务是否健康
3. 如果服务类型配置错误，Railway 可能期望 HTTP 端点

### 日志不显示的原因

1. **Python 输出缓冲**: Python 默认会缓冲 stdout/stderr，在容器环境中日志可能不会立即显示
2. **没有强制刷新**: 输出没有被立即刷新到流
3. **环境变量未设置**: `PYTHONUNBUFFERED` 环境变量未设置

## 解决方案

### 方案 0: 修复日志输出缓冲（必须先解决）

**问题**: Railway 看不到日志输出

**解决方法**:

1. **代码已自动处理**:
   - ✅ `PYTHONUNBUFFERED=1` 已在启动脚本中设置
   - ✅ `flush()` 调用已在关键位置添加
   - ✅ 输出同时发送到 stdout 和 stderr

2. **如果仍然看不到日志**:
   - 检查 Railway Dashboard → Worker Service → Variables
   - 确保没有覆盖 `PYTHONUNBUFFERED` 环境变量
   - 可以手动添加: `PYTHONUNBUFFERED=1`

3. **验证日志输出**:
   - 部署后应该立即看到:
     ```
     ============================================================
     🚀 Worker process starting...
     ============================================================
     🔧 Worker startup - Step 1: Initializing...
     ```

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

5. **禁用健康检查（关键！）**
   
   **Railway 默认会为所有服务启用健康检查，即使字段为空！**
   
   在 Railway Dashboard → Worker Service → Settings：
   
   - **方法 1: 使用环境变量禁用（推荐）**
     - 在 "Variables" 中添加：
       ```
       RAILWAY_HEALTHCHECK_TIMEOUT_SEC=0
       ```
     这会将健康检查超时设置为 0，实际禁用健康检查
   
   - **方法 2: 在 Settings 中禁用**
     - 查找 "Health Check Path" 或 "Health Check" 设置
     - **不能只是清空**，需要明确禁用
     - 如果找不到禁用选项，使用方法 1
   
   - **方法 3: 确保没有 PORT 环境变量**
     - **关键**: 如果 Worker 服务有 `PORT` 环境变量，Railway 会将其视为 web 服务
     - Railway 会尝试访问 `http://localhost:$PORT/health` 进行健康检查
     - **必须删除 PORT 环境变量**（如果存在）
     - 只保留 `SERVICE_TYPE=worker`
   
   ⚠️ **重要**: Railway 的健康检查在服务启动后立即开始，如果 Worker 没有 HTTP 端点，健康检查会在几秒内失败，导致 Railway 发送 SIGTERM 终止服务。

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
**症状**: Worker 在 3-5 秒后被 SIGTERM 终止
**解决**: 
   - 添加环境变量: `RAILWAY_HEALTHCHECK_TIMEOUT_SEC=0` 禁用健康检查
   - 确保没有 `PORT` 环境变量（如果有，删除它）
   - 在 Settings 中禁用健康检查（如果选项可用）

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

