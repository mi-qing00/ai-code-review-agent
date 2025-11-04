# GitHub Webhook 设置指南

## 概述

本应用提供了 `/webhooks/github` 端点来接收 GitHub webhook 事件。目前支持处理 `pull_request` 事件（opened, synchronize, reopened）。

## 端点信息

- **URL:** `POST /webhooks/github`
- **Content-Type:** `application/json`
- **认证:** HMAC SHA-256 签名验证

## GitHub Webhook 配置

### 1. 在 GitHub 仓库中设置 Webhook

1. 进入你的 GitHub 仓库
2. 点击 **Settings** → **Webhooks** → **Add webhook**
3. 配置以下信息：
   - **Payload URL:** `https://your-domain.com/webhooks/github`
   - **Content type:** `application/json`
   - **Secret:** 设置一个强密码（保存到 `.env` 文件的 `GITHUB_WEBHOOK_SECRET`）
   - **Events:** 选择 "Let me select individual events"
     - 勾选 ✅ **Pull requests**
   - 点击 **Add webhook**

### 2. 配置环境变量

在 `.env` 文件中设置：

```bash
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
GITHUB_TOKEN=your_github_personal_access_token
```

### 3. 本地测试（使用 ngrok）

对于本地开发，可以使用 ngrok 来暴露本地服务：

```bash
# 安装 ngrok
brew install ngrok  # macOS
# 或从 https://ngrok.com/download 下载

# 启动应用
./scripts/start-dev.sh

# 在另一个终端启动 ngrok
ngrok http 8000

# 使用 ngrok 提供的 HTTPS URL 配置 GitHub webhook
# 例如: https://abc123.ngrok.io/webhooks/github
```

## 支持的事件

### Pull Request 事件

目前处理以下 `pull_request` 动作：

- ✅ `opened` - PR 被创建
- ✅ `synchronize` - PR 分支有新提交
- ✅ `reopened` - PR 被重新打开

其他动作会被记录但不会触发处理。

## 请求格式

GitHub 会发送以下格式的请求：

```json
{
  "action": "opened",
  "pull_request": {
    "number": 123,
    "title": "Fix bug in authentication",
    "state": "open",
    ...
  },
  "repository": {
    "full_name": "owner/repo",
    "name": "repo",
    ...
  }
}
```

## 响应格式

### 成功响应 (200 OK)

```json
{
  "message": "Webhook processed successfully",
  "pr_id": 1,
  "pr_number": 123,
  "repo_full_name": "owner/repo",
  "action": "opened"
}
```

### 错误响应

#### 401 Unauthorized (签名验证失败)
```json
{
  "detail": "Invalid signature"
}
```

#### 400 Bad Request (无效的 JSON)
```json
{
  "detail": "Invalid JSON payload"
}
```

## 签名验证

所有请求都会使用 HMAC SHA-256 进行签名验证。GitHub 会在 `X-Hub-Signature-256` 头中发送签名。

签名格式：`sha256=<hex_digest>`

### 开发模式

在开发环境中，如果 `GITHUB_WEBHOOK_SECRET` 设置为 `your_webhook_secret_here`，签名验证会被跳过（仅用于开发）。

⚠️ **警告：** 生产环境必须使用有效的 webhook secret！

## 数据库存储

当 PR 事件被处理时：

1. 如果 PR 不存在，会创建新记录
2. 如果 PR 已存在，会更新状态为 `pending` 并更新 `updated_at` 时间戳

存储的表结构：
- `pull_requests` 表
  - `id`: 主键
  - `pr_number`: PR 编号
  - `repo_full_name`: 仓库全名（owner/repo）
  - `status`: 状态（pending, processing, completed, failed）
  - `created_at`: 创建时间
  - `updated_at`: 更新时间

## 测试

### 使用 curl 测试（本地开发模式）

```bash
# 生成测试签名（使用你的 secret）
SECRET="your_webhook_secret_here"
PAYLOAD='{"action":"opened","pull_request":{"number":123},"repository":{"full_name":"test/repo"}}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | sed 's/^.* //')
SIGNATURE="sha256=$SIGNATURE"

# 发送请求
curl -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: $SIGNATURE" \
  -H "X-GitHub-Event: pull_request" \
  -d "$PAYLOAD"
```

### 查看日志

应用会记录所有 webhook 处理过程：

```bash
# 查看应用日志输出
./scripts/start-dev.sh
```

日志会显示：
- 签名验证状态
- 处理的事件类型和动作
- 数据库操作结果
- 任何错误信息

## 故障排除

### 1. 签名验证失败

**问题：** 收到 401 Unauthorized

**解决方案：**
- 检查 `.env` 文件中的 `GITHUB_WEBHOOK_SECRET` 是否与 GitHub webhook 设置中的 secret 一致
- 确保请求头 `X-Hub-Signature-256` 存在且格式正确

### 2. 数据库连接失败

**问题：** 处理失败，日志显示数据库错误

**解决方案：**
- 确保 Docker Compose 服务正在运行：`docker-compose ps`
- 检查数据库连接字符串是否正确
- 查看应用日志获取详细错误信息

### 3. 事件被忽略

**问题：** 收到 200 响应但显示 "Event type 'xxx' ignored"

**说明：** 这是正常的。应用目前只处理 `pull_request` 事件，其他事件会被安全地忽略。

## 下一步

- [ ] 实现 Redis Streams 队列（Week 3）
- [ ] 添加 worker 处理队列中的任务
- [ ] 集成 LLM API 进行代码审查（Week 4）

