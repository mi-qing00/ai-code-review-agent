# 演示仓库设置指南

本指南将帮助您创建一个演示仓库来展示 AI Code Review Agent 的功能。

## 📋 概述

演示仓库包含多个带有故意问题的 PR，用于展示 AI 代码审查系统如何检测：
- 🔐 安全问题（SQL 注入、弱加密、硬编码密钥）
- ⚡ 性能问题（O(n²) 算法、低效操作）
- ⚠️ 错误处理（缺少 try-catch、潜在的运行时错误）

## 🚀 快速开始

### 前置要求

1. **GitHub CLI (gh)** - 用于创建仓库和 PR
   ```bash
   # macOS
   brew install gh
   
   # 或从 https://cli.github.com/ 下载
   ```

2. **GitHub CLI 认证**
   ```bash
   gh auth login
   ```

3. **GitHub App 已安装**
   - 确保您的 GitHub App (`ai-code-review-agent-dev`) 已创建并配置

### 步骤 1: 运行演示脚本

```bash
# 进入项目目录
cd /path/to/codingAgent

# 运行演示脚本
chmod +x scripts/demo-prs.sh
./scripts/demo-prs.sh
```

**重要**: 脚本会在项目**父目录**创建一个新的 `pr-review-demo` 目录，不会影响当前项目。

脚本将：
1. 在项目父目录创建新的本地目录 `pr-review-demo`
2. 创建新的 GitHub 仓库 `pr-review-demo`（如果不存在）
3. 在新仓库中创建三个演示 PR，每个包含不同类型的问题
4. 将代码推送到 GitHub

**示例目录结构**:
```
/path/to/
  ├── codingAgent/          # 您的项目目录
  └── pr-review-demo/       # 新创建的演示仓库（脚本创建）
```

### 步骤 2: 配置 GitHub App

1. 访问 GitHub App 设置：
   ```
   https://github.com/settings/apps/ai-code-review-agent-dev
   ```

2. 点击 **"Configure"** 或 **"Install App"**

3. 选择 **"Only select repositories"**

4. 添加 `pr-review-demo` 到允许的仓库列表

5. 点击 **"Install"**

### 步骤 3: 验证 Webhook 配置

确保 GitHub App 的 Webhook URL 指向您的部署地址：

1. 在 GitHub App 设置页面，点击 **"Webhook"**

2. 确认 Webhook URL 为：
   ```
   https://web-production-4a236.up.railway.app/webhooks/github
   ```

3. 如果不同，请更新为您的 Railway 部署 URL

### 步骤 4: 测试自动审查

**⚠️ 重要提示**: 如果您在运行脚本**之后**才安装 GitHub App，已存在的 PR **不会自动审查**。

#### 情况 1: 在安装 App 之前运行脚本

如果 PR 在安装 GitHub App 之前就已创建，您需要手动触发审查：

**方法 A: 重新打开 PR（推荐，最简单）**
1. 在 GitHub 上打开每个 PR
2. 点击 **"Close pull request"** 关闭 PR
3. 然后点击 **"Reopen pull request"** 重新打开
4. 这会触发 `reopened` 事件，AI 代理会自动审查

**方法 B: 推送新提交到 PR 分支**
```bash
cd ../pr-review-demo
git checkout demo/security-issues
echo "# Trigger review" >> README.md
git add README.md
git commit -m "Trigger AI review"
git push
```
这会触发 `synchronize` 事件，AI 代理会自动审查

#### 情况 2: 在安装 App 之后创建 PR

如果您先安装 GitHub App，再运行脚本，PR 创建时会自动触发审查：

1. 访问您的仓库：`https://github.com/YOUR_USERNAME/pr-review-demo`

2. 查看创建的 PR

3. 等待 AI 代理添加审查评论（通常 3-5 秒）

4. 查看检测到的问题

## 📝 创建的演示 PR

### PR #1: 安全问题 🔐

**文件**: `insecure_auth.py`

**问题**:
- SQL 注入漏洞（字符串插值）
- MD5 密码哈希（弱加密）
- 明文存储 API 密钥
- 硬编码密钥

**分支**: `demo/security-issues`

### PR #2: 性能问题 ⚡

**文件**: `slow_processor.py`

**问题**:
- O(n²) 重复查找算法
- 低效的列表成员检查
- 线性搜索而非哈希表
- 循环中的字符串连接

