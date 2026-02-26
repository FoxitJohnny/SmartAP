# Kubernetes Deployment Guide

This guide covers deploying SmartAP on Kubernetes using Helm charts.

## Prerequisites

- Kubernetes 1.28+
- Helm 3.12+
- kubectl configured for your cluster
- Ingress controller (nginx-ingress recommended)
- cert-manager (for TLS)
- PersistentVolume provisioner

## Quick Start

### Install with Helm

```bash
# Add SmartAP Helm repository
helm repo add smartap https://your-org.github.io/smartap-charts
helm repo update

# Install SmartAP
helm install smartap smartap/smartap \
  --namespace smartap \
  --create-namespace \
  --set api.githubToken=your_github_token \
  --set api.jwtSecretKey=$(openssl rand -hex 32)

# Check status
kubectl get pods -n smartap
```

### Install from Local Charts

```bash
cd smartap/helm

# Install with custom values
helm install smartap ./smartap \
  --namespace smartap \
  --create-namespace \
  -f values-production.yaml
```

---

## Helm Chart Structure

```
helm/
└── smartap/
    ├── Chart.yaml
    ├── values.yaml
    ├── values-production.yaml
    ├── templates/
    │   ├── _helpers.tpl
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   ├── ingress.yaml
    │   ├── configmap.yaml
    │   ├── secret.yaml
    │   ├── hpa.yaml
    │   ├── pdb.yaml
    │   └── serviceaccount.yaml
    └── charts/
        ├── postgresql/
        └── redis/
```

---

## Configuration

### values.yaml Overview

```yaml
# API Configuration
api:
  replicaCount: 3
  image:
    repository: ghcr.io/your-org/smartap
    tag: "3.0.0"
    pullPolicy: IfNotPresent
  
  resources:
    limits:
      cpu: 2000m
      memory: 4Gi
    requests:
      cpu: 500m
      memory: 1Gi

  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilization: 70

  # Environment variables
  githubToken: ""
  jwtSecretKey: ""
  logLevel: "INFO"

# Database Configuration
postgresql:
  enabled: true
  auth:
    postgresPassword: ""
    database: smartap
  primary:
    persistence:
      size: 50Gi

# Cache Configuration
redis:
  enabled: true
  architecture: standalone
  auth:
    enabled: false
  master:
    persistence:
      size: 8Gi

# Ingress Configuration
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
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

### Production Values

Create `values-production.yaml`:

```yaml
api:
  replicaCount: 5
  
  resources:
    limits:
      cpu: 4000m
      memory: 8Gi
    requests:
      cpu: 1000m
      memory: 2Gi

  autoscaling:
    enabled: true
    minReplicas: 5
    maxReplicas: 20
    targetCPUUtilization: 60

postgresql:
  primary:
    persistence:
      size: 100Gi
    resources:
      limits:
        cpu: 4000m
        memory: 16Gi

redis:
  master:
    persistence:
      size: 16Gi
    resources:
      limits:
        cpu: 2000m
        memory: 4Gi
```

---

## Secrets Management

### Using Kubernetes Secrets

```bash
# Create secrets
kubectl create secret generic smartap-secrets \
  --namespace smartap \
  --from-literal=github-token=your_token \
  --from-literal=jwt-secret-key=$(openssl rand -hex 32) \
  --from-literal=db-password=$(openssl rand -hex 16)
```

Reference in values.yaml:
```yaml
api:
  existingSecret: smartap-secrets
  secretKeys:
    githubToken: github-token
    jwtSecretKey: jwt-secret-key
```

### Using External Secrets Operator

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: smartap-secrets
  namespace: smartap
spec:
  refreshInterval: 1h
  secretStoreRef:
    kind: ClusterSecretStore
    name: vault-backend
  target:
    name: smartap-secrets
  data:
    - secretKey: github-token
      remoteRef:
        key: smartap/github-token
    - secretKey: jwt-secret-key
      remoteRef:
        key: smartap/jwt-secret
```

---

## High Availability

