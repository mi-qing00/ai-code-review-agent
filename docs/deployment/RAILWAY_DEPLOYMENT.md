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
3. **Database migrations run automatically**: When the web service starts, it will automatically check if database tables exist and run migrations if needed. You don't need to manually run SQL migrations.
4. Note: The database will be provisioned automatically

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
3. You'll get a URL like: `https://web-production-4a236.up.railway.app`
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

2. **Settings** → **Start Command:** 
   
   **Solution: Use Startup Script with Environment Variable**
   
   Railway's `railway.toml` may lock the start command. Use the provided startup script:
   
   **For Worker Service:**
   - Go to worker service → "Settings" → "Start Command"
   - Set to: `bash scripts/railway_start.sh`
   - Go to "Variables" → Add environment variable:
     - Key: `SERVICE_TYPE`
     - Value: `worker`
   
   **⚠️ CRITICAL: Configure Health Check for Worker Service**
   
   The worker now includes a minimal HTTP health check server!
   
   **In Railway Dashboard → Worker Service → Settings:**
   
   1. **Health Check Path**: Set to `/health`
   
   2. **Environment Variables:**
      ```
      SERVICE_TYPE=worker
      PORT=<Railway will auto-set this, or you can set it manually>
      ```
   
   **How it works:**
   - Worker automatically detects `PORT` environment variable
   - If `PORT` exists, starts a minimal HTTP server on that port
   - Health check endpoint `/health` returns `200 OK` with text "OK"
   - Railway will call `http://localhost:$PORT/health` to verify worker is running
   - If `PORT` is not set, health server won't start (fine for local development)
   
   **Note**: 
   - ✅ Worker now has HTTP health check endpoint, Railway won't kill it
   - ✅ Health check server only listens on `/health` and `/`, very lightweight
   - ✅ Doesn't affect worker's main functionality (processing Redis queue jobs)
   
   **For Web Service (if needed):**
   - Go to web service → "Settings" → "Start Command"  
   - Set to: `bash scripts/railway_start.sh`
   - The script will automatically detect it's a web service from the `PORT` environment variable
   - Or explicitly set: `SERVICE_TYPE=web`
   
   **Alternative: Direct Command (if script doesn't work)**
   - If the start command field is locked, try using Railway's "Override" feature
   - Or use Pre-Deploy step to set it dynamically
   - Or manually set: `python -m app.queue.consumer` directly in the start command field

3. **Settings** → **Restart Policy:** 
   
   **Important:** Set to "Always" for worker service
   
   - Go to worker service → "Settings" → "Restart Policy"
   - Select: **"Always"** (not "On Failure")
   - This ensures the worker automatically restarts if it crashes or stops
   - Worker must run continuously to process jobs from the queue
   
   **Note:** If restart policy is locked, it may be because `railway.toml` was setting it globally.
   The updated `railway.toml` no longer sets restart policy, so you should be able to configure it per service.

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
   https://web-production-4a236.up.railway.app/webhooks/github
   ```
4. Click "Save changes"

## Step 5: Test Deployment

### 5.1 Check Health Endpoint

```bash
curl https://web-production-4a236.up.railway.app/health
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

### Issue: Database tables not found (`relation "pull_requests" does not exist`)

**Cause:** Database migrations haven't run yet.

**Solution:**
- Migrations run automatically on web service startup. Check the logs for messages like:
  - `Checking database migration status...`
  - `Database tables not found. Running migrations...`
  - `✅ Database migrations completed`
- If migrations don't run automatically, you can manually trigger them by restarting the web service.
- **Manual migration (if needed):** Connect to Railway PostgreSQL and run:
  ```bash
  railway connect postgres
  ```
  Then run the migration files from `migrations/` directory.

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

