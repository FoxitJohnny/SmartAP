# SmartAP Helm Chart

Deploy SmartAP - Intelligent Invoice & Accounts Payable Automation Hub on Kubernetes.

## TL;DR

```bash
# Add Helm repository (if published)
helm repo add smartap https://charts.smartap.example.com
helm repo update

# Install with default values
helm install smartap smartap/smartap

# Or install from local chart
helm install smartap ./helm/smartap
```

## Introduction

This Helm chart deploys SmartAP on a Kubernetes cluster. SmartAP is an AI-powered invoice processing system that automates invoice extraction, validation, risk assessment, and approval workflows.

**Features:**
- 🤖 AI-powered invoice extraction (OCR + LLM)
- 🔍 Fraud and duplicate detection
- 📊 Multi-stage approval workflows
- 🔗 ERP integrations (QuickBooks, Xero, SAP)
- 📄 Foxit PDF processing
- 🔐 Enterprise security and audit trails
- 📈 Auto-scaling and high availability

## Prerequisites

- Kubernetes 1.23+
- Helm 3.8+
- PV provisioner support in the underlying infrastructure (for PostgreSQL and Redis persistence)
- LoadBalancer support (for nginx service) or Ingress controller

### Optional but Recommended

- [cert-manager](https://cert-manager.io/) for automatic TLS certificate management
- [metrics-server](https://github.com/kubernetes-sigs/metrics-server) for HPA support
- [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets) or [External Secrets Operator](https://external-secrets.io/) for secure secret management

## Installing the Chart

### Quick Start (Development)

```bash
# Create namespace
kubectl create namespace smartap

# Install with development values
helm install smartap ./helm/smartap \
  --namespace smartap \
  -f ./helm/smartap/values-dev.yaml \
  --set secrets.postgresPassword=dev_password_123 \
  --set secrets.secretKey=dev-secret-key-$(openssl rand -hex 16) \
  --set secrets.jwtSecret=dev-jwt-secret-$(openssl rand -hex 16) \
  --set secrets.foxitApiKey=your-foxit-api-key
```

Access the application:
```bash
# Port-forward to access locally
kubectl port-forward -n smartap svc/smartap-nginx 8080:80

# Open browser
open http://localhost:8080
```

### Production Deployment

#### Step 1: Generate Secrets

```bash
# Generate strong secrets
export POSTGRES_PASSWORD=$(openssl rand -base64 32)
export SECRET_KEY=$(openssl rand -hex 32)
export JWT_SECRET=$(openssl rand -hex 32)

# Get your Foxit API key from https://developers.foxit.com/
export FOXIT_API_KEY="your-foxit-api-key-here"

# Optional: AI provider API keys
export OPENAI_API_KEY="sk-..."
# or
export ANTHROPIC_API_KEY="sk-ant-..."
```

#### Step 2: Create Sealed Secrets (Recommended)

If using Sealed Secrets:

```bash
# Install sealed-secrets controller
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm install sealed-secrets sealed-secrets/sealed-secrets --namespace kube-system

# Create secret and seal it
kubectl create secret generic smartap-secrets \
  --from-literal=postgresPassword=$POSTGRES_PASSWORD \
  --from-literal=secretKey=$SECRET_KEY \
  --from-literal=jwtSecret=$JWT_SECRET \
  --from-literal=foxitApiKey=$FOXIT_API_KEY \
  --from-literal=openaiApiKey=$OPENAI_API_KEY \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > smartap-sealed-secret.yaml

# Apply sealed secret
kubectl apply -f smartap-sealed-secret.yaml -n smartap
```

#### Step 3: Install Chart

```bash
# Create namespace
kubectl create namespace smartap

# Install with production values
helm install smartap ./helm/smartap \
  --namespace smartap \
  -f ./helm/smartap/values-prod.yaml \
  --set global.domain=smartap.yourdomain.com \
  --set secrets.postgresPassword=$POSTGRES_PASSWORD \
  --set secrets.secretKey=$SECRET_KEY \
  --set secrets.jwtSecret=$JWT_SECRET \
  --set secrets.foxitApiKey=$FOXIT_API_KEY \
  --set secrets.openaiApiKey=$OPENAI_API_KEY
```

#### Step 4: Verify Installation

```bash
# Watch pods come up
kubectl get pods -n smartap -w

# Check services
kubectl get svc -n smartap

# Check ingress
kubectl get ingress -n smartap

# View logs
kubectl logs -n smartap -l app.kubernetes.io/component=backend --tail=100
```

## Configuration

### Values Files

The chart includes three environment-specific values files:

| File | Environment | Use Case |
|------|-------------|----------|
| `values.yaml` | Production (default) | Base configuration with production defaults |
| `values-dev.yaml` | Development | Minimal resources, single replicas, local testing |
| `values-staging.yaml` | Staging | Moderate resources, testing before production |
| `values-prod.yaml` | Production | Full resources, high availability, auto-scaling |

### Key Configuration Options

#### Global Settings

```yaml
global:
  environment: production  # development, staging, production
  domain: smartap.example.com
  imagePullSecrets: []
```

#### Component Replicas

```yaml
backend:
  replicaCount: 2
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
```

#### Resource Limits

```yaml
backend:
  resources:
    requests:
      memory: "512Mi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "2000m"
```

#### Database Configuration

```yaml
postgresql:
  enabled: true  # Set to false if using external database
  persistence:
    enabled: true
    size: 10Gi
    storageClass: "fast-ssd"  # Use your storage class
```

For external databases (AWS RDS, Azure Database, etc.):

```yaml
postgresql:
  enabled: false

config:
  databaseUrl: "postgresql://user:pass@rds.amazonaws.com:5432/smartap"
```

#### Redis Configuration

```yaml
redis:
  enabled: true  # Set to false if using external Redis
  persistence:
    enabled: true
    size: 5Gi
```

For external Redis (ElastiCache, Azure Cache, etc.):

```yaml
redis:
  enabled: false

config:
  redisUrl: "redis://elasticache.amazonaws.com:6379/0"
```

#### Ingress Configuration

```yaml
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: smartap.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: smartap-tls
      hosts:
        - smartap.example.com
```

#### AI Provider Configuration

```yaml
config:
  aiProvider: "openai"  # openai, anthropic, azure
  aiModel: "gpt-4o"
  aiTemperature: "0.1"
  aiMaxTokens: "4096"
```

### All Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.environment` | Environment name | `production` |
| `global.domain` | Application domain | `smartap.example.com` |
| `image.registry` | Docker registry | `docker.io` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `image.tag` | Image tag | `Chart.appVersion` |
| `backend.enabled` | Enable backend service | `true` |
| `backend.replicaCount` | Number of backend replicas | `2` |
| `backend.autoscaling.enabled` | Enable HPA for backend | `true` |
| `backend.autoscaling.minReplicas` | Minimum replicas | `2` |
| `backend.autoscaling.maxReplicas` | Maximum replicas | `10` |
| `frontend.enabled` | Enable frontend service | `true` |
| `frontend.replicaCount` | Number of frontend replicas | `2` |
| `postgresql.enabled` | Enable PostgreSQL | `true` |
| `postgresql.persistence.enabled` | Enable persistence | `true` |
| `postgresql.persistence.size` | PVC size | `10Gi` |
| `postgresql.persistence.storageClass` | Storage class | `""` |
| `redis.enabled` | Enable Redis | `true` |
| `redis.persistence.enabled` | Enable persistence | `true` |
| `redis.persistence.size` | PVC size | `5Gi` |
| `worker.enabled` | Enable Celery workers | `true` |
| `worker.replicaCount` | Number of worker replicas | `2` |
| `scheduler.enabled` | Enable Celery beat scheduler | `true` |
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class | `nginx` |
| `secrets.postgresPassword` | PostgreSQL password | `""` (required) |
| `secrets.secretKey` | App secret key | `""` (required) |
| `secrets.jwtSecret` | JWT secret | `""` (required) |
| `secrets.foxitApiKey` | Foxit API key | `""` (required) |
| `secrets.openaiApiKey` | OpenAI API key | `""` (optional) |
| `secrets.anthropicApiKey` | Anthropic API key | `""` (optional) |
| `config.appName` | Application name | `SmartAP` |
| `config.aiProvider` | AI provider | `openai` |
| `config.aiModel` | AI model | `gpt-4o` |
| `config.corsOrigins` | CORS origins | `["https://smartap.example.com"]` |

See `values.yaml` for all available parameters.

## Upgrading

### Standard Upgrade

```bash
# Upgrade to new version
helm upgrade smartap ./helm/smartap \
  --namespace smartap \
  -f ./helm/smartap/values-prod.yaml \
  --reuse-values
```

### Upgrade with Value Changes

```bash
# Upgrade with new configuration
helm upgrade smartap ./helm/smartap \
  --namespace smartap \
  -f ./helm/smartap/values-prod.yaml \
  --set backend.replicaCount=5
```

### Database Migrations

Database migrations run automatically as a pre-upgrade hook. The migration job:
- Waits for PostgreSQL to be ready
- Runs Alembic migrations
- Must complete successfully before upgrade proceeds

To manually trigger migrations:

```bash
# Run migration job manually
kubectl create job --from=cronjob/smartap-migration manual-migration-$(date +%s) -n smartap
```

### Rollback

```bash
# List releases
helm history smartap -n smartap

# Rollback to previous version
helm rollback smartap -n smartap

# Rollback to specific revision
helm rollback smartap 3 -n smartap
```

## Uninstalling

```bash
# Uninstall release
helm uninstall smartap -n smartap

# Delete PVCs (optional, data will be lost)
kubectl delete pvc -n smartap -l app.kubernetes.io/instance=smartap

# Delete namespace (optional)
kubectl delete namespace smartap
```

## Monitoring and Debugging

### View Logs

```bash
# Backend logs
kubectl logs -n smartap -l app.kubernetes.io/component=backend --tail=100 -f

# Frontend logs
kubectl logs -n smartap -l app.kubernetes.io/component=frontend --tail=100 -f

# Worker logs
kubectl logs -n smartap -l app.kubernetes.io/component=worker --tail=100 -f

# Scheduler logs
kubectl logs -n smartap -l app.kubernetes.io/component=scheduler --tail=100 -f

# All logs
kubectl logs -n smartap -l app.kubernetes.io/name=smartap --tail=50 --prefix=true
```

### Check Resource Usage

```bash
# Pod resource usage
kubectl top pods -n smartap

# Node resource usage
kubectl top nodes
```

### Exec into Pods

```bash
# Backend shell
kubectl exec -it -n smartap deployment/smartap-backend -- /bin/bash

# PostgreSQL shell
kubectl exec -it -n smartap statefulset/smartap-postgresql -- psql -U smartap
```

### Common Issues

#### Pods CrashLooping

```bash
# Check pod status
kubectl describe pod -n smartap <pod-name>

# Check logs
kubectl logs -n smartap <pod-name> --previous
```

**Common causes:**
- Missing required secrets (check `secrets.yaml`)
- Database connection failure (check PostgreSQL logs)
- Insufficient resources (check resource limits)

#### Database Connection Issues

```bash
# Test database connectivity
kubectl run -it --rm debug --image=postgres:16-alpine --restart=Never -n smartap -- \
  psql postgresql://smartap:password@smartap-postgresql:5432/smartap
```

#### Ingress Not Working

```bash
# Check ingress status
kubectl describe ingress smartap -n smartap

# Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller
```

## High Availability

For production deployments:

### Multi-AZ Deployment

```yaml
# values-prod.yaml
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
            - key: app.kubernetes.io/name
              operator: In
              values:
                - smartap
        topologyKey: topology.kubernetes.io/zone
```

### Database HA

For production, use managed databases:

**AWS RDS:**
```yaml
postgresql:
  enabled: false
config:
  databaseUrl: "postgresql://user:pass@smartap-prod.cluster-xxxxx.us-east-1.rds.amazonaws.com:5432/smartap"
```

**Azure Database:**
```yaml
postgresql:
  enabled: false
config:
  databaseUrl: "postgresql://user@smartap-prod:pass@smartap-prod.postgres.database.azure.com:5432/smartap"
```

### Redis HA

For production, use managed Redis:

**AWS ElastiCache:**
```yaml
redis:
  enabled: false
config:
  redisUrl: "redis://smartap-prod.abcdef.ng.0001.use1.cache.amazonaws.com:6379/0"
```

## Security

### Network Policies

Enable network policies for production:

```yaml
networkPolicy:
  enabled: true
```

### Pod Security Standards

The chart follows Pod Security Standards:
- Non-root containers
- Read-only root filesystem where possible
- Capability dropping
- Security context restrictions

### Secrets Management

**Recommended approaches:**

1. **Sealed Secrets** (easiest):
```bash
kubectl create secret generic smartap-secrets \
  --from-literal=postgresPassword=$POSTGRES_PASSWORD \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > smartap-sealed-secret.yaml
```

2. **External Secrets Operator** (most flexible):
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: smartap-secrets
spec:
  secretStoreRef:
    name: aws-secretsmanager
  target:
    name: smartap-secrets
  data:
    - secretKey: postgresPassword
      remoteRef:
        key: /smartap/postgres-password
```

3. **HashiCorp Vault** (enterprise):
```yaml
annotations:
  vault.hashicorp.com/agent-inject: "true"
  vault.hashicorp.com/role: "smartap"
  vault.hashicorp.com/agent-inject-secret-db: "database/creds/smartap"
```

## Performance Tuning

### Celery Workers

Adjust concurrency based on workload:

```yaml
worker:
  replicaCount: 5
  env:
    CELERY_CONCURRENCY: "4"  # 4 threads per worker
```

### Database Connection Pooling

```yaml
config:
  databaseUrl: "postgresql://user:pass@host:5432/smartap?pool_size=20&max_overflow=10"
```

### Resource Limits

For high-traffic deployments:

```yaml
backend:
  resources:
    requests:
      memory: "1Gi"
      cpu: "1000m"
    limits:
      memory: "4Gi"
      cpu: "4000m"
  autoscaling:
    minReplicas: 5
    maxReplicas: 50
```

## License

Copyright © 2026 SmartAP Team

## Support

- **Documentation:** https://docs.smartap.example.com
- **Issues:** https://github.com/yourusername/smartap/issues
- **Discussions:** https://github.com/yourusername/smartap/discussions
- **Email:** support@smartap.example.com
