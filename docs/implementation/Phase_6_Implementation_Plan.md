# Phase 6 Implementation Plan: Cloud Deployment

**Phase:** 6 (Phase 4.6)  
**Status:** Planning  
**Objective:** Enable production-ready cloud deployment with Kubernetes, Helm, Azure Container Apps, and CI/CD automation

---

## Overview

Phase 6 transforms SmartAP from a Docker Compose application into a **cloud-native, scalable** platform ready for enterprise deployment. This phase focuses on:

1. **Kubernetes Support**: Native k8s manifests for any Kubernetes cluster
2. **Helm Charts**: Parameterized deployments with one command
3. **Azure Container Apps**: Serverless container deployment on Azure
4. **CI/CD Pipeline**: Automated testing, building, and deployment
5. **Monitoring & Observability**: Prometheus, Grafana, Application Insights
6. **Auto-Scaling**: Horizontal Pod Autoscaler (HPA) and cloud auto-scaling
7. **Multi-Region**: Deploy across multiple regions for high availability

---

## Implementation Steps

### Step 1: Kubernetes Deployment Manifests
**Effort:** 2-3 days  
**Priority:** High

#### Tasks:
- [ ] Create namespace configuration (`namespace.yaml`)
- [ ] Create ConfigMap for environment variables (`configmap.yaml`)
- [ ] Create Secrets for sensitive data (`secrets.yaml`)
- [ ] Create PostgreSQL StatefulSet with persistent volume (`postgres.yaml`)
- [ ] Create Redis Deployment (`redis.yaml`)
- [ ] Create Backend API Deployment (`backend-deployment.yaml`)
- [ ] Create Frontend Deployment (`frontend-deployment.yaml`)
- [ ] Create Celery Worker Deployment (`worker-deployment.yaml`)
- [ ] Create Celery Beat Deployment (`scheduler-deployment.yaml`)
- [ ] Create Service manifests for all components (`services.yaml`)
- [ ] Create Ingress for external access (`ingress.yaml`)
- [ ] Create PersistentVolumeClaims for data storage (`pvcs.yaml`)

#### Deliverables:
```
k8s/
├── namespace.yaml
├── configmap.yaml
├── secrets.yaml
├── postgres-statefulset.yaml
├── redis-deployment.yaml
├── backend-deployment.yaml
├── frontend-deployment.yaml
├── worker-deployment.yaml
├── scheduler-deployment.yaml
├── services.yaml
├── ingress.yaml
├── pvcs.yaml
└── kustomization.yaml
```

#### Key Features:
- **Namespaces**: Isolate SmartAP resources
- **Resource Limits**: CPU/Memory limits for all pods
- **Health Checks**: Liveness and readiness probes
- **Rolling Updates**: Zero-downtime deployments
- **Persistent Storage**: StatefulSets for database
- **Load Balancing**: Services with ClusterIP/LoadBalancer

---

### Step 2: Helm Chart Creation
**Effort:** 3-4 days  
**Priority:** High

#### Tasks:
- [ ] Initialize Helm chart structure (`helm create smartap`)
- [ ] Create `Chart.yaml` with metadata
- [ ] Create `values.yaml` with default configuration
- [ ] Create `values-dev.yaml` for development environment
- [ ] Create `values-staging.yaml` for staging environment
- [ ] Create `values-prod.yaml` for production environment
- [ ] Convert k8s manifests to Helm templates
- [ ] Add conditionals for optional components (workers, nginx)
- [ ] Create helper templates (`_helpers.tpl`)
- [ ] Add NOTES.txt for post-install instructions
- [ ] Create hooks for database migrations (pre-install, pre-upgrade)
- [ ] Package Helm chart for distribution

