# 环境配置说明

创建 `.env` 文件并填入以下配置：

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/code_review_db

# Redis
REDIS_URL=redis://localhost:6379/0

# GitHub
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
GITHUB_TOKEN=your_github_token_here

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# App Settings
LOG_LEVEL=INFO
ENVIRONMENT=development
```

## 配置说明

- **DATABASE_URL**: PostgreSQL 连接字符串
- **REDIS_URL**: Redis 连接字符串
- **GITHUB_WEBHOOK_SECRET**: GitHub webhook 的密钥（用于验证 webhook 请求）
- **GITHUB_TOKEN**: GitHub 个人访问令牌（需要 `repo` 权限）
- **OPENAI_API_KEY**: OpenAI API 密钥
- **LOG_LEVEL**: 日志级别（DEBUG, INFO, WARNING, ERROR）
- **ENVIRONMENT**: 运行环境（development, production）

