# SmartAP Deployment Guide

## Table of Contents
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Production Configuration](#production-configuration)
- [Monitoring & Logging](#monitoring--logging)
- [Scaling](#scaling)
- [Troubleshooting](#troubleshooting)

---

## Local Development

### Prerequisites
- Python 3.11+
- PostgreSQL 16+ (or SQLite for dev)
- Redis 7+ (optional, for caching)

### Setup

1. **Clone repository**:
   ```bash
   git clone https://github.com/your-org/smartap.git
   cd smartap/backend
   ```

2. **Create virtual environment**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1  # Windows
   # source venv/bin/activate    # Linux/Mac
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt --pre
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Initialize database**:
   ```bash
   python -m src.db.seed
   ```

6. **Run development server**:
   ```bash
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Access API**:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Health check: http://localhost:8000/api/v1/health

---

## Docker Deployment

### Build Image

```bash
# Development image
docker build -t smartap-api:dev -f Dockerfile .

# Production image
docker build -t smartap-api:latest -f Dockerfile.prod .
```

### Run with Docker Compose

**Development:**
```bash
docker-compose up -d
```

**Production:**
```bash
# Set environment variables
export DB_PASSWORD=your_secure_password
export GITHUB_TOKEN=your_github_token

# Start services
docker-compose -f docker-compose.prod.yml up -d
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| API | 8000 | SmartAP FastAPI application |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache |
| pgAdmin | 5050 | Database management (dev only) |
| Redis Commander | 8081 | Redis management (dev only) |

### Useful Commands

```bash
# View logs
docker-compose logs -f api

# Restart API
docker-compose restart api

# Run database migrations
docker-compose exec api python -m src.db.seed

# Access container shell
docker-compose exec api /bin/bash

# Stop all services
docker-compose down

# Clean up (removes volumes)
docker-compose down -v
```

---

## Kubernetes Deployment

### Prerequisites
- Kubernetes cluster (v1.24+)
- kubectl configured
- Ingress controller (nginx, traefik, or ALB)
- Persistent volume provisioner
- (Optional) cert-manager for TLS

### Deployment Steps

1. **Create namespace**:
   ```bash
   kubectl apply -f k8s/namespace.yaml
   ```

2. **Update secrets** (IMPORTANT):
   ```bash
   # Edit k8s/secret.yaml with actual credentials
   # Or use sealed-secrets/external-secrets
   kubectl apply -f k8s/secret.yaml
   ```

3. **Create ConfigMap**:
   ```bash
   kubectl apply -f k8s/configmap.yaml
   ```

4. **Create PersistentVolumeClaims**:
   ```bash
   kubectl apply -f k8s/pvc.yaml
   ```

5. **Deploy PostgreSQL**:
   ```bash
   kubectl apply -f k8s/postgres-deployment.yaml
   
   # Wait for PostgreSQL to be ready
   kubectl wait --for=condition=ready pod -l component=database -n smartap --timeout=120s
   ```

6. **Deploy Redis**:
   ```bash
   kubectl apply -f k8s/redis-deployment.yaml
   
   # Wait for Redis to be ready
   kubectl wait --for=condition=ready pod -l component=cache -n smartap --timeout=60s
   ```

7. **Deploy API**:
   ```bash
   kubectl apply -f k8s/api-deployment.yaml
   
   # Wait for API to be ready
   kubectl wait --for=condition=ready pod -l component=api -n smartap --timeout=120s
   ```

8. **Configure autoscaling**:
   ```bash
   kubectl apply -f k8s/hpa.yaml
   ```

9. **Setup Ingress**:
   ```bash
   # Update k8s/ingress.yaml with your domain
   kubectl apply -f k8s/ingress.yaml
   ```

### Verify Deployment

```bash
# Check all resources
kubectl get all -n smartap

# Check pod status
kubectl get pods -n smartap

# Check logs
kubectl logs -f deployment/smartap-api -n smartap

# Check HPA status
kubectl get hpa -n smartap

# Describe deployment
kubectl describe deployment smartap-api -n smartap
```

### Access Services

```bash
# Port forward for testing
kubectl port-forward -n smartap svc/smartap-api 8000:80

# Access via ingress (after DNS setup)
curl https://smartap.example.com/api/v1/health
```

---

## Production Configuration

### Environment Variables

**Required:**
- `DATABASE_URL`: PostgreSQL connection string
- `DB_PASSWORD`: Database password (from secret)
- `GITHUB_TOKEN`: GitHub PAT for AI models
- `REDIS_ENABLED`: Enable caching (true)
- `REDIS_URL`: Redis connection string

**Recommended:**
- `LOG_LEVEL`: INFO or WARNING for production
- `LOG_FORMAT`: json for structured logging
- `DATABASE_POOL_SIZE`: 20-50 (based on load)
- `CACHE_TTL_SECONDS`: 3600-7200

### Security Checklist

- [ ] Use strong database passwords
- [ ] Store secrets in Kubernetes Secrets or external secret manager
- [ ] Enable TLS/SSL for API (cert-manager + Let's Encrypt)
- [ ] Configure network policies
- [ ] Use non-root container user (already configured)
- [ ] Enable pod security policies
- [ ] Set resource limits and requests
- [ ] Configure RBAC properly
- [ ] Enable audit logging
- [ ] Use private container registry

### Database Configuration

**PostgreSQL Performance Tuning:**

```sql
-- Edit postgresql.conf
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
work_mem = 10MB
min_wal_size = 1GB
max_wal_size = 4GB
max_worker_processes = 8
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
```

**Create Indexes:**

```sql
-- Run after initial deployment
CREATE INDEX idx_invoices_status_created ON invoices(status, created_at);
CREATE INDEX idx_pos_vendor_status ON purchase_orders(vendor_id, status);
CREATE INDEX idx_matching_document_id ON matching_results(document_id);
CREATE INDEX idx_risk_document_id ON risk_assessments(document_id);
```

### Redis Configuration

```yaml
# Redis config (already in k8s manifests)
maxmemory: 1gb
maxmemory-policy: allkeys-lru
save: 900 1 300 10 60 10000  # Persistence
appendonly: yes  # AOF persistence
```

---

## Monitoring & Logging

### Health Check Endpoints

SmartAP provides multiple health check endpoints for different monitoring needs:

| Endpoint | Auth | Description | Use Case |
|----------|------|-------------|----------|
| `/api/v1/health` | No | Basic health check | Load balancer probes |
| `/api/v1/health/detailed` | No | Component-level health | Kubernetes readiness |
| `/api/v1/health/full` | No | Full system health | Deep diagnostics |
| `/api/v1/metrics` | No | Performance metrics | APM integration |
| `/api/v1/metrics/endpoints` | No | Per-endpoint stats | Performance tuning |
| `/api/v1/metrics/circuit-breakers` | No | Circuit breaker status | Integration monitoring |

**Health Check Examples:**
```bash
# Basic health (for load balancers)
curl http://localhost:8000/api/v1/health

# Detailed health (for Kubernetes readiness)
curl http://localhost:8000/api/v1/health/detailed

# Full health with integrations
curl http://localhost:8000/api/v1/health/full

# Application metrics (last 60 minutes)
curl http://localhost:8000/api/v1/metrics?minutes=60

# Circuit breaker status
curl http://localhost:8000/api/v1/metrics/circuit-breakers
```

### Kubernetes Probes Configuration

```yaml
# In k8s/api-deployment.yaml
livenessProbe:
  httpGet:
    path: /api/v1/health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /api/v1/health/detailed
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
```

### Database and Redis Health

```bash
# Database connection
kubectl exec -it deployment/smartap-postgres -n smartap -- pg_isready -U smartap

# Redis connection
kubectl exec -it deployment/smartap-redis -n smartap -- redis-cli ping
```

### Prometheus Metrics

**Install Prometheus:**
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring
```

**Add ServiceMonitor:**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: smartap-api
  namespace: smartap
spec:
  selector:
    matchLabels:
      app: smartap
      component: api
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

### Logging with ELK/EFK

**Structured JSON logs** are configured automatically when `LOG_FORMAT=json`.

**Ship logs to Elasticsearch:**
1. Install Filebeat or Fluentd as DaemonSet
2. Configure to read container logs
3. Forward to Elasticsearch
4. View in Kibana

**Example Fluentd config:**
```yaml
<match kubernetes.**smartap**>
  @type elasticsearch
  host elasticsearch.logging.svc.cluster.local
  port 9200
  index_name smartap
  type_name _doc
</match>
```

---

## Scaling

### Horizontal Pod Autoscaling

HPA is configured to scale based on CPU and memory:

```yaml
# k8s/hpa.yaml
minReplicas: 3
maxReplicas: 10
metrics:
  - cpu: 70%
  - memory: 80%
```

**Monitor HPA:**
```bash
kubectl get hpa -n smartap -w
```

**Manual scaling:**
```bash
kubectl scale deployment smartap-api -n smartap --replicas=5
```

### Vertical Scaling

**Update resource limits:**
```bash
# Edit k8s/api-deployment.yaml
resources:
  requests:
    cpu: "1"
    memory: "1Gi"
  limits:
    cpu: "4"
    memory: "4Gi"

# Apply changes
kubectl apply -f k8s/api-deployment.yaml
```

### Database Scaling

**Read replicas:**
1. Setup PostgreSQL replication
2. Update connection strings for read queries
3. Use read replicas for reporting/analytics

**Connection pooling:**
- Already configured via `DATABASE_POOL_SIZE`
- Consider external pooler like PgBouncer for 100+ connections

### Cache Scaling

**Redis Cluster:**
```bash
# For high availability
helm install redis bitnami/redis-cluster \
  --set cluster.nodes=6 \
  --set cluster.replicas=1
```

---

## Troubleshooting

### API Not Starting

```bash
# Check pod logs
kubectl logs -f deployment/smartap-api -n smartap

# Check pod events
kubectl describe pod <pod-name> -n smartap

# Check configuration
kubectl get configmap smartap-config -n smartap -o yaml
```

**Common issues:**
- Database connection failed → Check DATABASE_URL and credentials
- Redis connection failed → Check REDIS_URL and Redis pod status
- Import errors → Rebuild Docker image with correct dependencies

### Database Connection Issues

```bash
# Test database connection
kubectl exec -it deployment/smartap-postgres -n smartap -- psql -U smartap -d smartap

# Check database logs
kubectl logs deployment/smartap-postgres -n smartap

# Verify secret
kubectl get secret smartap-secrets -n smartap -o jsonpath='{.data.DB_PASSWORD}' | base64 -d
```

### High Memory Usage

```bash
# Check resource usage
kubectl top pods -n smartap

# Describe pod
kubectl describe pod <pod-name> -n smartap

# Check HPA
kubectl get hpa -n smartap
```

**Solutions:**
- Increase memory limits
- Enable HPA to scale horizontally
- Optimize database queries
- Tune Redis maxmemory

### Slow API Response

**Diagnosis:**
```bash
# Check API logs for slow queries
kubectl logs deployment/smartap-api -n smartap | grep -i "slow"

# Check database performance
kubectl exec -it deployment/smartap-postgres -n smartap -- \
  psql -U smartap -d smartap -c "SELECT * FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;"

# Check Redis stats
kubectl exec -it deployment/smartap-redis -n smartap -- redis-cli INFO stats
```

**Solutions:**
- Enable Redis caching: `REDIS_ENABLED=true`
- Add database indexes (see Production Configuration)
- Scale up pods with HPA
- Optimize AI model calls

### Pod Crashes/Restarts

```bash
# Check crash logs
kubectl logs <pod-name> -n smartap --previous

# Check pod events
kubectl get events -n smartap --sort-by='.lastTimestamp'

# Check resource limits
kubectl describe pod <pod-name> -n smartap | grep -A 5 "Limits"
```

**Common causes:**
- OOMKilled → Increase memory limits
- CrashLoopBackOff → Check startup logs
- Liveness probe failure → Increase timeout or fix health endpoint

### Ingress Issues

```bash
# Check ingress
kubectl get ingress -n smartap
kubectl describe ingress smartap-ingress -n smartap

# Check ingress controller logs
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
```

**Common issues:**
- 502 Bad Gateway → API pods not ready
- 404 Not Found → Check path configuration
- 413 Request Too Large → Increase `proxy-body-size` annotation

---

## Backup & Recovery

### Database Backup

```bash
# Create backup
kubectl exec deployment/smartap-postgres -n smartap -- \
  pg_dump -U smartap smartap > smartap_backup_$(date +%Y%m%d).sql

# Automated backups with CronJob
kubectl apply -f k8s/backup-cronjob.yaml
```

### Restore Database

```bash
# Restore from backup
kubectl exec -i deployment/smartap-postgres -n smartap -- \
  psql -U smartap smartap < smartap_backup_20260107.sql
```

### Persistent Volume Snapshots

```bash
# Create snapshot (cloud provider specific)
# AWS EBS
aws ec2 create-snapshot --volume-id vol-xxxxx

# GCP
gcloud compute disks snapshot postgres-disk

# Azure
az snapshot create --resource-group myResourceGroup --source myDisk
```

---

## Maintenance

### Rolling Updates

```bash
# Update image
kubectl set image deployment/smartap-api -n smartap \
  api=smartap-api:v1.1.0

# Check rollout status
kubectl rollout status deployment/smartap-api -n smartap

# Rollback if needed
kubectl rollout undo deployment/smartap-api -n smartap
```

### Database Migrations

```bash
# Run migrations
kubectl exec -it deployment/smartap-api -n smartap -- \
  python -m alembic upgrade head
```

### Clean Up Old Data

```bash
# Delete old invoices (>90 days)
kubectl exec -it deployment/smartap-postgres -n smartap -- \
  psql -U smartap -d smartap -c \
  "DELETE FROM invoices WHERE created_at < NOW() - INTERVAL '90 days';"
```

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/your-org/smartap/issues
- Documentation: https://docs.smartap.io
- Email: support@smartap.io

**Emergency Contact:**
- On-call: +1-XXX-XXX-XXXX
- Slack: #smartap-support
