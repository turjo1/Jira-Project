# Kubernetes Deployment Checklist

Use this checklist to ensure all deployment steps are completed before going to production.

## Pre-Deployment

### Infrastructure Setup
- [ ] Kubernetes cluster created (1.24+)
  - [ ] Cluster has at least 4 CPU cores, 8GB RAM (development)
  - [ ] Production cluster has 16+ CPU, 32GB+ RAM
- [ ] kubectl installed and configured
- [ ] Admin access to cluster verified
- [ ] Persistent storage configured (PVs, storage classes)

### Certificate Management
- [ ] cert-manager installed (v1.13+)
- [ ] ClusterIssuer created for Let's Encrypt
- [ ] Email configured for cert-manager

### Ingress Controller
- [ ] nginx-ingress controller installed
- [ ] LoadBalancer service ready with external IP
- [ ] DNS domain registered

### Container Registry
- [ ] Docker registry account created
- [ ] Credentials configured in cluster (if private)
- [ ] Image push permissions verified

### Backend Build & Test
- [ ] Backend tests passing: `pytest tests/ --cov=app --cov-fail-under=80`
- [ ] Backend image built: `docker build -t jira-analytics-backend:latest backend/`
- [ ] Backend image pushed to registry
- [ ] Database migrations created: `alembic revision --autogenerate -m "..."`
- [ ] Migration files reviewed

### Frontend Build & Test
- [ ] Frontend tests passing: `npm run test:run`
- [ ] Frontend linting passing: `npm run lint`
- [ ] Frontend type checks passing: `npm run typecheck`
- [ ] Frontend image built: `docker build --target runtime -t jira-analytics-frontend:latest frontend/`
- [ ] Frontend image pushed to registry

## Deployment Steps

### Phase 1: Namespace & RBAC
- [ ] Read `01-namespace.yaml` and update resource quotas if needed
- [ ] Read `02-rbac.yaml` and review permissions
- [ ] Apply: `kubectl apply -f 01-namespace.yaml`
- [ ] Apply: `kubectl apply -f 02-rbac.yaml`
- [ ] Verify ServiceAccount created: `kubectl -n jira-analytics get sa`

### Phase 2: Secrets Management
- [ ] Generate JWT secret: `openssl rand -hex 32`
- [ ] Create JWT secret: `kubectl -n jira-analytics create secret generic jwt-secret --from-literal=key=...`
- [ ] Generate MySQL passwords: `openssl rand -hex 16` (2 passwords)
- [ ] Create MySQL secrets: `kubectl -n jira-analytics create secret generic mysql-credentials --from-literal=...`
- [ ] Obtain Jira OAuth credentials from OAuth app
- [ ] Create Jira secrets: `kubectl -n jira-analytics create secret generic jira-oauth-credentials --from-literal=...`
- [ ] Generate database connection string
- [ ] Create database credentials secret
- [ ] Verify all secrets: `kubectl -n jira-analytics get secrets`

### Phase 3: Configuration
- [ ] Edit `03-configmap.yaml` with your domain and settings
  - [ ] Update `CORS_ORIGINS`
  - [ ] Update `API_BASE_URL`
  - [ ] Update `JIRA_API_URL`
  - [ ] Set appropriate log levels
- [ ] Apply: `kubectl apply -f 03-configmap.yaml`
- [ ] Verify ConfigMaps: `kubectl -n jira-analytics get configmap`

### Phase 4: Data Layer
- [ ] Read `05-mysql-statefulset.yaml` and review configuration
  - [ ] Check storage class matches your cluster
  - [ ] Adjust storage size if needed (default 20Gi)
  - [ ] Review resource limits
- [ ] Apply: `kubectl apply -f 05-mysql-statefulset.yaml`
- [ ] Monitor MySQL startup: `kubectl -n jira-analytics logs -f statefulset/mysql`
- [ ] Verify MySQL is ready: `kubectl -n jira-analytics get pods mysql-0`
  - [ ] Wait for "Running" status and "1/1" ready replicas

- [ ] Read `06-redis-statefulset.yaml` and review configuration
  - [ ] Check storage class (default: standard)
  - [ ] Adjust storage size if needed (default 5Gi)
  - [ ] Review Redis configuration
