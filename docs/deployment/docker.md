# Docker Deployment Guide

This guide covers deploying SmartAP using Docker and Docker Compose.

## Prerequisites

- Docker 24.0+
- Docker Compose 2.20+
- 4GB RAM minimum (8GB recommended)
- 20GB disk space

## Quick Start

### Development Environment

```bash
# Clone repository
git clone https://github.com/your-org/smartap.git
cd smartap

# Copy environment template
cp .env.example .env

# Edit .env with your settings
# At minimum, set:
# - GITHUB_TOKEN (for AI models)
# - JWT_SECRET_KEY (generate with: openssl rand -hex 32)

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

Access points:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **pgAdmin**: http://localhost:5050 (dev only)

### Production Environment

```bash
# Set production environment variables
export DB_PASSWORD=$(openssl rand -hex 16)
export JWT_SECRET_KEY=$(openssl rand -hex 32)
export GITHUB_TOKEN=your_github_token

# Use production compose file
docker-compose -f docker-compose.prod.yml up -d
```

---

## Docker Compose Files

### Development (docker-compose.yml)

Includes:
- SmartAP API (port 8000)
- PostgreSQL 16 (port 5432)
- Redis 7 (port 6379)
- pgAdmin (port 5050)

### Production (docker-compose.prod.yml)

Includes:
- SmartAP API with health checks
- PostgreSQL with persistent volume
- Redis with AOF persistence
- Nginx reverse proxy with TLS
- Prometheus metrics collection

---

## Service Configuration

### API Service

```yaml
services:
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/smartap
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### PostgreSQL Service

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: smartap
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: smartap
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U smartap"]
      interval: 10s
      timeout: 5s
      retries: 5
```

### Redis Service

```yaml
services:
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
```

---

## Building Images

### Development Build

```bash
cd backend
docker build -t smartap-api:dev .
```

### Production Build

```bash
cd backend
docker build -f Dockerfile.prod -t smartap-api:latest .
```

### Multi-Platform Build

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/your-org/smartap:latest \
  --push .
```

---

## Volume Management

### Data Persistence

```bash
# List volumes
docker volume ls | grep smartap

# Backup PostgreSQL data
docker run --rm \
  -v smartap_postgres_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/postgres_backup.tar.gz /data

# Restore PostgreSQL data
docker run --rm \
  -v smartap_postgres_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/postgres_backup.tar.gz -C /
```

### Cleanup

```bash
# Remove stopped containers
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

---

## Networking

### Internal Network

Services communicate via internal Docker network:

```yaml
networks:
  smartap-network:
    driver: bridge
```

Service discovery by container name:
- `api` → SmartAP API
- `db` → PostgreSQL
- `redis` → Redis

### External Access

Production setup with Nginx:

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
```

---

## Health Checks

### API Health

```bash
# Basic health check
curl http://localhost:8000/api/v1/health

# Detailed health check
curl http://localhost:8000/api/v1/health/detailed
```

Response:
```json
{
  "status": "healthy",
  "version": "3.0.0",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2026-01-10T12:00:00Z"
}
```

### Container Health

```bash
# Check all service health
docker-compose ps

# Inspect specific service
docker inspect --format='{{.State.Health.Status}}' smartap-api-1
```

---

## Logging

### View Logs

```bash
# All services
docker-compose logs

# Specific service with follow
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api
```

### Log Configuration

Set in environment:
```bash
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json         # json, text
```

### Log Aggregation

For production, configure logging driver:

```yaml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## Scaling

### Horizontal Scaling

```bash
# Scale API to 3 instances
docker-compose up -d --scale api=3
```

With load balancer:

```yaml
services:
  nginx:
    # ... nginx config ...
    depends_on:
      - api

  api:
    deploy:
      replicas: 3
```

### Resource Limits

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G
```

---

## Troubleshooting

### Common Issues

**Container won't start:**
```bash
# Check logs
docker-compose logs api

# Check if ports are in use
netstat -tulpn | grep 8000
```

**Database connection failed:**
```bash
# Verify database is running
docker-compose exec db pg_isready

# Check connection string
docker-compose exec api env | grep DATABASE_URL
```

**Out of memory:**
```bash
# Check container stats
docker stats

# Increase memory limit in docker-compose.yml
```

### Debug Mode

```bash
# Run with debug output
docker-compose up --build

# Shell into container
docker-compose exec api /bin/bash

# Run migrations manually
docker-compose exec api alembic upgrade head
```

---

## Security Considerations

1. **Never expose database ports** in production
2. **Use secrets management** for sensitive values
3. **Enable TLS** via reverse proxy
4. **Regular image updates** for security patches
5. **Network isolation** between services

See [SECURITY.md](../../SECURITY.md) for complete security guidelines.
