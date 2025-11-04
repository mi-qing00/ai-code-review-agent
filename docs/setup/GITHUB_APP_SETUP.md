# GitHub App 设置指南

为了发布评论到 GitHub PR，需要使用 GitHub App 认证（而不是 Personal Access Token）。

## 为什么需要 GitHub App？

使用 GitHub App 认证的好处：
- ✅ 更细粒度的权限控制
- ✅ 自动 token 刷新
- ✅ 更好的安全性
- ✅ 可以发布 PR 评论（PAT 通常没有足够权限）

## 设置步骤

### Step 1: 获取 GitHub App 信息

1. 访问你的 GitHub App 设置页面：
   ```
   https://github.com/settings/apps/ai-code-review-agent-dev/advanced
   ```

2. 记录以下信息：
   - **App ID**: 在 "About" 部分找到
   - **Installation ID**: 在 "Installations" 部分找到
   - **Private Key**: 点击 "Generate a private key" 下载 `.pem` 文件

### Step 2: 保存 Private Key

将下载的 private key 保存到项目目录：

```bash
# 保存到项目根目录（或安全的位置）
mv ~/Downloads/your-app-name.private-key.pem ./github-app-key.pem

# 设置适当的权限（只允许所有者读取）
chmod 600 ./github-app-key.pem
```

**重要：** 不要将 private key 提交到 Git！添加到 `.gitignore`：

```bash
echo "*.pem" >> .gitignore
echo "github-app-key.pem" >> .gitignore
```

### Step 3: 配置环境变量

在 `.env` 文件中添加：

```bash
# GitHub App (required for posting comments)
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY_PATH=./github-app-key.pem
GITHUB_APP_INSTALLATION_ID=12345678
```

### Step 4: 验证 App 权限

确保你的 GitHub App 有以下权限：

1. **Repository permissions:**
   - ✅ Contents: Read
   - ✅ Pull requests: **Write** (必需！)
   - ✅ Metadata: Read

2. **Subscribe to events:**
   - ✅ Pull request

### Step 5: 测试配置

```bash
# 测试配置是否正确
poetry run python -c "
from app.core.config import settings
print(f'App ID: {settings.github_app_id}')
print(f'Key Path: {settings.github_app_private_key_path}')
print(f'Installation ID: {settings.github_app_installation_id}')
"
```

### Step 6: 重新运行测试

```bash
# 运行端到端测试
poetry run python scripts/test_end_to_end.py kaitlynmi/pr-review-agent-test 1
```

## 故障排查

### 问题 1: 403 Forbidden

**原因：** App 没有 "Pull requests: Write" 权限

**解决：**
1. 访问 App 设置页面
2. 在 "Permissions & events" 部分
3. 确保 "Pull requests" 权限设置为 "Write"

### 问题 2: Private Key 文件找不到

**错误：** `FileNotFoundError: GitHub App private key not found`

**解决：**
1. 检查 `GITHUB_APP_PRIVATE_KEY_PATH` 路径是否正确
2. 确保文件存在且有读取权限
3. 使用绝对路径（推荐）

### 问题 3: Invalid JWT

**错误：** JWT 生成失败

**解决：**
1. 检查 private key 文件格式是否正确（应该是 PEM 格式）
2. 确保 App ID 正确
3. 检查系统时间是否正确（JWT 有时间戳）

### 问题 4: Installation ID 错误

**错误：** Token 获取失败

**解决：**
1. 确认 Installation ID 正确
2. 确保 App 已安装到目标仓库
3. 检查 App 是否已授权访问仓库

## 回退方案

如果暂时无法使用 GitHub App，可以继续使用 PAT，但：
- ⚠️ PAT 可能没有足够的权限发布评论
- ⚠️ 需要手动刷新 token
- ⚠️ 安全性较低

系统会自动检测：如果配置了 App 认证就使用 App，否则回退到 PAT。

