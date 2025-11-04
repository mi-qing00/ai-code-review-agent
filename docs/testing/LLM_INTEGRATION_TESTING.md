# LLM 集成测试指南

本指南帮助您测试完整的代码审查流程，从配置验证到端到端测试。

## 前置条件

✅ Worker 已启动  
✅ GitHub App 已配置并连接到测试仓库  
✅ Webhook URL 已设置（通过 ngrok 或其他方式）  
✅ 测试仓库：[kaitlynmi/pr-review-agent-test](https://github.com/kaitlynmi/pr-review-agent-test)

## 测试步骤

### Step 1: 验证配置

首先验证 Zhipu 配置是否正确：

```bash
# 方法 1: 使用测试脚本
./scripts/test_llm_integration.sh

# 方法 2: 手动验证
python3 -c "
from app.core.config import settings
config = settings.get_llm_config()
print(f'Provider: {config[\"provider\"]}')
print(f'Model: {config[\"model\"]}')
print(f'API Key: {config[\"api_key\"][:20]}...')
"
```

**预期输出：**
```
Provider: zhipu
Model: glm-4.6
API Key: a15656b019ee4c6395e4...
```

### Step 2: 测试 Zhipu Provider（独立测试）

测试 LLM provider 是否能正常工作：

```bash
./scripts/test_llm_integration.sh
```

或者手动测试：

```python
import asyncio
from app.llm.factory import get_llm_provider

async def test():
    provider = get_llm_provider()
    
    test_diff = """--- a/test.py
+++ b/test.py
@@ -1,3 +1,3 @@
 def divide(a, b):
-    return a / b
+    return a / b  # Missing error handling
"""
    
    result = await provider.analyze_diff(test_diff)
    print(f"Comments: {len(result.comments)}")
    print(f"Tokens: {result.tokens_used}")
    print(f"Cost: ${result.cost:.4f}")

asyncio.run(test())
```

**预期输出：**
- ✅ Provider 初始化成功
- ✅ 分析完成，返回评论
- ✅ Token 使用和成本计算正确

### Step 3: 测试响应解析器

验证 LLM 响应是否能正确解析为结构化评论：

```bash
python3 -c "
from app.llm.parser import parse_review_response

response = '''test.py:5 - Missing error handling for division by zero
test.py:10 - Variable name 'x' is not descriptive
'''

comments = parse_review_response(response)
for comment in comments:
    print(f'{comment.file_path}:{comment.line_number} - {comment.comment_text}')
"
```

**预期输出：**
```
test.py:5 - Missing error handling for division by zero
test.py:10 - Variable name 'x' is not descriptive
```

### Step 4: 测试 GitHub Diff 获取

测试能否从 GitHub 获取 PR diff：

```bash
python3 scripts/test_end_to_end.py kaitlynmi/pr-review-agent-test 1
```

**注意：** 需要先创建一个测试 PR，或者使用现有的 PR 号码。

**预期输出：**
- ✅ GitHub 客户端初始化成功
- ✅ Diff 获取成功
- ✅ 显示文件变更、增减行数等信息

### Step 5: 端到端测试（完整流程）

#### 方法 1: 使用测试脚本

```bash
python3 scripts/test_end_to_end.py kaitlynmi/pr-review-agent-test <PR_NUMBER>
```

这会：
1. 验证配置
2. 从 GitHub 获取 PR diff
3. 使用 LLM 分析 diff
4. 显示生成的评论（可选：发布到 GitHub）

#### 方法 2: 通过 Webhook 触发（真实场景）

1. **创建测试 PR**
   - 在测试仓库创建一个新分支
   - 添加一些有问题的代码（例如：缺少错误处理、SQL 注入风险等）
   - 创建 PR

2. **监控 Worker 日志**
   ```bash
   # 在运行 worker 的终端查看日志
   # 应该看到：
   # - Webhook 接收
   # - Job 入队
   # - 开始处理
   # - 获取 diff
   # - LLM 分析
   # - 发布评论
   ```

3. **检查 PR**
   - 打开 GitHub PR 页面
   - 应该看到 AI 生成的审查评论

### Step 6: 测试不同场景

#### 场景 1: 小 PR（单文件，少量变更）

创建一个简单的 PR，修改一个文件：
```python
# 修改前
def divide(a, b):
    return a / b

# 修改后
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
```

**预期：** LLM 应该识别出改进点或给出正面反馈

#### 场景 2: 有问题的代码

创建包含明显问题的 PR：
```python
# 安全问题
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"  # SQL injection
    return execute(query)

# 资源泄漏
def read_file(path):
    f = open(path)
    return f.read()  # Missing close()
```

**预期：** LLM 应该识别出安全问题、资源泄漏等问题

#### 场景 3: 大 PR（多文件）

创建一个修改多个文件的 PR，测试系统是否：
- 正确处理大 diff
- 限制评论数量（最多 100 条）
- 按重要性排序评论

#### 场景 4: 空 PR 或只有格式变更

创建只修改空白或格式的 PR。

**预期：** LLM 可能不生成评论，或生成较少的评论

## 故障排查

### 问题 1: 配置错误

**症状：** `ValueError: ZHIPU_API_KEY is required`

**解决方案：**
```bash
# 检查 .env 文件
cat .env | grep ZHIPU

# 确保设置了正确的值
export ZHIPU_API_KEY=a15656b019ee4c6395e4bf62796f20f5.gZb6cbbDqKjt4YDt
export LLM_PROVIDER=zhipu
```

### 问题 2: LLM API 调用失败

**症状：** `APIError: Zhipu API error`

**解决方案：**
1. 检查 API key 是否有效
2. 检查网络连接
3. 查看完整错误日志

### 问题 3: GitHub API 权限问题

**症状：** `Access denied to kaitlynmi/pr-review-agent-test`

**解决方案：**
1. 检查 `GITHUB_TOKEN` 是否设置
2. 确认 token 有 `repo` 权限
3. 确认 GitHub App 有访问仓库的权限

### 问题 4: Worker 没有处理 Job

**症状：** Job 一直处于 `queued` 状态

**解决方案：**
1. 检查 worker 是否正在运行
2. 检查 Redis 连接
3. 查看 worker 日志中的错误信息

### 问题 5: 评论没有发布到 GitHub

**症状：** LLM 分析成功，但没有评论出现在 PR 上

**解决方案：**
1. 检查 GitHub token 权限
2. 检查 position 计算是否正确
3. 查看 worker 日志中的错误信息

## 监控和日志

### 查看 Worker 日志

```bash
# 如果使用 start-worker.sh
tail -f logs/worker.log

# 或者直接查看终端输出
```

### 检查数据库状态

```sql
-- 查看最近的 PR 处理状态
SELECT pr_number, repo_full_name, status, 
       created_at, updated_at, error_message
FROM pull_requests
ORDER BY created_at DESC
LIMIT 10;
```

### 检查队列状态

```bash
# Redis CLI
docker exec code_review_redis redis-cli

# 查看队列长度
XLEN review_jobs

# 查看 pending 消息
XPENDING review_jobs review_workers
```

## 性能指标

测试时关注以下指标：

- **响应时间：** LLM 分析通常需要 1-5 秒
- **Token 使用：** 取决于 diff 大小
- **成本：** Zhipu 相对便宜，但也要监控使用量
- **成功率：** 应该 > 95%

## 下一步

测试成功后，可以：

1. **优化提示词** - 根据实际输出调整 prompt
2. **调整评论筛选** - 减少误报
3. **添加缓存** - 实现内容地址缓存（Week 5）
4. **并发处理** - 实现并发处理多个 PR（Week 6）

