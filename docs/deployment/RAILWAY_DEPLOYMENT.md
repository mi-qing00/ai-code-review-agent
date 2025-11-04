# Railway Deployment Guide

## Overview

This guide walks you through deploying the AI Code Review Agent to Railway.

## Prerequisites

- Railway account (sign up at https://railway.app)
- GitHub repository with the code
- GitHub App credentials (App ID, Installation ID, Private Key)
- LLM provider API key (Zhipu, OpenAI, or Anthropic)

## Step 1: Prepare GitHub App Private Key

Railway doesn't handle multi-line environment variables well, so we use base64 encoding:

```bash
# On your local machine, encode the private key
base64 -i ai-code-review-agent-dev.2025-11-03.private-key.pem | pbcopy

# Or on Linux:
base64 -i ai-code-review-agent-dev.2025-11-03.private-key.pem | xclip -selection clipboard
```

This copies the base64-encoded key to your clipboard. You'll paste it into Railway's environment variables.

## Step 2: Deploy to Railway

### 2.1 Create New Project

1. Go to https://railway.app/new
2. Sign in with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose your repository: `ai-code-review-agent`

### 2.2 Add PostgreSQL Database

1. Click "New" → "Database" → "PostgreSQL"
2. Railway automatically creates `DATABASE_URL` environment variable
3. Note: The database will be provisioned automatically

### 2.3 Add Redis Database

1. Click "New" → "Database" → "Redis"
2. Railway automatically creates `REDIS_URL` environment variable

### 2.4 Configure Web Service

1. Click on your web service
2. Go to "Variables" → "Raw Editor"
3. Add the following environment variables:

```bash
# LLM Provider
LLM_PROVIDER=zhipu
ZHIPU_API_KEY=your_zhipu_key_here
ZHIPU_MODEL=glm-4.6

# GitHub App
GITHUB_APP_ID=2230451
GITHUB_APP_INSTALLATION_ID=92935491
GITHUB_APP_PRIVATE_KEY_BASE64=<paste the base64 encoded key from Step 1>
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here

# App Settings
LOG_LEVEL=INFO
ENVIRONMENT=production
```

**Important:** 
- Use `GITHUB_APP_PRIVATE_KEY_BASE64` (not `GITHUB_APP_PRIVATE_KEY_PATH`)
- Paste the entire base64 string (no quotes, no line breaks)

### 2.5 Get Public URL

1. Click on your web service
2. Go to "Settings" → "Generate Domain"
3. You'll get a URL like: `https://ai-code-review-agent-production.up.railway.app`
4. Copy this URL - you'll need it for Step 4

## Step 3: Deploy Worker Process

The worker runs as a separate service on Railway.

### 3.1 Create Worker Service

1. In Railway dashboard, click "New" → "Service"
2. Select "GitHub Repo" → choose `ai-code-review-agent`
3. Railway will detect it's a Python project

### 3.2 Configure Worker Service

1. **Variables:** Copy all environment variables from the web service. The worker needs access to the same configuration:

   **Required Environment Variables:**
   ```bash
   # Database (automatically provided by Railway PostgreSQL service)
   DATABASE_URL=postgresql://...

   # Redis (automatically provided by Railway Redis service)
   REDIS_URL=redis://...

   # LLM Provider
   LLM_PROVIDER=zhipu
   ZHIPU_API_KEY=your_zhipu_key_here
   ZHIPU_MODEL=glm-4.6

   # GitHub App (for posting comments)
   GITHUB_APP_ID=2230451
   GITHUB_APP_INSTALLATION_ID=92935491
   GITHUB_APP_PRIVATE_KEY_BASE64=<base64_encoded_key>

   # GitHub Webhook (for webhook verification - also needed by worker for some operations)
   GITHUB_WEBHOOK_SECRET=your_webhook_secret_here

   # App Settings
   LOG_LEVEL=INFO
   ENVIRONMENT=production
   ```

   **How to copy variables:**
   - Go to web service → "Variables" → "Raw Editor"
   - Copy all variables
   - Go to worker service → "Variables" → "Raw Editor"
   - Paste all variables
   - Or manually add each variable one by one

2. **Settings** → **Start Command:** `python -m app.queue.consumer`
3. **Settings** → **Restart Policy:** "Always"

### 3.3 Deploy Worker

Railway will automatically deploy when you push to GitHub.

## Step 4: Update GitHub App Webhook URL

1. Go to your GitHub App settings:
   ```
   https://github.com/settings/apps/ai-code-review-agent-dev
   ```

2. Navigate to "Webhook" section
3. Update **Webhook URL** to your Railway URL:
   ```
   https://ai-code-review-agent-production.up.railway.app/webhooks/github
   ```
4. Click "Save changes"

## Step 5: Test Deployment

### 5.1 Check Health Endpoint

```bash
curl https://ai-code-review-agent-production.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "postgres": "connected",
  "redis": "connected"
}
```

### 5.2 View Logs

1. In Railway dashboard, click on your service
2. Go to "Logs" tab
3. You should see:
   - "Application started"
   - Database connection successful
   - Redis connection successful

### 5.3 Test Webhook

1. Create a test PR in your repository
2. Check Railway logs for webhook processing
3. Verify worker processes the job

## Troubleshooting

### Issue: Health check fails

**Check:**
- Database and Redis services are running
- Environment variables are set correctly
- Check logs for connection errors

### Issue: Worker not processing jobs

**Check:**
- Worker service is running (check logs)
- Redis connection is working
- Environment variables are copied to worker service

### Issue: GitHub App authentication fails

**Check:**
- `GITHUB_APP_PRIVATE_KEY_BASE64` is set correctly (full base64 string, no line breaks)
- `GITHUB_APP_ID` and `GITHUB_APP_INSTALLATION_ID` are correct
- Private key is valid (not expired)

### Issue: Webhook returns 401

**Check:**
- `GITHUB_WEBHOOK_SECRET` matches the secret in GitHub App settings
- Webhook URL is correct

## Monitoring

### View Logs

- **Web Service:** Railway dashboard → Your service → Logs
- **Worker Service:** Railway dashboard → Worker service → Logs

### Metrics

- Visit: `https://your-app-url.up.railway.app/api/metrics`
- Admin dashboard: `https://your-app-url.up.railway.app/api/admin`

## Cost Estimation

Railway free tier includes:
- $5/month credit
- 500 hours of compute time
- 1GB storage
- 100GB bandwidth

For this project:
- Web service: ~$2-3/month
- Worker service: ~$2-3/month
- PostgreSQL: Free (included)
- Redis: Free (included)

**Total:** Should fit within free tier for light usage.

## Next Steps

After deployment:
1. Test with a real PR
2. Monitor logs for errors
3. Set up alerts (optional)
4. Scale services if needed

## Rollback

If something goes wrong:
1. Go to Railway dashboard → Your service → "Deployments"
2. Click on previous successful deployment
3. Click "Redeploy"