#### Deliverables:
```
helm/
└── smartap/
    ├── Chart.yaml
    ├── values.yaml
    ├── values-dev.yaml
    ├── values-staging.yaml
    ├── values-prod.yaml
    ├── templates/
    │   ├── _helpers.tpl
    │   ├── configmap.yaml
    │   ├── secrets.yaml
    │   ├── postgres-statefulset.yaml
    │   ├── redis-deployment.yaml
    │   ├── backend-deployment.yaml
    │   ├── frontend-deployment.yaml
    │   ├── worker-deployment.yaml
    │   ├── scheduler-deployment.yaml
    │   ├── services.yaml
    │   ├── ingress.yaml
    │   ├── pvcs.yaml
    │   ├── hpa.yaml
    │   └── NOTES.txt
    └── charts/
```

#### Key Features:
- **Parameterization**: All values configurable via `values.yaml`
- **Environment Profiles**: Separate configs for dev/staging/prod
- **Dependencies**: PostgreSQL and Redis as sub-charts (optional)
- **Upgrade Hooks**: Database migrations before deployment
- **Validation**: Schema validation for values
- **Documentation**: Comprehensive NOTES.txt with next steps

#### Installation Command:
```bash
# Install with default values
helm install smartap ./helm/smartap

# Install with production values
helm install smartap ./helm/smartap -f helm/smartap/values-prod.yaml

# Upgrade existing installation
helm upgrade smartap ./helm/smartap
```

---

### Step 3: Azure Container Apps Deployment
**Effort:** 2-3 days  
**Priority:** High

#### Tasks:
- [ ] Create Azure Bicep template for Container Apps Environment
- [ ] Create Bicep module for PostgreSQL Flexible Server
- [ ] Create Bicep module for Redis Cache
- [ ] Create Bicep module for Backend Container App
- [ ] Create Bicep module for Frontend Container App
- [ ] Create Bicep module for Worker Container App
- [ ] Create Bicep module for Scheduler Container App
- [ ] Create Bicep module for Application Insights
- [ ] Create Bicep module for Key Vault (secrets management)
- [ ] Create Bicep module for Storage Account (file storage)
- [ ] Create Bicep module for Virtual Network (optional)
- [ ] Create main Bicep orchestration file
- [ ] Create Azure CLI deployment script
- [ ] Create Azure DevOps pipeline (alternative to GitHub Actions)

#### Deliverables:
```
azure/
├── bicep/
│   ├── main.bicep
│   ├── modules/
│   │   ├── container-apps-environment.bicep
│   │   ├── postgres.bicep
│   │   ├── redis.bicep
│   │   ├── backend-app.bicep
│   │   ├── frontend-app.bicep
│   │   ├── worker-app.bicep
│   │   ├── scheduler-app.bicep
│   │   ├── app-insights.bicep
│   │   ├── key-vault.bicep
│   │   ├── storage.bicep
│   │   └── vnet.bicep
│   └── parameters/
│       ├── parameters-dev.json
│       ├── parameters-staging.json
│       └── parameters-prod.json
├── scripts/
│   ├── deploy.sh
│   ├── deploy.ps1
│   └── destroy.sh
└── README.md
```

#### Key Features:
- **Serverless**: No infrastructure management
- **Auto-Scaling**: Scale to zero when idle
- **Managed Services**: Azure PostgreSQL, Redis, App Insights
- **Secrets Management**: Azure Key Vault integration
- **Networking**: Private endpoints for database (optional)
- **Cost-Effective**: Pay only for what you use

#### Deployment Command:
```bash
# Deploy to Azure
az deployment group create \
  --resource-group smartap-rg \
  --template-file azure/bicep/main.bicep \
  --parameters @azure/bicep/parameters/parameters-prod.json
```

---

### Step 4: GitHub Actions CI/CD Pipeline
**Effort:** 2-3 days  
**Priority:** High

