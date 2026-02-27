# SmartAP — Free-Tier Demo Deployment Guide

Deploy SmartAP for prototype/demo purposes using **$0/month** free-tier services.

| Component | Service | Cost | Why |
|-----------|---------|------|-----|
| Frontend | **Vercel** (Free) | $0 | Built by the Next.js team; zero-config deploy |
| Backend | **Render** (Free) | $0 | Supports Docker, auto-deploy from GitHub |
| Database | **SQLite** (bundled) | $0 | Already built into the backend — no external DB needed |
| Redis | *skipped* | $0 | Optional; not needed for demos |

> **Total cost: $0/month**

---

## Table of Contents

- [Option A: Vercel + Render (Recommended)](#option-a-vercel--render-recommended)
- [Option B: Vercel + Azure App Service Free Tier](#option-b-vercel--azure-app-service-free-tier)
- [Option C: Cloudflare Pages + Render](#option-c-cloudflare-pages--render)
- [Limitations & Notes](#limitations--notes)

---

## Option A: Vercel + Render (Recommended)

The simplest path — both platforms auto-deploy from GitHub with zero Docker setup.

### Step 1: Deploy Backend to Render

1. Go to [render.com](https://render.com) and sign in with GitHub
2. Click **New > Web Service**
3. Connect your `FoxitJohnny/SmartAP` repository
4. Configure:

   | Setting | Value |
   |---------|-------|
   | **Name** | `smartap-api` |
   | **Root Directory** | `backend` |
   | **Runtime** | `Docker` |
   | **Instance Type** | `Free` |

5. Add **Environment Variables** (click "Advanced"):

   | Key | Value |
   |-----|-------|
   | `SECRET_KEY` | *(generate one: `openssl rand -hex 32`)* |
   | `APP_ENV` | `production` |
   | `DEBUG` | `false` |
   | `CORS_ORIGINS` | `https://smartap.vercel.app` *(update after Vercel deploy)* |
   | `AI_PROVIDER` | `github` |
   | `GITHUB_TOKEN` | *(your GitHub PAT)* |
   | `REDIS_ENABLED` | `false` |

6. Click **Deploy Web Service**

Your backend will be live at: `https://smartap-api.onrender.com`

> **Note:** Render free tier spins down after 15 minutes of inactivity. First request after idle takes ~30–60 seconds. This is fine for demos.

#### Database seeding

The Dockerfile now auto-seeds demo data on every container start, so no manual action needed.

If you ever need to force a re-seed (e.g., data got corrupted), call the admin API:

```bash
# Seed (skips if data exists)
curl -X POST https://smartap-api.onrender.com/api/v1/admin/seed \
  -H "X-Admin-Key: YOUR_SECRET_KEY"

# Force re-seed (wipes and recreates all data)
curl -X POST https://smartap-api.onrender.com/api/v1/admin/seed/force \
  -H "X-Admin-Key: YOUR_SECRET_KEY"
```

Replace `YOUR_SECRET_KEY` with the `SECRET_KEY` value you set in environment variables.

### Step 2: Deploy Frontend to Vercel

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub
2. Click **Add New > Project**
3. Import `FoxitJohnny/SmartAP`
4. Configure:

   | Setting | Value |
   |---------|-------|
   | **Framework Preset** | `Next.js` *(auto-detected)* |
   | **Root Directory** | `frontend` *(click "Edit" to change)* |
   | **Build Command** | `npm run build` |
   | **Output Directory** | `.next` *(default)* |

5. Add **Environment Variables**:

   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_URL` | `https://smartap-api.onrender.com/api/v1` |

6. Click **Deploy**

Your frontend will be live at: `https://smartap.vercel.app` (or similar)

### Step 3: Update CORS

After both are deployed, go back to Render and update the `CORS_ORIGINS` env var to match your actual Vercel URL:

```
CORS_ORIGINS=https://smartap-YOUR_SUFFIX.vercel.app
```

Render will auto-redeploy.

**Done!** Your demo is live.

---

## Option B: Vercel + Azure App Service Free Tier

Use this if you prefer keeping the backend on Azure.

### Step 1: Deploy Backend to Azure App Service (F1 Free)

Azure App Service Free tier (F1) supports Python natively — no Docker needed.

```bash
# Login
az login

# Create resource group
az group create --name smartap-demo-rg --location eastus

# Create free App Service plan
az appservice plan create \
  --name smartap-demo-plan \
  --resource-group smartap-demo-rg \
  --sku F1 \
  --is-linux

# Create the web app (Python 3.11)
az webapp create \
  --resource-group smartap-demo-rg \
  --plan smartap-demo-plan \
  --name smartap-api-demo \
  --runtime "PYTHON:3.11"

# Configure it to run from the backend directory
az webapp config appsettings set \
  --resource-group smartap-demo-rg \
  --name smartap-api-demo \
  --settings \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true \
    SECRET_KEY="$(openssl rand -hex 32)" \
    APP_ENV=production \
    DEBUG=false \
    CORS_ORIGINS="https://smartap.vercel.app" \
    AI_PROVIDER=github \
    GITHUB_TOKEN="your-github-pat" \
    REDIS_ENABLED=false

# Deploy the backend code  
cd backend
az webapp up \
  --resource-group smartap-demo-rg \
  --name smartap-api-demo \
  --runtime "PYTHON:3.11"
```

> **Azure F1 limitations:** 60 CPU-minutes/day, 1 GB RAM, no custom domains, no always-on. Fine for occasional demos.

The backend URL will be: `https://smartap-api-demo.azurewebsites.net`

You need a startup command for FastAPI:

```bash
az webapp config set \
  --resource-group smartap-demo-rg \
  --name smartap-api-demo \
  --startup-file "uvicorn src.main:app --host 0.0.0.0 --port 8000"
```

### Step 2: Deploy Frontend to Vercel

Same as [Option A, Step 2](#step-2-deploy-frontend-to-vercel), but set:

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | `https://smartap-api-demo.azurewebsites.net/api/v1` |

---

## Option C: Cloudflare Pages + Render

Use this if you already set up the Cloudflare adapter from the previous guide.

### Step 1: Deploy Backend to Render

Same as [Option A, Step 1](#step-1-deploy-backend-to-render).

### Step 2: Deploy Frontend to Cloudflare Pages

> Requires `@opennextjs/cloudflare` and `wrangler.jsonc` already configured (see previous Cloudflare setup).

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com) → **Workers & Pages** → **Create**
2. Connect your GitHub repo
3. Configure:

   | Setting | Value |
   |---------|-------|
   | **Project name** | `smartap` |
   | **Root directory** | `frontend` |
   | **Build command** | `npm run build:worker` |
   | **Deploy command** | `npx wrangler deploy` |

4. Add environment variable:

   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_URL` | `https://smartap-api.onrender.com/api/v1` |

5. Click **Deploy**

---

## Limitations & Notes

### Render free-tier cold starts
Render spins down free services after 15 minutes of inactivity. The first request wakes it up in ~30–60 seconds. **Tip for demos:** open the backend URL in a browser tab a minute before your demo starts to "warm it up."

### SQLite on ephemeral disk
Render's free tier has ephemeral storage — the SQLite DB resets on every deploy/restart. The Dockerfile now handles this automatically by running `python -m src.db.seed` before starting the server. Demo data is re-created in ~5 seconds on each cold start.

If you need to manually re-seed a running instance, use the admin API:

```bash
curl -X POST https://smartap-api.onrender.com/api/v1/admin/seed/force \
  -H "X-Admin-Key: YOUR_SECRET_KEY"
```

### Vercel free-tier limits
- Unlimited static/SSR pages
- 100 GB bandwidth/month
- Serverless function execution: 100 GB-hours/month
- More than enough for demo purposes

### Azure F1 free-tier limits
- 60 CPU-minutes/day (resets daily)
- 1 GB RAM, 1 GB storage
- No custom domains, no SSL with custom domain
- No always-on (cold starts)

### Environment variable quick-reference

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL (frontend) | `https://smartap-api.onrender.com/api/v1` |
| `CORS_ORIGINS` | Allowed frontend origins (backend) | `https://smartap.vercel.app` |
| `SECRET_KEY` | JWT signing key (backend) | `openssl rand -hex 32` |
| `AI_PROVIDER` | AI model provider (backend) | `github` |
| `GITHUB_TOKEN` | GitHub PAT for AI models (backend) | `ghp_...` |
| `REDIS_ENABLED` | Disable Redis for demo (backend) | `false` |

---

## Comparison Summary

| | **Option A** (Vercel + Render) | **Option B** (Vercel + Azure F1) | **Option C** (Cloudflare + Render) |
|---|---|---|---|
| **Cost** | $0 | $0 | $0 |
| **Setup time** | ~10 min | ~15 min | ~15 min |
| **Backend cold start** | ~30–60s | ~20–30s | ~30–60s |
| **CI/CD** | Auto (GitHub push) | Manual (`az webapp up`) | Auto (GitHub push) |
| **Best for** | Quickest demo | Azure ecosystem | Already using Cloudflare |
