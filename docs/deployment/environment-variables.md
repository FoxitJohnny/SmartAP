# Environment Variables Reference

This document lists all environment variables used to configure SmartAP.

## Quick Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Yes | - | Secret key for JWT tokens |
| `GITHUB_TOKEN` | Yes* | - | GitHub Models API token |
| `REDIS_URL` | No | - | Redis connection string |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |

*Required for AI features

---

## Database Configuration

### DATABASE_URL
PostgreSQL connection string in SQLAlchemy format.

```bash
# Async driver (recommended)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# Sync driver (for migrations)
DATABASE_URL_SYNC=postgresql://user:password@host:5432/dbname
```

**Examples:**
```bash
# Local development
DATABASE_URL=postgresql+asyncpg://smartap:devpassword@localhost:5432/smartap

# Docker Compose
DATABASE_URL=postgresql+asyncpg://smartap:${DB_PASSWORD}@db:5432/smartap

# Production with SSL
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db.example.com:5432/smartap?ssl=require
```

### DATABASE_POOL_SIZE
Number of connections to maintain in the pool.

```bash
DATABASE_POOL_SIZE=10  # Default: 5
```

### DATABASE_MAX_OVERFLOW
Maximum connections above pool size.

```bash
DATABASE_MAX_OVERFLOW=20  # Default: 10
```

---

## Authentication

### JWT_SECRET_KEY
**Required.** Secret key for signing JWT tokens.

```bash
# Generate a secure key
JWT_SECRET_KEY=$(openssl rand -hex 32)
```

⚠️ **Security:** Never commit this value. Use secrets management in production.

### JWT_ALGORITHM
Algorithm for JWT signing.

```bash
JWT_ALGORITHM=HS256  # Default
```

### JWT_ACCESS_TOKEN_EXPIRE_MINUTES
Access token lifetime in minutes.

```bash
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30  # Default
```

### JWT_REFRESH_TOKEN_EXPIRE_DAYS
Refresh token lifetime in days.

```bash
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7  # Default
```

---

## AI Model Configuration

### GITHUB_TOKEN
GitHub Personal Access Token for GitHub Models API.

```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

**Required scopes:** `models:read`

### AI_MODEL_PROVIDER
AI model provider to use.

```bash
AI_MODEL_PROVIDER=github  # Options: github, openai, anthropic, azure
```

### AI_MODEL_NAME
Model identifier.

```bash
AI_MODEL_NAME=gpt-4o  # Default for GitHub Models
```

### AI_MODEL_TEMPERATURE
Model temperature for response randomness.

```bash
AI_MODEL_TEMPERATURE=0.0  # Default (deterministic)
```

### OPENAI_API_KEY
OpenAI API key (if using OpenAI provider).

```bash
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
```

### ANTHROPIC_API_KEY
Anthropic API key (if using Anthropic provider).

```bash
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx
```

### AZURE_OPENAI_ENDPOINT
Azure OpenAI endpoint URL.

```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

### AZURE_OPENAI_API_KEY
Azure OpenAI API key.

```bash
AZURE_OPENAI_API_KEY=xxxxxxxxxxxxxxxxxxxx
```

---

## Redis Configuration

### REDIS_URL
Redis connection string.

```bash
# Local development
REDIS_URL=redis://localhost:6379/0

# With password
REDIS_URL=redis://:password@redis-host:6379/0

# TLS enabled
REDIS_URL=rediss://:password@redis-host:6379/0
```

### REDIS_ENABLED
Enable/disable Redis caching.

```bash
REDIS_ENABLED=true  # Default: false
```

### CACHE_DEFAULT_TTL
Default cache TTL in seconds.

```bash
CACHE_DEFAULT_TTL=300  # Default: 5 minutes
```

---

## API Configuration

### API_HOST
Host to bind the API server.

```bash
API_HOST=0.0.0.0  # Default
```

### API_PORT
Port for the API server.

```bash
API_PORT=8000  # Default
```

### API_WORKERS
Number of Uvicorn workers (production only).

```bash
API_WORKERS=4  # Default: 1
```

### API_RELOAD
Enable auto-reload for development.

```bash
API_RELOAD=true  # Default: false
```

---

## CORS Configuration

### CORS_ORIGINS
Allowed origins for CORS requests.

```bash
# Single origin
CORS_ORIGINS=https://app.example.com

# Multiple origins (comma-separated)
CORS_ORIGINS=https://app.example.com,https://admin.example.com

# Development (allow all)
CORS_ORIGINS=*
```

### CORS_ALLOW_CREDENTIALS
Allow credentials in CORS requests.

```bash
CORS_ALLOW_CREDENTIALS=true  # Default
```

### CORS_ALLOW_METHODS
Allowed HTTP methods.

```bash
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,PATCH  # Default: *
```

### CORS_ALLOW_HEADERS
Allowed request headers.

```bash
CORS_ALLOW_HEADERS=Authorization,Content-Type  # Default: *
```

---

## Rate Limiting

### RATE_LIMIT_ENABLED
Enable rate limiting middleware.

```bash
RATE_LIMIT_ENABLED=true  # Default
```

### RATE_LIMIT_PER_MINUTE
Requests allowed per minute per client.

```bash
RATE_LIMIT_PER_MINUTE=60  # Default
```

### RATE_LIMIT_PER_HOUR
Requests allowed per hour per client.

