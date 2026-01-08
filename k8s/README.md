# Kubernetes Deployment for SmartAP

This directory contains Kubernetes manifests for deploying SmartAP to any Kubernetes cluster.

## Prerequisites

- Kubernetes cluster (1.24+)
- kubectl CLI installed and configured
- Container registry (Docker Hub, Azure Container Registry, etc.)
- Ingress controller (nginx-ingress, traefik, etc.)
- Persistent volume provisioner (for storage)

## Quick Start

### 1. Build and Push Docker Images

```bash
# Build backend image
cd backend
docker build -t your-registry/smartap/backend:latest .
docker push your-registry/smartap/backend:latest

# Build frontend image
cd ../frontend
docker build -t your-registry/smartap/frontend:latest .
docker push your-registry/smartap/frontend:latest
```

### 2. Update Image References

Edit `kustomization.yaml` to point to your container registry:

```yaml
images:
  - name: smartap/backend
    newName: your-registry.azurecr.io/smartap/backend
    newTag: latest
  - name: smartap/frontend
    newName: your-registry.azurecr.io/smartap/frontend
    newTag: latest
```

### 3. Configure Secrets

**⚠️ IMPORTANT**: Never commit real secrets to version control!

Create secrets from command line:

```bash
kubectl create secret generic smartap-secrets \
  --from-literal=DB_PASSWORD='your_secure_password' \
  --from-literal=SECRET_KEY='your_secret_key' \
  --from-literal=GITHUB_TOKEN='your_github_token' \
  --namespace=smartap
```

Or use a secrets management solution like:
- Azure Key Vault
- AWS Secrets Manager
- HashiCorp Vault
- Sealed Secrets

### 4. Deploy to Kubernetes

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Apply all manifests
kubectl apply -f .

# Or use kustomize
kubectl apply -k .
```

### 5. Verify Deployment

```bash
# Check all resources
kubectl get all -n smartap

# Check pod status
kubectl get pods -n smartap

# Check services
kubectl get svc -n smartap

# Check ingress
kubectl get ingress -n smartap

# View logs
kubectl logs -n smartap deployment/backend
kubectl logs -n smartap deployment/frontend
kubectl logs -n smartap deployment/worker
```

### 6. Access the Application

```bash
# Get ingress IP/hostname
kubectl get ingress -n smartap

# If using LoadBalancer service
kubectl get svc frontend-service -n smartap

# Port-forward for local testing
kubectl port-forward -n smartap svc/frontend-service 3000:80
kubectl port-forward -n smartap svc/backend-service 8000:8000
```

Access at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Architecture

```
┌────────────────────────────────────────────────┐
│              Ingress Controller                │
│         (smartap.example.com)                  │
└───────────────┬────────────────────────────────┘
                │
        ┌───────┴────────┐
        │                │
        ▼                ▼
  ┌─────────┐      ┌──────────┐
  │Frontend │      │ Backend  │
  │ Service │      │ Service  │
  │ (80)    │      │ (8000)   │
  └────┬────┘      └─────┬────┘
       │                 │
       ▼                 ▼
  ┌─────────┐      ┌──────────┐
  │Frontend │      │ Backend  │
  │  Pods   │      │  Pods    │
  │ (x2)    │      │ (x2)     │
  └─────────┘      └─────┬────┘
                          │
                    ┌─────┴─────┐
                    │           │
                    ▼           ▼
              ┌──────────┐ ┌──────────┐
              │ Worker   │ │Scheduler │
              │  Pods    │ │  Pod     │
              │ (x2)     │ │ (x1)     │
              └─────┬────┘ └─────┬────┘
                    │            │
            ┌───────┴────────────┴────┐
            │                         │
            ▼                         ▼
      ┌──────────┐              ┌─────────┐
      │PostgreSQL│              │  Redis  │
      │StatefulSet              │ Deploy  │
      │  (x1)    │              │ (x1)    │
      └────┬─────┘              └────┬────┘
           │                         │
           ▼                         ▼
      ┌──────────┐              ┌─────────┐
      │   PVC    │              │   PVC   │
      │  (10Gi)  │              │  (5Gi)  │
      └──────────┘              └─────────┘