- [ ] Apply: `kubectl apply -f 06-redis-statefulset.yaml`
- [ ] Monitor Redis startup: `kubectl -n jira-analytics logs -f statefulset/redis`
- [ ] Verify Redis is ready: `kubectl -n jira-analytics get pods redis-0`

### Phase 5: Backend Deployment
- [ ] Edit `07-fastapi-deployment.yaml`
  - [ ] Replace `docker.io/YOUR_DOCKER_USERNAME/` with actual username
  - [ ] Update image tag if not using `:latest`
  - [ ] Review replica count (default 3)
  - [ ] Review resource requests/limits
- [ ] Apply: `kubectl apply -f 07-fastapi-deployment.yaml`
- [ ] Monitor backend startup:
  ```bash
  kubectl -n jira-analytics logs -f deployment/fastapi
  ```
- [ ] Verify backend is healthy:
  ```bash
  kubectl -n jira-analytics exec deployment/fastapi -- curl localhost:8000/health
  ```

### Phase 6: Celery Workers
- [ ] Edit `08-celery-worker-deployment.yaml`
  - [ ] Replace Docker username
  - [ ] Review replica count (default 2)
  - [ ] Review resource limits
- [ ] Apply: `kubectl apply -f 08-celery-worker-deployment.yaml`
- [ ] Monitor worker startup: `kubectl -n jira-analytics logs -f deployment/celery-worker`
- [ ] Verify worker connects to Redis:
  ```bash
  kubectl -n jira-analytics exec deployment/celery-worker -- \
    celery -A app.tasks inspect active
  ```

### Phase 7: Celery Beat Scheduler
- [ ] Edit `09-celery-beat-deployment.yaml`
  - [ ] Replace Docker username
  - [ ] **VERIFY replicas: 1** (critical for scheduler)
  - [ ] Review resource limits
- [ ] Apply: `kubectl apply -f 09-celery-beat-deployment.yaml`
- [ ] Monitor Beat startup: `kubectl -n jira-analytics logs -f deployment/celery-beat`
- [ ] Verify Beat is scheduling:
  ```bash
  kubectl -n jira-analytics exec deployment/celery-beat -- \
    celery -A app.tasks inspect scheduled
  ```

### Phase 8: Frontend Deployment
- [ ] Edit `10-frontend-deployment.yaml`
  - [ ] Replace Docker username
  - [ ] Review replica count (default 2)
  - [ ] Review resource limits
- [ ] Apply: `kubectl apply -f 10-frontend-deployment.yaml`
- [ ] Monitor frontend startup: `kubectl -n jira-analytics logs -f deployment/frontend`
- [ ] Verify frontend is healthy:
  ```bash
  kubectl -n jira-analytics exec deployment/frontend -- \
    wget -qO- http://localhost:8080/index.html | head -20
  ```

### Phase 9: Ingress & TLS
- [ ] Ensure cert-manager is running: `kubectl get all -n cert-manager`
- [ ] Edit `11-ingress.yaml`
  - [ ] Replace all `jira-analytics.example.com` with your domain
  - [ ] Update cert-manager ClusterIssuer if needed
  - [ ] Update basic auth credentials for metrics endpoint
- [ ] Apply: `kubectl apply -f 11-ingress.yaml`
- [ ] Monitor Ingress creation:
  ```bash
  kubectl -n jira-analytics get ingress -w
  ```
- [ ] Wait for certificate to be issued:
  ```bash
  kubectl -n jira-analytics describe certificate jira-analytics-cert
  ```
- [ ] Get Ingress IP:
  ```bash
  kubectl -n jira-analytics get ingress jira-analytics-ingress
  ```

### Phase 10: DNS Configuration
- [ ] Get the Ingress LoadBalancer IP from output above
- [ ] Update DNS records to point to Ingress IP:
  - [ ] `jira-analytics.example.com A <INGRESS_IP>`
  - [ ] `*.jira-analytics.example.com CNAME jira-analytics.example.com` (optional)
- [ ] Test DNS resolution:
  ```bash
  nslookup jira-analytics.example.com
  ```