```bash
RATE_LIMIT_PER_HOUR=1000  # Default
```

### RATE_LIMIT_BURST
Maximum burst requests in 1 second.

```bash
RATE_LIMIT_BURST=10  # Default
```

---

## Logging

### LOG_LEVEL
Logging verbosity level.

```bash
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### LOG_FORMAT
Log output format.

```bash
LOG_FORMAT=json  # Options: json, text
```

### LOG_FILE
Path to log file (optional).

```bash
LOG_FILE=/var/log/smartap/app.log
```

---

## PDF Processing

### FOXIT_LICENSE_KEY
Foxit PDF SDK license key.

```bash
FOXIT_LICENSE_KEY=xxxxxxxxxxxxxxxxxxxx
```

### FOXIT_LICENSE_SN
Foxit PDF SDK serial number.

```bash
FOXIT_LICENSE_SN=xxxxxxxxxxxxxxxxxxxx
```

### MAX_UPLOAD_SIZE_MB
Maximum file upload size in MB.

```bash
MAX_UPLOAD_SIZE_MB=50  # Default
```

### SUPPORTED_FILE_TYPES
Comma-separated list of allowed file extensions.

```bash
SUPPORTED_FILE_TYPES=pdf,tiff,tif,png,jpeg,jpg  # Default
```

---

## eSign Integration

### FOXIT_ESIGN_API_URL
Foxit eSign API base URL.

```bash
FOXIT_ESIGN_API_URL=https://api.esign.foxit.com
```

### FOXIT_ESIGN_CLIENT_ID
Foxit eSign OAuth client ID.

```bash
FOXIT_ESIGN_CLIENT_ID=xxxxxxxxxxxxxxxxxxxx
```

### FOXIT_ESIGN_CLIENT_SECRET
Foxit eSign OAuth client secret.

```bash
FOXIT_ESIGN_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxx
```

---

## ERP Integration

### ERP_SYNC_ENABLED
Enable ERP synchronization.

```bash
ERP_SYNC_ENABLED=true  # Default: false
```

### QUICKBOOKS_CLIENT_ID
QuickBooks OAuth client ID.

```bash
QUICKBOOKS_CLIENT_ID=xxxxxxxxxxxxxxxxxxxx
```

### QUICKBOOKS_CLIENT_SECRET
QuickBooks OAuth client secret.

```bash
QUICKBOOKS_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxx
```

### NETSUITE_ACCOUNT_ID
NetSuite account ID.

```bash
NETSUITE_ACCOUNT_ID=xxxxxxxxxxxx
```

### NETSUITE_CONSUMER_KEY
NetSuite consumer key.

```bash
NETSUITE_CONSUMER_KEY=xxxxxxxxxxxxxxxxxxxx
```

### NETSUITE_CONSUMER_SECRET
NetSuite consumer secret.

```bash
NETSUITE_CONSUMER_SECRET=xxxxxxxxxxxxxxxxxxxx
```

---

## Feature Flags

### FEATURE_ESIGN_ENABLED
Enable eSignature features.

```bash
FEATURE_ESIGN_ENABLED=true  # Default: false
```

### FEATURE_ERP_SYNC_ENABLED
Enable ERP synchronization features.

```bash
FEATURE_ERP_SYNC_ENABLED=true  # Default: false
```

### FEATURE_APPROVAL_WORKFLOW_ENABLED
Enable approval workflow features.

```bash
FEATURE_APPROVAL_WORKFLOW_ENABLED=true  # Default: true
```

---

## Development

### DEBUG
Enable debug mode.

```bash
DEBUG=true  # Default: false
```

### TESTING
Enable testing mode.

```bash
TESTING=true  # Default: false
```

### SEED_DATABASE
Seed database with sample data on startup.

```bash
SEED_DATABASE=true  # Default: false
```

---

## Example .env Files

### Development

```bash
# .env.development
DATABASE_URL=postgresql+asyncpg://smartap:devpassword@localhost:5432/smartap_dev
JWT_SECRET_KEY=dev-secret-key-not-for-production
GITHUB_TOKEN=ghp_your_development_token
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=DEBUG
DEBUG=true
CORS_ORIGINS=*
```

### Production

```bash
# .env.production
DATABASE_URL=postgresql+asyncpg://smartap:${DB_PASSWORD}@db.internal:5432/smartap
JWT_SECRET_KEY=${JWT_SECRET_KEY}  # From secrets manager
GITHUB_TOKEN=${GITHUB_TOKEN}  # From secrets manager
REDIS_URL=rediss://:${REDIS_PASSWORD}@redis.internal:6379/0
REDIS_ENABLED=true
LOG_LEVEL=INFO
LOG_FORMAT=json
CORS_ORIGINS=https://smartap.example.com
RATE_LIMIT_ENABLED=true
```

### Testing

```bash
# .env.test
DATABASE_URL=sqlite+aiosqlite:///:memory:
JWT_SECRET_KEY=test-secret-key
GITHUB_TOKEN=test-token
REDIS_ENABLED=false
LOG_LEVEL=WARNING
TESTING=true
```

---

## Security Notes

1. **Never commit secrets** - Use `.env.example` as a template
2. **Use secrets management** - AWS Secrets Manager, HashiCorp Vault, etc.
3. **Rotate credentials regularly** - Especially JWT secrets
4. **Validate in production** - Ensure all required variables are set
5. **Audit access** - Log when sensitive configs are accessed