**分支**: `demo/performance-issues`

### PR #3: 错误处理 ⚠️

**文件**: `calculator.py`

**问题**:
- 除零检查缺失
- JSON 解析无错误处理
- 数组越界未验证
- 文件操作无错误处理
- 用户输入验证缺失

**分支**: `demo/error-handling`

## 🎯 创建演示仓库 README

在演示仓库中，您可以使用以下 README 模板：

参见: `docs/demo/DEMO_REPOSITORY_README.md`

将模板内容复制到您的演示仓库的 README.md 文件中。

## 🔧 故障排查

### 问题: 脚本无法创建仓库

**解决方案**:
- 检查 GitHub CLI 是否已认证：`gh auth status`
- 确认有创建仓库的权限
- 如果仓库已存在，脚本会继续使用现有仓库

### 问题: PR 已存在

**解决方案**:
- 脚本会尝试创建 PR，如果已存在会显示警告
- 可以手动删除旧 PR 后重新运行脚本
- 或使用 `gh pr list` 查看现有 PR

### 问题: AI 代理未审查 PR

**检查清单**:
1. ✅ GitHub App 已安装到仓库
2. ✅ Webhook URL 配置正确
3. ✅ Worker 服务正在运行（检查 Railway 日志）
4. ✅ 环境变量配置正确
5. ✅ Redis 和数据库连接正常
6. ⚠️ **PR 是在安装 App 之后创建的吗？** 如果不是，请重新打开 PR 触发审查

**常见原因和解决方案**:

**原因 1: PR 在安装 App 之前就存在**
- **解决方案**: 重新打开 PR（关闭然后重新打开）或推送新提交

**原因 2: Webhook 未触发**
- **检查**: 在 GitHub 仓库设置中查看 Webhook 交付记录
- **调试**: 查看是否有失败的交付，检查错误信息

**原因 3: Worker 未运行**
- **检查**: Railway dashboard → Worker 服务 → Logs
- **调试**: 确保 worker 服务状态为 "Running"

**调试步骤**:
```bash
# 检查 Railway 日志
# 在 Railway dashboard 中查看 web 和 worker 服务的日志

# 检查 API 健康状态
curl https://web-production-4a236.up.railway.app/health

# 检查队列指标
curl https://web-production-4a236.up.railway.app/api/metrics

# 检查 GitHub Webhook 交付
# 在 GitHub 仓库: Settings → Webhooks → 点击您的 webhook → Recent Deliveries
```

## 📊 预期结果

每个 PR 应该收到包含以下内容的审查评论：

1. **问题摘要** - 检测到的问题列表
2. **严重性评级** - 每个问题的严重程度
3. **代码位置** - 问题所在的文件和行号
4. **修复建议** - 如何修复问题的建议
5. **代码示例** - 改进后的代码示例（如果有）

## 🎨 自定义演示

您可以修改 `scripts/demo-prs.sh` 来：

- 添加更多演示 PR
- 创建不同类型的代码问题
- 测试特定的检测场景
- 添加自定义文件

## 🔗 相关链接

- [GitHub App 设置指南](../setup/GITHUB_APP_SETUP.md)
- [Railway 部署指南](../deployment/RAILWAY_DEPLOYMENT.md)
- [Webhook 设置指南](../setup/WEBHOOK_SETUP.md)

## 📝 注意事项

⚠️ **重要**: 演示仓库中的代码包含**故意的问题**，仅用于演示目的。

- 不要在生产环境中使用这些代码
- 不要将这些代码合并到主分支
- 这些代码仅用于展示 AI 代码审查功能

## ❓ 常见问题

### Q: 我需要每次运行端到端测试来让 AI 代理添加评论吗？

**A: 不需要！** 在生产环境中，AI 代理是**完全自动**的：

1. 创建 PR → GitHub 发送 webhook
2. Webhook → Redis Queue → Worker
3. Worker → AI 分析 → 自动发布评论

您**不需要**运行任何测试脚本。系统会自动处理所有 PR。

**端到端测试脚本** (`test_end_to_end.py`) 仅用于：
- 开发和调试
- 验证配置
- 故障排查

详见: [自动审查 vs 手动测试](./AUTO_VS_MANUAL_REVIEW.md)

---

*创建日期: $(date)*