#### Tasks:
- [ ] Create workflow for running tests (`test.yml`)
- [ ] Create workflow for building Docker images (`build.yml`)
- [ ] Create workflow for pushing to container registry (`publish.yml`)
- [ ] Create workflow for deploying to Kubernetes (`deploy-k8s.yml`)
- [ ] Create workflow for deploying to Azure Container Apps (`deploy-azure.yml`)
- [ ] Create workflow for Helm chart linting and testing (`helm-test.yml`)
- [ ] Create workflow for security scanning (Trivy, Snyk) (`security.yml`)
- [ ] Create workflow for dependency updates (Dependabot)
- [ ] Set up GitHub Environments (dev, staging, prod)
- [ ] Configure GitHub Secrets for credentials
- [ ] Add deployment approval gates for production
- [ ] Create reusable workflow templates

#### Deliverables:
```
.github/
├── workflows/
│   ├── ci.yml                    # Run tests on every push
│   ├── build.yml                 # Build Docker images
│   ├── publish.yml               # Push to ACR/Docker Hub
│   ├── deploy-k8s.yml            # Deploy to Kubernetes
│   ├── deploy-azure.yml          # Deploy to Azure Container Apps
│   ├── helm-lint.yml             # Lint Helm charts
│   ├── security-scan.yml         # Security vulnerability scanning
│   └── release.yml               # Create GitHub releases
├── actions/
│   ├── setup-python/
│   ├── setup-node/
│   └── setup-kubectl/
└── dependabot.yml
```

#### Pipeline Stages:

**1. CI Pipeline (Continuous Integration)**:
```yaml
Trigger: Every push/PR
├── Checkout code
├── Setup Python & Node.js
├── Install dependencies
├── Run linters (Black, ESLint, Prettier)
├── Run unit tests (pytest, Jest)
├── Run integration tests
├── Generate coverage reports
└── Upload coverage to Codecov
```

**2. Build Pipeline**:
```yaml
Trigger: Push to main, tags
├── Checkout code
├── Build backend Docker image
├── Build frontend Docker image
├── Build worker Docker image
├── Scan images for vulnerabilities (Trivy)
├── Tag images with version
└── Push to container registry (ACR/Docker Hub)
```

**3. Deploy Pipeline (Kubernetes)**:
```yaml
Trigger: Manual, or after build success
├── Checkout code
├── Setup kubectl
├── Login to Kubernetes cluster
├── Apply k8s manifests (or Helm install)
├── Wait for rollout completion
├── Run smoke tests
└── Send Slack notification
```

**4. Deploy Pipeline (Azure Container Apps)**:
```yaml
Trigger: Manual, or after build success
├── Checkout code
├── Azure Login
├── Deploy Bicep templates
├── Update container app revisions
├── Run smoke tests
└── Send email notification
```

#### Key Features:
- **Automated Testing**: Run tests on every commit
- **Multi-Environment**: Deploy to dev/staging/prod
- **Approval Gates**: Require manual approval for production
- **Rollback**: Easy rollback to previous versions
- **Notifications**: Slack/Email notifications on deployment
- **Security Scanning**: Vulnerability scanning with Trivy

---

### Step 5: Monitoring & Observability Setup
**Effort:** 2-3 days  
**Priority:** Medium

#### Tasks:
- [ ] Create Prometheus deployment and configuration
- [ ] Create Grafana deployment with dashboards
- [ ] Create ServiceMonitor for scraping metrics
- [ ] Create AlertManager for alerting rules
- [ ] Create custom Grafana dashboards for SmartAP
- [ ] Add Prometheus client to backend (metrics endpoint)
- [ ] Create Azure Application Insights configuration
- [ ] Add Application Insights SDK to backend
- [ ] Create custom metrics (invoice processing time, accuracy)
- [ ] Create alert rules (high error rate, slow response time)
- [ ] Create runbooks for common incidents
- [ ] Set up log aggregation (ELK Stack or Azure Log Analytics)

#### Deliverables:
```
monitoring/
├── prometheus/
│   ├── prometheus-deployment.yaml
│   ├── prometheus-config.yaml
│   ├── prometheus-service.yaml
│   └── servicemonitor.yaml
├── grafana/
│   ├── grafana-deployment.yaml
│   ├── grafana-service.yaml
│   ├── dashboards/
│   │   ├── smartap-overview.json
│   │   ├── invoice-processing.json
│   │   ├── agent-performance.json
│   │   └── system-health.json
│   └── datasources.yaml
├── alertmanager/
│   ├── alertmanager-deployment.yaml
│   ├── alertmanager-config.yaml
│   └── alert-rules.yaml
└── azure/
    ├── app-insights-config.json
    └── log-analytics-workspace.bicep
```

