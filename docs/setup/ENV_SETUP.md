# 环境配置说明

创建 `.env` 文件并填入以下配置：

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/code_review_db

# Redis
REDIS_URL=redis://localhost:6379/0

# GitHub
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
GITHUB_TOKEN=your_github_token_here  # Fallback, not recommended

# GitHub App (recommended for posting comments)
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY_PATH=/path/to/private-key.pem
GITHUB_APP_INSTALLATION_ID=12345678

# LLM Provider Selection
LLM_PROVIDER=zhipu  # Options: anthropic, openai, zhipu

# Anthropic (Claude)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo

# Zhipu (GLM-4)
ZHIPU_API_KEY=a15656b019ee4c6395e4bf62796f20f5.gZb6cbbDqKjt4YDt
ZHIPU_MODEL=glm-4.6

# App Settings
LOG_LEVEL=INFO
ENVIRONMENT=development
```

## 配置说明

- **DATABASE_URL**: PostgreSQL 连接字符串
- **REDIS_URL**: Redis 连接字符串
- **GITHUB_WEBHOOK_SECRET**: GitHub webhook 的密钥（用于验证 webhook 请求）
- **GITHUB_TOKEN**: GitHub 个人访问令牌（需要 `repo` 权限）
- **LLM_PROVIDER**: LLM 提供商选择（anthropic, openai, zhipu）
- **ANTHROPIC_API_KEY**: Anthropic Claude API 密钥（当使用 anthropic 时）
- **ANTHROPIC_MODEL**: Claude 模型名称
- **OPENAI_API_KEY**: OpenAI API 密钥（当使用 openai 时）
- **OPENAI_MODEL**: OpenAI 模型名称
- **ZHIPU_API_KEY**: Zhipu AI API 密钥（当使用 zhipu 时）
- **ZHIPU_MODEL**: Zhipu 模型名称
- **LOG_LEVEL**: 日志级别（DEBUG, INFO, WARNING, ERROR）
- **ENVIRONMENT**: 运行环境（development, production）

