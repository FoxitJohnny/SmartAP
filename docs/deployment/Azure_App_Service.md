# SmartAP — Azure App Service Deployment Guide

Deploy the SmartAP frontend (Next.js) and backend (FastAPI) to Azure App Service using Docker containers, with Azure Database for PostgreSQL and Azure Cache for Redis.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [1. Create Azure Resources](#1-create-azure-resources)
- [2. Deploy the Backend](#2-deploy-the-backend)
- [3. Deploy the Frontend](#3-deploy-the-frontend)
- [4. Configure Custom Domains & SSL](#4-configure-custom-domains--ssl)
- [5. CI/CD with GitHub Actions](#5-cicd-with-github-actions)
- [6. Monitoring & Logging](#6-monitoring--logging)
- [7. Troubleshooting](#7-troubleshooting)

---

## Architecture Overview

```
┌────────────────────────────────────────────────────┐
│                    Azure                           │
│                                                    │
│  ┌──────────────┐       ┌───────────────────────┐  │
│  │  App Service  │       │     App Service       │  │
│  │  (Frontend)   │──────▶│     (Backend)         │  │
│  │  Next.js      │       │     FastAPI/Uvicorn   │  │
│  │  :3000        │       │     :8000             │  │
│  └──────────────┘       └──────────┬────────────┘  │
│                                    │               │
│                         ┌──────────┴────────────┐  │
│                         │                       │  │
│                 ┌───────▼──────┐  ┌─────────────▼┐ │
│                 │ Azure DB for │  │ Azure Cache  │ │
│                 │ PostgreSQL   │  │ for Redis    │ │
│                 └──────────────┘  └──────────────┘ │
│                                                    │
│  ┌──────────────────────────────────────────────┐  │
│  │         Azure Container Registry (ACR)       │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```

---

## Prerequisites

- **Azure CLI** installed and authenticated (`az login`)
- **Docker** installed locally (for building/testing images)
- A GitHub repository with the SmartAP code

### Install Azure CLI

```bash
# Windows (winget)
winget install Microsoft.AzureCLI

# macOS
brew install azure-cli

# Verify
az version
az login
```

---

## 1. Create Azure Resources

### Set variables

```bash
# Customize these
RESOURCE_GROUP=smartap-rg
LOCATION=eastus
ACR_NAME=smartapacr        # Must be globally unique, lowercase, alphanumeric
BACKEND_APP=smartap-api
FRONTEND_APP=smartap-web
PG_SERVER=smartap-pg
PG_ADMIN_USER=smartapadmin
PG_ADMIN_PASSWORD=$(openssl rand -base64 24)  # Save this!
REDIS_NAME=smartap-redis
APP_PLAN=smartap-plan
```

### Create Resource Group

```bash
az group create --name $RESOURCE_GROUP --location $LOCATION
```

### Create Azure Container Registry

```bash
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true
```

### Create Azure Database for PostgreSQL Flexible Server

```bash
az postgres flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name $PG_SERVER \
  --location $LOCATION \
  --admin-user $PG_ADMIN_USER \
  --admin-password "$PG_ADMIN_PASSWORD" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 16 \
  --yes

# Create the application database
az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $PG_SERVER \
  --database-name smartap
```

### Create Azure Cache for Redis

```bash
az redis create \
  --resource-group $RESOURCE_GROUP \
  --name $REDIS_NAME \
  --location $LOCATION \
  --sku Basic \
  --vm-size C0 \
  --enable-non-ssl-port false
```

### Create App Service Plan (Linux)

```bash
az appservice plan create \
  --name $APP_PLAN \
  --resource-group $RESOURCE_GROUP \
  --is-linux \
  --sku B1
```

> **Tip:** Use `B1` for testing. Scale to `P1v3` or higher for production workloads.

---

## 2. Deploy the Backend

### 2.1 Build & push Docker image

```bash
# Log in to ACR
az acr login --name $ACR_NAME

# Build the production image
cd backend
docker build -t $ACR_NAME.azurecr.io/smartap-api:latest -f Dockerfile.prod .

# Test locally first
docker run --rm -p 8000:8000 \
  -e DATABASE_URL=sqlite+aiosqlite:///./test.db \
  -e SECRET_KEY=test-secret-key \
  $ACR_NAME.azurecr.io/smartap-api:latest

# Verify: curl http://localhost:8000/api/v1/health

# Push to ACR
docker push $ACR_NAME.azurecr.io/smartap-api:latest
```

### 2.2 Create Backend App Service

```bash
# Get ACR credentials
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_PLAN \
  --name $BACKEND_APP \
  --container-image-name $ACR_NAME.azurecr.io/smartap-api:latest \
  --container-registry-url https://$ACR_NAME.azurecr.io \
  --container-registry-user $ACR_NAME \
  --container-registry-password "$ACR_PASSWORD"
```

### 2.3 Configure Backend Environment Variables

Retrieve connection strings first:

```bash
# PostgreSQL connection string
PG_HOST=$(az postgres flexible-server show \
  --resource-group $RESOURCE_GROUP \
  --name $PG_SERVER \
  --query fullyQualifiedDomainName -o tsv)

# Redis connection string
REDIS_KEY=$(az redis list-keys \
  --resource-group $RESOURCE_GROUP \
  --name $REDIS_NAME \
  --query primaryKey -o tsv)

REDIS_HOST=$(az redis show \
  --resource-group $RESOURCE_GROUP \
  --name $REDIS_NAME \
  --query hostName -o tsv)
```

Set all app settings:

```bash
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP \
  --settings \
    DATABASE_URL="postgresql+asyncpg://${PG_ADMIN_USER}:${PG_ADMIN_PASSWORD}@${PG_HOST}:5432/smartap?sslmode=require" \
    REDIS_ENABLED="true" \
    REDIS_URL="rediss://:${REDIS_KEY}@${REDIS_HOST}:6380/0" \
    APP_ENV="production" \
    SECRET_KEY="$(openssl rand -hex 32)" \
    ALGORITHM="HS256" \
    ACCESS_TOKEN_EXPIRE_MINUTES="30" \
    CORS_ORIGINS="https://${FRONTEND_APP}.azurewebsites.net" \
    DEBUG="false" \
    LOG_LEVEL="info" \
    WEBSITES_PORT="8000" \
    AI_PROVIDER="azure" \
    AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com" \
    AZURE_OPENAI_API_KEY="your-key" \
    AZURE_OPENAI_DEPLOYMENT="gpt-4o"
```

> **Important:** `WEBSITES_PORT=8000` tells Azure to route traffic to the container's port 8000.

### 2.4 Allow Azure services to access PostgreSQL

```bash
az postgres flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --name $PG_SERVER \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

> **Production:** Use VNet integration instead of firewall rules for better security.

### 2.5 Enable logging

```bash
az webapp log config \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP \
  --docker-container-logging filesystem

# View logs
az webapp log tail --resource-group $RESOURCE_GROUP --name $BACKEND_APP
```

### 2.6 Verify

```bash
BACKEND_URL="https://${BACKEND_APP}.azurewebsites.net"
curl -s "$BACKEND_URL/api/v1/health"
```

---

## 3. Deploy the Frontend

### 3.1 Restore standalone output for Docker

The frontend Dockerfile uses Next.js `standalone` output. Make sure `next.config.ts` has:

```typescript
const nextConfig: NextConfig = {
  reactCompiler: true,
  output: 'standalone',
};
```

> **Note:** If you added `@opennextjs/cloudflare` for Cloudflare deployment, the Docker
> deployment uses the existing `Dockerfile` which runs `npm run build` (standard Next.js build)
> and copies the standalone output. Both can coexist.

### 3.2 Build & push Docker image

```bash
cd frontend

# Build with the backend API URL baked in
docker build \
  -t $ACR_NAME.azurecr.io/smartap-web:latest \
  --build-arg REACT_APP_API_URL=https://${BACKEND_APP}.azurewebsites.net/api/v1 \
  .

# Test locally
docker run --rm -p 3000:3000 $ACR_NAME.azurecr.io/smartap-web:latest
# Verify: curl http://localhost:3000

# Push to ACR
docker push $ACR_NAME.azurecr.io/smartap-web:latest
```

### 3.3 Create Frontend App Service

```bash
az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_PLAN \
  --name $FRONTEND_APP \
  --container-image-name $ACR_NAME.azurecr.io/smartap-web:latest \
  --container-registry-url https://$ACR_NAME.azurecr.io \
  --container-registry-user $ACR_NAME \
  --container-registry-password "$ACR_PASSWORD"
```

### 3.4 Configure Frontend Environment Variables

```bash
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $FRONTEND_APP \
  --settings \
    NEXT_PUBLIC_API_URL="https://${BACKEND_APP}.azurewebsites.net/api/v1" \
    WEBSITES_PORT="3000" \
    NODE_ENV="production"
```

> **Note:** `NEXT_PUBLIC_*` variables used in client-side code are baked in at build time.
> If you change the backend URL, you must **rebuild** the frontend image.
> For server-side code, runtime env vars work normally.

### 3.5 Verify

```bash
FRONTEND_URL="https://${FRONTEND_APP}.azurewebsites.net"
curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL"
# Should return 200
```

---

## 4. Configure Custom Domains & SSL

### Add a custom domain

```bash
# Backend
az webapp config hostname add \
  --resource-group $RESOURCE_GROUP \
  --webapp-name $BACKEND_APP \
  --hostname api.smartap.yourdomain.com

# Frontend
az webapp config hostname add \
  --resource-group $RESOURCE_GROUP \
  --webapp-name $FRONTEND_APP \
  --hostname smartap.yourdomain.com
```

### Enable free managed SSL

```bash
az webapp config ssl bind \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP \
  --certificate-thumbprint $(az webapp config ssl create \
    --resource-group $RESOURCE_GROUP \
    --name $BACKEND_APP \
    --hostname api.smartap.yourdomain.com \
    --query thumbprint -o tsv) \
  --ssl-type SNI

# Repeat for frontend
```

### Update CORS after custom domain

```bash
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP \
  --settings CORS_ORIGINS="https://smartap.yourdomain.com"
```

---

## 5. CI/CD with GitHub Actions

Create `.github/workflows/deploy-azure.yml`:

```yaml
name: Deploy to Azure App Service

on:
  push:
    branches: [main]

env:
  ACR_NAME: smartapacr
  RESOURCE_GROUP: smartap-rg
  BACKEND_APP: smartap-api
  FRONTEND_APP: smartap-web

jobs:
  build-and-deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Log in to Azure
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Log in to ACR
        run: az acr login --name ${{ env.ACR_NAME }}

      - name: Build & push backend image
        run: |
          cd backend
          docker build -t ${{ env.ACR_NAME }}.azurecr.io/smartap-api:${{ github.sha }} \
                       -t ${{ env.ACR_NAME }}.azurecr.io/smartap-api:latest \
                       -f Dockerfile.prod .
          docker push ${{ env.ACR_NAME }}.azurecr.io/smartap-api --all-tags

      - name: Deploy backend
        uses: azure/webapps-deploy@v3
        with:
          app-name: ${{ env.BACKEND_APP }}
          images: ${{ env.ACR_NAME }}.azurecr.io/smartap-api:${{ github.sha }}

  build-and-deploy-frontend:
    runs-on: ubuntu-latest
    needs: build-and-deploy-backend
    steps:
      - uses: actions/checkout@v4

      - name: Log in to Azure
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Log in to ACR
        run: az acr login --name ${{ env.ACR_NAME }}

      - name: Build & push frontend image
        run: |
          cd frontend
          docker build -t ${{ env.ACR_NAME }}.azurecr.io/smartap-web:${{ github.sha }} \
                       -t ${{ env.ACR_NAME }}.azurecr.io/smartap-web:latest \
                       --build-arg REACT_APP_API_URL=https://${{ env.BACKEND_APP }}.azurewebsites.net/api/v1 \
                       .
          docker push ${{ env.ACR_NAME }}.azurecr.io/smartap-web --all-tags

      - name: Deploy frontend
        uses: azure/webapps-deploy@v3
        with:
          app-name: ${{ env.FRONTEND_APP }}
          images: ${{ env.ACR_NAME }}.azurecr.io/smartap-web:${{ github.sha }}
```

### Set up GitHub Secrets

```bash
# Create a service principal for GitHub Actions
az ad sp create-for-rbac \
  --name smartap-github-deploy \
  --role contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/$RESOURCE_GROUP \
  --sdk-auth
```

Copy the JSON output and add it as `AZURE_CREDENTIALS` in your GitHub repo → Settings → Secrets.

---

## 6. Monitoring & Logging

### Enable Application Insights

```bash
# Create Application Insights
az monitor app-insights component create \
  --app smartap-insights \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP \
  --application-type web

APPINSIGHTS_KEY=$(az monitor app-insights component show \
  --app smartap-insights \
  --resource-group $RESOURCE_GROUP \
  --query instrumentationKey -o tsv)

# Add to backend
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY="$APPINSIGHTS_KEY"
```

### Stream logs in real time

```bash
# Backend logs
az webapp log tail --resource-group $RESOURCE_GROUP --name $BACKEND_APP

# Frontend logs
az webapp log tail --resource-group $RESOURCE_GROUP --name $FRONTEND_APP
```

### Health check configuration

```bash
# Backend health check
az webapp config set \
  --resource-group $RESOURCE_GROUP \
  --name $BACKEND_APP \
  --generic-configurations '{"healthCheckPath": "/api/v1/health"}'

# Frontend health check
az webapp config set \
  --resource-group $RESOURCE_GROUP \
  --name $FRONTEND_APP \
  --generic-configurations '{"healthCheckPath": "/"}'
```

---

## 7. Troubleshooting

### Container won't start

```bash
# Check container logs
az webapp log tail --resource-group $RESOURCE_GROUP --name $BACKEND_APP

# SSH into the container
az webapp ssh --resource-group $RESOURCE_GROUP --name $BACKEND_APP
```

### Database connection refused

- Ensure the firewall rule allows Azure services (see step 2.4)
- Verify `?sslmode=require` is in the `DATABASE_URL`
- Check the PostgreSQL server is running: `az postgres flexible-server show --name $PG_SERVER --resource-group $RESOURCE_GROUP`

### CORS errors

- Backend `CORS_ORIGINS` must include the exact frontend URL (with `https://`, no trailing slash)
- After adding custom domains, update `CORS_ORIGINS` to match

### Slow cold starts

- Scale to `P1v3` or higher plan to enable Always On:
  ```bash
  az webapp config set \
    --resource-group $RESOURCE_GROUP \
    --name $BACKEND_APP \
    --always-on true
  ```

### Estimated monthly cost (Basic tier)

| Resource | SKU | ~Cost/month |
|----------|-----|-------------|
| App Service Plan (B1) | 1 core, 1.75 GB | $13 |
| PostgreSQL Flexible (B1ms) | 1 vCore, 2 GB | $25 |
| Azure Cache for Redis (C0) | 250 MB | $16 |
| Container Registry (Basic) | 10 GB | $5 |
| **Total** | | **~$59** |

> Scale up resources as needed for production workloads. Use `P1v3` App Service ($115/mo) for Always On and better performance.

---

## Quick Reference

| Resource | URL |
|----------|-----|
| Backend API | `https://smartap-api.azurewebsites.net/api/v1` |
| Swagger Docs | `https://smartap-api.azurewebsites.net/docs` |
| Frontend | `https://smartap-web.azurewebsites.net` |
| Azure Portal | `https://portal.azure.com/#@/resource/subscriptions/.../resourceGroups/smartap-rg` |