### Pod Disruption Budget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: smartap-api-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: smartap-api
```

### Anti-Affinity Rules

```yaml
api:
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            labelSelector:
              matchLabels:
                app: smartap-api
            topologyKey: kubernetes.io/hostname
```

### Multi-Zone Deployment

```yaml
api:
  topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
      labelSelector:
        matchLabels:
          app: smartap-api
```

---

## Monitoring

### Prometheus Integration

```yaml
api:
  serviceMonitor:
    enabled: true
    interval: 30s
    path: /metrics

  podAnnotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8000"
    prometheus.io/path: "/metrics"
```

### Grafana Dashboard

Import the SmartAP dashboard:
```bash
kubectl apply -f https://raw.githubusercontent.com/your-org/smartap/main/k8s/grafana-dashboard.yaml
```

### Alerting Rules

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: smartap-alerts
spec:
  groups:
    - name: smartap
      rules:
        - alert: SmartAPHighErrorRate
          expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: High error rate detected
```

---

## Ingress Configuration

### NGINX Ingress

```yaml
ingress:
  enabled: true
  className: nginx
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
```

### TLS with cert-manager

```yaml
ingress:
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  tls:
    - secretName: smartap-tls
      hosts:
        - smartap.example.com
```

---

## Database Operations

### Backup with CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: postgres:16
              command:
                - /bin/sh
                - -c
                - pg_dump -h $PGHOST -U $PGUSER -d smartap | gzip > /backup/smartap-$(date +%Y%m%d).sql.gz
              envFrom:
                - secretRef:
                    name: postgres-credentials
              volumeMounts:
                - name: backup
                  mountPath: /backup
          volumes:
            - name: backup
              persistentVolumeClaim:
                claimName: backup-pvc
          restartPolicy: OnFailure
```

### Database Migration

```bash
# Run migrations
kubectl exec -it deploy/smartap-api -n smartap -- alembic upgrade head

# Check migration status
kubectl exec -it deploy/smartap-api -n smartap -- alembic current
```

---

## Scaling

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: smartap-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: smartap-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

### Vertical Pod Autoscaler

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: smartap-api-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: smartap-api
  updatePolicy:
    updateMode: "Auto"
```

---

## Troubleshooting

### Common Issues

**Pods not starting:**
```bash
kubectl describe pod -n smartap -l app=smartap-api
kubectl logs -n smartap -l app=smartap-api --previous
```

**Database connection issues:**
```bash
kubectl exec -it deploy/smartap-api -n smartap -- \
  python -c "from src.db.database import engine; print(engine.url)"
```

**Ingress not working:**
```bash
kubectl describe ingress -n smartap
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller
```

### Debug Commands

```bash
# Get all resources
kubectl get all -n smartap

# Check events
kubectl get events -n smartap --sort-by='.lastTimestamp'

# Port forward for local debugging
kubectl port-forward svc/smartap-api 8000:8000 -n smartap

# Shell into pod
kubectl exec -it deploy/smartap-api -n smartap -- /bin/bash
```

---

## Upgrade Process

### Helm Upgrade

```bash
# Check current version
helm list -n smartap

# Upgrade to new version
helm upgrade smartap smartap/smartap \
  --namespace smartap \
  -f values-production.yaml \
  --set api.image.tag=3.1.0

# Rollback if needed
helm rollback smartap 1 -n smartap
```

### Zero-Downtime Deployment

Ensure proper configuration:
```yaml
api:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 0
  
  readinessProbe:
    httpGet:
      path: /api/v1/health
      port: 8000
    initialDelaySeconds: 10
    periodSeconds: 5
  
  livenessProbe:
    httpGet:
      path: /api/v1/health
      port: 8000
    initialDelaySeconds: 30
    periodSeconds: 10
```

---

## Uninstall

```bash
# Uninstall release
helm uninstall smartap -n smartap

# Delete namespace (removes all resources)
kubectl delete namespace smartap

# Delete persistent volumes (WARNING: data loss)
kubectl delete pvc -n smartap --all
```