#### Key Metrics:
- **Application Metrics**:
  - Invoice processing rate (invoices/min)
  - Extraction accuracy (%)
  - Processing time per invoice (seconds)
  - Agent execution time (ms)
  - Error rate (%)
  - API response time (ms)

- **Infrastructure Metrics**:
  - CPU usage (%)
  - Memory usage (%)
  - Disk I/O (IOPS)
  - Network throughput (MB/s)
  - Pod restarts
  - Database connections

- **Business Metrics**:
  - Touchless processing rate (%)
  - Invoices pending approval
  - Average approval time (hours)
  - Fraud detection rate
  - Cost per invoice

#### Dashboards:
1. **SmartAP Overview**: High-level KPIs, processing volume, accuracy
2. **Invoice Processing**: Detailed invoice flow, extraction pipeline
3. **Agent Performance**: Per-agent metrics, execution times
4. **System Health**: Infrastructure health, resource usage
5. **Business Metrics**: Cost savings, touchless rate, ROI

#### Alerts:
- **Critical**: API down, database connection lost, disk full
- **Warning**: High error rate (>5%), slow response time (>2s)
- **Info**: Deployment completed, scaling event

---

### Step 6: Auto-Scaling Configuration
**Effort:** 1-2 days  
**Priority:** Medium

#### Tasks:
- [ ] Create Horizontal Pod Autoscaler (HPA) for backend
- [ ] Create HPA for frontend
- [ ] Create HPA for worker
- [ ] Configure metrics server for k8s cluster
- [ ] Create custom metrics for scaling (queue length)
- [ ] Configure Azure Container Apps auto-scaling rules
- [ ] Set up KEDA for event-driven scaling
- [ ] Create load testing scripts to validate scaling
- [ ] Document scaling behavior and thresholds

#### Deliverables:
```
k8s/
├── hpa/
│   ├── backend-hpa.yaml
│   ├── frontend-hpa.yaml
│   └── worker-hpa.yaml
├── keda/
│   ├── keda-scaledobject-backend.yaml
│   └── keda-scaledobject-worker.yaml
└── load-tests/
    ├── locustfile.py
    └── k6-script.js
```

#### Scaling Rules:

**Backend API**:
- **Min Replicas**: 2
- **Max Replicas**: 10
- **CPU Target**: 70%
- **Memory Target**: 80%
- **Scale-up**: Add pod when CPU > 70% for 2 minutes
- **Scale-down**: Remove pod when CPU < 50% for 5 minutes

**Frontend**:
- **Min Replicas**: 2
- **Max Replicas**: 5
- **CPU Target**: 60%

**Worker (Celery)**:
- **Min Replicas**: 1
- **Max Replicas**: 20
- **Queue Length Target**: 10 tasks per worker
- **KEDA**: Scale based on Redis queue length

**Azure Container Apps**:
- **HTTP Scaling**: 0-100 replicas based on HTTP requests
- **CPU Scaling**: 50-100% CPU threshold
- **Custom Metrics**: Queue length, processing rate

#### Load Testing:
```bash
# k6 load test
k6 run --vus 100 --duration 5m k8s/load-tests/k6-script.js

# Locust load test
locust -f k8s/load-tests/locustfile.py --host http://smartap.example.com
```

---

### Step 7: Multi-Region Deployment
**Effort:** 2-3 days  
**Priority:** Low (Optional)