- [ ] Wait for DNS propagation (5-60 minutes)

## Post-Deployment Verification

### Service Accessibility
- [ ] Frontend loads: `https://jira-analytics.example.com`
- [ ] API health endpoint: `curl https://jira-analytics.example.com/health`
- [ ] Frontend health check: `curl https://jira-analytics.example.com/healthz`

### Pod Status
- [ ] All pods running: `kubectl -n jira-analytics get pods`
  - [ ] fastapi (3 running)
  - [ ] celery-worker (2 running)
  - [ ] celery-beat (1 running)
  - [ ] frontend (2 running)
  - [ ] mysql-0 (1 running)
  - [ ] redis-0 (1 running)
- [ ] No pods in CrashLoopBackOff
- [ ] All containers ready (1/1 or 2/2)

### Resource Usage
- [ ] Check CPU/memory: `kubectl -n jira-analytics top pods`
- [ ] Pod logs clean (no errors): `kubectl -n jira-analytics logs <POD>`
- [ ] No pending PVCs: `kubectl -n jira-analytics get pvc`

### Feature Testing
- [ ] Can log in with Jira OAuth
- [ ] Dashboard metrics loading
- [ ] WebSocket connection established
- [ ] Real-time updates working (test with manual Jira update)
- [ ] Celery jobs running (check logs)

### Health Checks
- [ ] Liveness probes passing
- [ ] Readiness probes passing
- [ ] No evictions due to resource pressure

### Monitoring Setup (Optional)
- [ ] Prometheus scraping metrics: `/metrics` endpoint
- [ ] Grafana dashboards configured
- [ ] Log aggregation working (ELK, etc.)
- [ ] Alerts configured for critical paths

## Production Hardening

### Security
- [ ] RBAC reviewed for least privilege
- [ ] Network policies configured (if needed)
- [ ] Pod security standards/policies enforced
- [ ] Secrets stored in external key manager (Vault, AWS Secrets Manager)
- [ ] Image scanning performed (no critical vulnerabilities)
- [ ] Container registry is private with authentication
- [ ] Rate limiting configured on Ingress

### High Availability
- [ ] All Deployments have ≥2 replicas
- [ ] PodDisruptionBudgets configured
- [ ] HPA tested and tuned
- [ ] Database backup strategy implemented
- [ ] Backup tested (restore from backup verified)
- [ ] Disaster recovery plan documented

### Scaling
- [ ] HPA metrics baseline: `kubectl -n jira-analytics get hpa`
- [ ] Load test completed
- [ ] Scale-up scenario tested
- [ ] Scale-down scenario tested
- [ ] Max replicas appropriate for cluster capacity

### Observability
- [ ] All components logging properly
- [ ] Log retention configured
- [ ] Metrics collection validated
- [ ] Alert thresholds set appropriately
- [ ] Health check endpoints responding

## Go-Live Checklist

- [ ] All verification steps passed
- [ ] Performance baseline established
- [ ] Runbooks created for common issues
- [ ] On-call schedule established
- [ ] Incident response plan documented
- [ ] User documentation complete
- [ ] Support team trained
- [ ] Rollback procedure documented and tested
- [ ] Change log recorded
- [ ] Stakeholders notified

## Rollback Plan

If issues occur post-deployment:

1. **Quick Rollback (if image issue)**:
   ```bash
   kubectl -n jira-analytics set image deployment/fastapi \
     fastapi=<PREVIOUS_IMAGE> --record
   ```

2. **Database Rollback**:
   ```bash
   # Restore from backup
   kubectl -n jira-analytics exec -i mysql-0 -- mysql \
     -u root -p$MYSQL_ROOT_PASSWORD < backup.sql
   ```

3. **Full Rollback**:
   ```bash
   # Delete namespace and redeploy from previous version
   kubectl delete namespace jira-analytics
   # Rerun deployment steps with previous image tags
   ```

## Support Contact

For issues, refer to:
- `kubernetes/README.md` - Deployment guide
- `../ARCHITECTURE.md` - System architecture
- `../CLAUDE.md` - Project context
- GitHub Issues for bug reports
