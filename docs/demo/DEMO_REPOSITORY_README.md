# 🤖 AI Code Review Agent - Live Demo

This repository demonstrates an AI-powered code review system that automatically analyzes pull requests and provides feedback on security, performance, and code quality issues.

## 🎯 What This Demonstrates

- **Automatic PR Review**: AI agent reviews every PR within seconds
- **Security Detection**: SQL injection, weak crypto, hardcoded secrets
- **Performance Analysis**: O(n²) algorithms, inefficient operations
- **Error Handling**: Missing try-catch, potential runtime errors

## 🚀 How It Works

1. **Create a PR** with some code (even with bugs!)
2. **AI Agent automatically reviews** your code within 3-5 seconds
3. **Get detailed feedback** on security, performance, and quality issues
4. **Improve your code** based on AI suggestions

## 📊 Example Reviews

### 🔐 Security Issues PR

[View PR #1](./pulls) - Detected:
- SQL injection vulnerability
- MD5 password hashing (weak)
- Plain text API key storage
- Hardcoded secrets

### ⚡ Performance Issues PR

[View PR #2](./pulls) - Detected:
- O(n²) complexity in duplicate finding
- Inefficient list membership checks
- Linear search instead of hash table
- String concatenation in loops

### ⚠️ Error Handling PR

[View PR #3](./pulls) - Detected:
- Missing division by zero checks
- JSON parsing without error handling
- Array bounds not validated
- File operations without try-except

## 🎯 Try It Yourself

1. **Fork this repository**
2. **Install the bot**: [AI Code Review Agent](https://github.com/apps/ai-code-review-agent-dev)
   - Click "Configure" → Add this repository
3. **Create a PR** with some code (intentionally buggy or not!)
4. **Watch the bot review it automatically!**

## 🔧 Technology Stack

- **Backend**: Python 3.11, FastAPI, asyncio
- **Queue**: Redis Streams
- **Database**: PostgreSQL 15
- **LLM**: Multiple providers (Claude, GPT-4, Zhipu GLM-4)
- **Deployment**: Railway

## 📈 Performance Metrics

- **Average Review Time**: 3-5 seconds
- **Cost Per Review**: $0.002-0.09 (depending on provider)
- **Accuracy**: 77% issue detection vs commercial tools

## 🔗 Links

- **Source Code**: [GitHub Repository](https://github.com/YOUR_USERNAME/ai-code-review-agent)
- **Live Dashboard**: [Admin Dashboard](https://web-production-4a236.up.railway.app/api/admin/dashboard)
- **API Documentation**: [API Docs](https://web-production-4a236.up.railway.app/docs)
- **Health Check**: [Health Endpoint](https://web-production-4a236.up.railway.app/health)

## 📝 About This Demo

This repository contains **intentionally problematic code** for demonstration purposes. The AI Code Review Agent automatically detects and reports:

- 🔐 Security vulnerabilities
- ⚡ Performance bottlenecks  
- ⚠️ Missing error handling
- 🐛 Code quality issues
- 📚 Best practice violations

**Note**: These demo files should NOT be used in production!

## 🎓 Learning Resources

Want to build your own AI code review system? Check out:

- [Architecture Design](./docs/JOB_QUEUE_DESIGN.md)
- [Deployment Guide](./docs/deployment/RAILWAY_DEPLOYMENT.md)
- [Testing Guide](./docs/testing/TESTING_GUIDE.md)

## 🤝 Contributing

This is a demonstration repository. Feel free to:

- Create PRs to test the AI agent
- Report issues with the review system
- Suggest improvements

## 📄 License

MIT License - Feel free to use this for learning and demonstration purposes.

---

*Built as a portfolio project demonstrating backend engineering and AI integration.*  
*Powered by [AI Code Review Agent](https://github.com/YOUR_USERNAME/ai-code-review-agent)*