#### Tasks:
- [ ] Design multi-region architecture
- [ ] Set up Azure Traffic Manager for global load balancing
- [ ] Configure PostgreSQL read replicas in multiple regions
- [ ] Set up Azure Cosmos DB (alternative to PostgreSQL)
- [ ] Configure Redis cluster with geo-replication
- [ ] Create deployment scripts for multi-region
- [ ] Set up cross-region failover
- [ ] Configure CDN for frontend assets
- [ ] Test disaster recovery procedures
- [ ] Document multi-region deployment

#### Architecture:
```
Global Load Balancer (Azure Traffic Manager)
├── Region 1 (East US)
│   ├── Container Apps
│   ├── PostgreSQL (Primary)
│   └── Redis Cache
├── Region 2 (West US)
│   ├── Container Apps
│   ├── PostgreSQL (Read Replica)
│   └── Redis Cache
└── Region 3 (Europe)
    ├── Container Apps
    ├── PostgreSQL (Read Replica)
    └── Redis Cache
```

---

### Step 8: Documentation Updates
**Effort:** 1-2 days  
**Priority:** High

#### Tasks:
- [ ] Create comprehensive deployment guide (`Deployment_Guide.md`)
- [ ] Update main README with cloud deployment sections
- [ ] Create Kubernetes quickstart guide
- [ ] Create Helm chart usage documentation
- [ ] Create Azure Container Apps deployment guide
- [ ] Create CI/CD pipeline documentation
- [ ] Create monitoring and observability guide
- [ ] Create troubleshooting guide for cloud deployments
- [ ] Create cost optimization guide
- [ ] Create Phase 6 implementation summary

#### Deliverables:
```
docs/
├── cloud-deployment/
│   ├── Kubernetes_Deployment.md
│   ├── Helm_Chart_Guide.md
│   ├── Azure_Container_Apps.md
│   ├── CI_CD_Pipeline.md
│   ├── Monitoring_Guide.md
│   ├── Auto_Scaling_Guide.md
│   ├── Multi_Region_Deployment.md
│   ├── Cost_Optimization.md
│   └── Troubleshooting_Cloud.md
└── Phase_6_Implementation_Summary.md
```

---

### Step 9: Testing & Validation
**Effort:** 2-3 days  
**Priority:** High

#### Tasks:
- [ ] Test Kubernetes deployment on local cluster (Minikube/Kind)
- [ ] Test Helm chart installation/upgrade/rollback
- [ ] Test Azure Container Apps deployment
- [ ] Validate CI/CD pipeline end-to-end
- [ ] Perform load testing and validate auto-scaling
- [ ] Test monitoring and alerting
- [ ] Test disaster recovery procedures
- [ ] Validate security configurations
- [ ] Perform cost analysis
- [ ] Create test reports

#### Test Scenarios:
1. **Deployment Tests**:
   - Fresh installation
   - Upgrade from previous version
   - Rollback to previous version
   - Configuration changes

2. **Scaling Tests**:
   - Scale up under load
   - Scale down when idle
   - Worker scaling based on queue length

3. **Resilience Tests**:
   - Pod failure recovery
   - Database connection loss
   - Redis cache failure
   - Network partition

4. **Performance Tests**:
   - API response time under load
   - Invoice processing throughput
   - Database query performance
   - Cache hit rate

5. **Security Tests**:
   - Secrets management
   - Network policies
   - RBAC validation
   - Vulnerability scanning

---

## Success Criteria

### Phase 6 is considered complete when:

- [ ] **Kubernetes Deployment**: Can deploy SmartAP to any k8s cluster with `kubectl apply`
- [ ] **Helm Chart**: Can install/upgrade SmartAP with `helm install smartap`
- [ ] **Azure Container Apps**: Can deploy to Azure with `az deployment group create`
- [ ] **CI/CD Pipeline**: Automated testing, building, and deployment working
- [ ] **Monitoring**: Grafana dashboards showing all key metrics
- [ ] **Auto-Scaling**: HPA scaling pods based on CPU/memory/queue length
- [ ] **Documentation**: Complete guides for all deployment methods
- [ ] **Load Testing**: System handles 100+ invoices/min with auto-scaling
- [ ] **Security**: All secrets in Key Vault, images scanned for vulnerabilities