```

## Resources Overview

| Resource | Type | Replicas | Purpose |
|----------|------|----------|---------|
| postgres | StatefulSet | 1 | Invoice database |
| redis | Deployment | 1 | Cache & queue |
| backend | Deployment | 2 | FastAPI REST API |
| frontend | Deployment | 2 | React web UI |
| worker | Deployment | 2 | Celery background tasks |
| scheduler | Deployment | 1 | Celery beat scheduler |

## Storage Requirements

| PVC | Size | Access Mode | Purpose |
|-----|------|-------------|---------|
| postgres-storage | 10Gi | ReadWriteOnce | Database files |
| redis-pvc | 5Gi | ReadWriteOnce | Redis persistence |
| uploads-pvc | 50Gi | ReadWriteMany | Uploaded invoices |
| processed-pvc | 50Gi | ReadWriteMany | Processed files |
| archival-pvc | 100Gi | ReadWriteMany | Long-term storage |
| signed-pvc | 20Gi | ReadWriteMany | Signed documents |

**Note**: For `ReadWriteMany` access mode, you need a storage class that supports it (e.g., Azure Files, NFS, CephFS).

## Configuration

### ConfigMap (`configmap.yaml`)

Contains non-sensitive configuration:
- Database connection settings
- Redis settings
- Application configuration
- Feature flags

### Secrets (`secrets.yaml`)

Contains sensitive data:
- Database password
- API keys (GitHub, Foxit, ERP)
- SMTP credentials
- JWT secret key

**⚠️ Security Best Practice**: Use external secrets management in production.

### Resource Limits

Default resource requests/limits per pod:

**Backend**:
- Request: 500m CPU, 512Mi memory
- Limit: 2 CPU, 2Gi memory

**Frontend**:
- Request: 100m CPU, 128Mi memory
- Limit: 500m CPU, 512Mi memory

**Worker**:
- Request: 500m CPU, 512Mi memory
- Limit: 2 CPU, 2Gi memory

**Database**:
- Request: 250m CPU, 256Mi memory
- Limit: 1 CPU, 1Gi memory

**Redis**:
- Request: 100m CPU, 128Mi memory
- Limit: 500m CPU, 512Mi memory

### Ingress Configuration

The ingress is configured for:
- SSL/TLS termination
- Rate limiting (100 req/s)
- CORS support
- Request body size: 10MB
- Timeouts: 60s

Update `ingress.yaml` with your domain:

```yaml
spec:
  rules:
  - host: smartap.example.com  # Replace with your domain
```

For HTTPS, uncomment TLS section and configure cert-manager:

```yaml
tls:
- hosts:
  - smartap.example.com
  secretName: smartap-tls-secret
```

## Scaling

### Manual Scaling

```bash
# Scale backend pods
kubectl scale deployment backend -n smartap --replicas=5

# Scale worker pods
kubectl scale deployment worker -n smartap --replicas=10

# Scale frontend pods
kubectl scale deployment frontend -n smartap --replicas=3
```

### Auto-Scaling

See `hpa.yaml` for Horizontal Pod Autoscaler configuration.

## Monitoring

### Check Pod Logs

```bash
# Backend logs
kubectl logs -n smartap -l app=backend -f

# Worker logs
kubectl logs -n smartap -l app=worker -f

# All pods logs
kubectl logs -n smartap -l app.kubernetes.io/name=smartap -f --max-log-requests=10
```

### Check Resource Usage

```bash
# Pod resource usage
kubectl top pods -n smartap

# Node resource usage
kubectl top nodes
```

### Exec into Pod

```bash
# Exec into backend pod
kubectl exec -it -n smartap deployment/backend -- /bin/bash

# Exec into database pod
kubectl exec -it -n smartap statefulset/postgres -- psql -U smartap -d smartap
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod events
kubectl describe pod -n smartap <pod-name>

# Check pod logs
kubectl logs -n smartap <pod-name>

# Check if images are accessible
kubectl get events -n smartap --sort-by='.lastTimestamp'
```

### Database Connection Issues

```bash
# Check if PostgreSQL is running
kubectl get pods -n smartap -l app=postgres

# Test database connection
kubectl exec -it -n smartap statefulset/postgres -- psql -U smartap -d smartap -c "SELECT 1"

# Check database logs
kubectl logs -n smartap statefulset/postgres
```

### Storage Issues

```bash
# Check PVCs
kubectl get pvc -n smartap

# Check PVs
kubectl get pv

# Describe PVC for events
kubectl describe pvc -n smartap uploads-pvc
```

### Ingress Not Working

```bash
# Check ingress status
kubectl get ingress -n smartap

# Check ingress controller logs
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller

# Test service directly
kubectl port-forward -n smartap svc/frontend-service 8080:80
```

## Updating Deployment

### Rolling Update

```bash
# Update backend image
kubectl set image deployment/backend backend=your-registry/smartap/backend:v2.0.0 -n smartap

# Update frontend image
kubectl set image deployment/frontend frontend=your-registry/smartap/frontend:v2.0.0 -n smartap

# Check rollout status
kubectl rollout status deployment/backend -n smartap
```

### Rollback

```bash
# Rollback to previous version
kubectl rollout undo deployment/backend -n smartap

# Rollback to specific revision
kubectl rollout undo deployment/backend --to-revision=2 -n smartap

# Check rollout history
kubectl rollout history deployment/backend -n smartap
```

## Cleanup

```bash
# Delete all resources in namespace
kubectl delete namespace smartap

# Or delete specific resources
kubectl delete -f .

# Or use kustomize
kubectl delete -k .
```

## Production Checklist

Before deploying to production:

- [ ] Configure proper secrets management (Key Vault, Sealed Secrets)
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure resource limits appropriately
- [ ] Set up monitoring (Prometheus, Grafana)
- [ ] Configure backup for PostgreSQL
- [ ] Set up log aggregation (ELK, Azure Log Analytics)
- [ ] Enable network policies for security
- [ ] Configure RBAC for access control
- [ ] Set up disaster recovery plan
- [ ] Configure auto-scaling (HPA)
- [ ] Test rollback procedures
- [ ] Document runbooks for incidents
- [ ] Set up alerting (PagerDuty, OpsGenie)
- [ ] Perform load testing
- [ ] Security scan container images
- [ ] Review and harden ingress configuration

## Support

- Documentation: https://docs.smartap.dev
- GitHub Issues: https://github.com/your-org/SmartAP/issues
- Discord: https://discord.gg/smartap
- Email: support@smartap.dev