---

## Timeline Estimate

| Step | Effort | Priority | Start | End |
|------|--------|----------|-------|-----|
| 1. Kubernetes Manifests | 2-3 days | High | Week 1 | Week 1 |
| 2. Helm Chart | 3-4 days | High | Week 1 | Week 2 |
| 3. Azure Container Apps | 2-3 days | High | Week 2 | Week 2 |
| 4. CI/CD Pipeline | 2-3 days | High | Week 2 | Week 3 |
| 5. Monitoring Setup | 2-3 days | Medium | Week 3 | Week 3 |
| 6. Auto-Scaling | 1-2 days | Medium | Week 3 | Week 3 |
| 7. Multi-Region | 2-3 days | Low | Week 4 | Week 4 |
| 8. Documentation | 1-2 days | High | Week 4 | Week 4 |
| 9. Testing & Validation | 2-3 days | High | Week 4 | Week 4 |

**Total Estimated Time**: 4 weeks (20 working days)

---

## Dependencies

### Tools Required:
- Docker & Docker Compose
- kubectl (Kubernetes CLI)
- Helm 3+
- Azure CLI
- GitHub account (for Actions)
- Azure subscription (for Container Apps)
- Kubernetes cluster (local: Minikube/Kind, cloud: AKS/EKS/GKE)

### Skills Required:
- Kubernetes fundamentals
- Helm chart development
- Azure services (Container Apps, PostgreSQL, Redis)
- CI/CD with GitHub Actions
- Monitoring (Prometheus, Grafana)
- Bicep/ARM templates

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Kubernetes complexity** | High | Start with simple manifests, add complexity gradually |
| **Azure costs** | Medium | Use cost budgets, auto-scale down when idle |
| **Database migration** | High | Test migrations extensively, have rollback plan |
| **CI/CD failures** | Medium | Add retry logic, manual approval gates |
| **Performance issues** | High | Load test early, optimize bottlenecks |
| **Security vulnerabilities** | High | Regular scanning, dependency updates |

---

## Cost Estimation (Azure)

### Monthly Cost (Production):

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| **Container Apps** | 4 apps × 1 vCPU × 2GB RAM | ~$100 |
| **PostgreSQL Flexible Server** | General Purpose, 2 vCores | ~$150 |
| **Redis Cache** | Standard C1 (1GB) | ~$75 |
| **Application Insights** | 5GB data/month | ~$25 |
| **Storage Account** | 100GB Blob + 10K transactions | ~$10 |
| **Key Vault** | Standard tier | ~$1 |
| **Virtual Network** | Standard tier (optional) | ~$5 |
| **Traffic Manager** | Multi-region (optional) | ~$10 |

**Total Estimated Cost**: ~$376/month (single region, production)

### Cost Optimization Tips:
- Use Azure Reserved Instances for PostgreSQL (save up to 60%)
- Enable auto-scale down to 0 for non-production environments
- Use Azure Cost Management + Billing alerts
- Consider Azure Dev/Test pricing for staging

---

## Next Steps After Phase 6

### Phase 7: Advanced Analytics
- ML-powered spend analysis
- Predictive analytics (AP aging forecast)
- Vendor performance dashboards
- Custom report builder

### Phase 8: Mobile App
- iOS/Android native apps
- Push notifications for approvals
- Camera-based invoice capture
- Offline mode

### Phase 9: Agent Marketplace
- Community agent repository
- One-click agent installation
- Agent ratings and reviews
- Agent monetization (premium agents)

### Phase 10: Enterprise Features
- Multi-tenancy
- Advanced RBAC
- SSO/SAML
- SLA monitoring
- White-labeling

---

## References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [Azure Container Apps Documentation](https://learn.microsoft.com/en-us/azure/container-apps/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [KEDA Documentation](https://keda.sh/docs/)

---

**Document Version**: 1.0  
**Last Updated**: January 8, 2026  
**Status**: Ready for Implementation
