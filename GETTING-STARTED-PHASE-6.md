# Phase 6 - Getting Started Guide

**Phase:** Infrastructure - CI/CD Pipeline + Kubernetes Deployment  
**Status:** COMPLETE  
**Time to read:** 5 minutes

## What's New

Phase 6 adds **production deployment infrastructure** to the Jira Team Performance Analytics platform. All CI/CD automation and Kubernetes manifests are ready to use.

## Files Created

### GitHub Actions CI/CD Pipeline
```
.github/workflows/ci.yml (314 lines)
```
- Runs on every PR and push to main
- Tests backend (pytest), frontend (vitest)
- Builds Docker images
- Uploads test coverage to Codecov
- Runs E2E tests on PRs only

### Kubernetes Manifests
```
kubernetes/
├── 01-namespace.yaml              (42 lines)   - Namespace & resource quotas
├── 02-rbac.yaml                   (78 lines)   - RBAC & permissions
├── 03-configmap.yaml              (159 lines)  - Configuration
├── 04-secrets.yaml.example        (68 lines)   - Secrets template
├── 04b-database-credentials.yaml  (17 lines)   - Database connection
├── 05-mysql-statefulset.yaml      (130 lines)  - MySQL 8.0
├── 06-redis-statefulset.yaml      (125 lines)  - Redis 7
├── 07-fastapi-deployment.yaml     (245 lines)  - FastAPI + HPA
├── 08-celery-worker-deployment.yaml (151 lines) - Celery workers
├── 09-celery-beat-deployment.yaml   (151 lines) - Celery scheduler
├── 10-frontend-deployment.yaml      (175 lines) - React frontend
├── 11-ingress.yaml                  (165 lines) - Ingress + TLS
├── README.md                        (450 lines) - Deployment guide
├── DEPLOYMENT-CHECKLIST.md          (400 lines) - Step-by-step checklist
├── validate-manifests.sh            (script)    - Validation script
└── (15 files, ~2,700 lines total)
```

### Documentation
```
PHASE-6-INFRASTRUCTURE-COMPLETION.md  - Full completion report
GETTING-STARTED-PHASE-6.md           - This file
```

## Quick Start (30 minutes)

### 1. Validate Manifests
```bash
cd kubernetes/
./validate-manifests.sh
```

### 2. Understand the Architecture
- Read: `kubernetes/README.md` (comprehensive guide)
- Reference: `PHASE-6-INFRASTRUCTURE-COMPLETION.md`

### 3. Prepare for Deployment
```bash
# Prerequisites:
# - Kubernetes cluster (1.24+)
# - kubectl installed and configured
# - Docker images pushed to registry
# - cert-manager installed
# - nginx-ingress installed

# Clone/review deployment checklist
cat kubernetes/DEPLOYMENT-CHECKLIST.md
```

### 4. Generate Secrets
```bash
# Create namespace
kubectl apply -f kubernetes/01-namespace.yaml

# Generate JWT secret (keep this safe!)
kubectl -n jira-analytics create secret generic jwt-secret \
  --from-literal=key=$(openssl rand -hex 32)

# Generate MySQL passwords
MYSQL_ROOT=$(openssl rand -hex 16)
MYSQL_JIRA=$(openssl rand -hex 16)

kubectl -n jira-analytics create secret generic mysql-credentials \
  --from-literal=root-password=$MYSQL_ROOT \
  --from-literal=jira-password=$MYSQL_JIRA \
  --from-literal=jira-username=jira

# Add Jira OAuth credentials
kubectl -n jira-analytics create secret generic jira-oauth-credentials \
  --from-literal=client-id=YOUR_CLIENT_ID \
  --from-literal=client-secret=YOUR_CLIENT_SECRET

# Create database connection string
DB_URL="mysql+pymysql://jira:${MYSQL_JIRA}@mysql:3306/jira_analytics"
kubectl -n jira-analytics create secret generic database-credentials \
  --from-literal=connection-string=$DB_URL
```

### 5. Deploy Step by Step

Follow `kubernetes/DEPLOYMENT-CHECKLIST.md` sections:
1. Phase 1: Namespace & RBAC ✓ (already done above)
2. Phase 2: Secrets ✓ (already done above)
3. Phase 3: Configuration
4. Phase 4: Data Layer (MySQL, Redis)
5. Phase 5: Backend (FastAPI)
6. Phase 6: Workers (Celery)
7. Phase 7: Scheduler (Celery Beat)
8. Phase 8: Frontend
9. Phase 9: Ingress & TLS
10. Phase 10: DNS & Verification

## Key Concepts

### StatefulSet vs Deployment
- **StatefulSet**: MySQL, Redis (need stable identity + persistent storage)
- **Deployment**: FastAPI, Celery, Frontend (stateless, can be replaced)

### High Availability
- **Replicas**: FastAPI (3), Frontend (2), Celery Workers (2), MySQL (1), Redis (1)
- **HPA**: FastAPI & Frontend auto-scale based on CPU/memory
- **PDB**: Pods survive node maintenance

### Data Persistence
- **MySQL PVC**: 20Gi persistent volume
- **Redis PVC**: 5Gi persistent volume
- **Ephemeral**: Logs, temp files (emptyDir)

### Security
- **Non-root**: All pods run as UID 1000+
- **Read-only**: Root filesystem is read-only
- **RBAC**: Minimal permissions per service account
- **TLS**: Auto-renewed via cert-manager + Let's Encrypt

## CI/CD Pipeline

### On Every PR
1. Lint checks (black, ruff, eslint)
2. Unit tests (pytest, vitest)
3. Build Docker images (no push)
4. E2E tests (Playwright)

**Result:** "checks passed" label on PR before merge

### On Push to Main
1. All of above
2. **Push images to Docker Hub**
3. Tag with commit SHA
4. Ready for `kubectl apply`

**Result:** New images available for deployment

### Manual: Deploy to Kubernetes
```bash
# Update image tags in manifests
# 07-fastapi-deployment.yaml
# 10-frontend-deployment.yaml
# etc.

# Apply
kubectl apply -f kubernetes/

# Watch
kubectl -n jira-analytics get pods -w
```

## Common Tasks

### Check Pod Status
```bash
kubectl -n jira-analytics get pods
kubectl -n jira-analytics describe pod <POD_NAME>
kubectl -n jira-analytics logs <POD_NAME>
```

### View Metrics
```bash
# CPU/memory usage
kubectl -n jira-analytics top pods

# HPA status
kubectl -n jira-analytics get hpa -w

# Check scaling history
kubectl -n jira-analytics describe hpa fastapi-hpa
```

### Database Access
```bash
# Exec into MySQL pod
kubectl -n jira-analytics exec -it mysql-0 -- bash
mysql -u root -p$MYSQL_ROOT_PASSWORD

# Or port-forward locally
kubectl -n jira-analytics port-forward mysql-0 3306:3306
# Connect: mysql -h127.0.0.1 -uroot -p
```

### View Logs
```bash
# FastAPI logs
kubectl -n jira-analytics logs -f deployment/fastapi

# Celery worker logs
kubectl -n jira-analytics logs -f deployment/celery-worker

# Celery Beat logs
kubectl -n jira-analytics logs -f deployment/celery-beat

# Follow all logs
kubectl -n jira-analytics logs -f --all-containers=true pods --prefix=true
```

### Verify Ingress
```bash
# Check Ingress status
kubectl -n jira-analytics get ingress

# Check certificate
kubectl -n jira-analytics describe certificate jira-analytics-cert

# Test HTTPS endpoint
curl https://jira-analytics.example.com/health
```

## Troubleshooting

### Pod Won't Start
```bash
# Check events and logs
kubectl -n jira-analytics describe pod <POD_NAME>
kubectl -n jira-analytics logs <POD_NAME>

# Common causes:
# - Image not found (update Docker username)
# - Secret missing (check kubectl get secret)
# - Insufficient resources (check kubectl describe nodes)
```

### Database Connection Fails
```bash
# Check connection string secret
kubectl -n jira-analytics get secret database-credentials -o yaml

# Test MySQL is running
kubectl -n jira-analytics get statefulset mysql

# Verify MySQL is ready
kubectl -n jira-analytics exec mysql-0 -- mysqladmin ping -uroot -p$MYSQL_ROOT_PASSWORD
```

### WebSocket Connection Fails
```bash
# Check Nginx Ingress logs
kubectl -n ingress-nginx logs -f deployment/nginx-ingress-controller

# Verify WebSocket annotation in Ingress
kubectl -n jira-analytics get ingress -o yaml | grep websocket

# Check API is responding
curl https://jira-analytics.example.com/health
```

### Certificate Not Issuing
```bash
# Check cert-manager is running
kubectl get all -n cert-manager

# Check certificate status
kubectl -n jira-analytics describe certificate jira-analytics-cert

# Check cert-manager logs
kubectl -n cert-manager logs -f deployment/cert-manager

# Might need to create ClusterIssuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

## Performance Targets

| Metric | Target | Impact |
|--------|--------|--------|
| API response time | <200ms p95 | User experience |
| Dashboard load time | <2s | Frontend speed |
| Jira sync duration | <4 min | Refresh cycle |
| WebSocket latency | <500ms | Real-time updates |
| Pod startup | <30s | Deployment speed |
| Database query | <100ms p95 | Metrics calculation |

## Resource Allocation

**Total Requests:** ~1.1 CPU cores, 3.5Gi memory  
**Total Limits:** ~5.6 CPU cores, 6.5Gi memory

**Cluster Requirements:**
- Development: 4 CPU, 8GB RAM
- Production: 8+ CPU, 16GB+ RAM

## Next Steps

1. **Test locally** (if possible):
   ```bash
   docker-compose -f backend/docker-compose.yml up
   # Visit http://localhost:3000
   ```

2. **Deploy to staging:**
   - Update domain to staging subdomain
   - Deploy manifests
   - Run E2E tests
   - Monitor metrics

3. **Deploy to production:**
   - Update domain
   - Configure backups
   - Set up monitoring/logging
   - Enable rate limiting

4. **Monitor & optimize:**
   - Watch HPA scaling
   - Tune thresholds based on load
   - Check resource usage
   - Implement disaster recovery

## Support Resources

- **Deployment Guide**: `kubernetes/README.md`
- **Checklist**: `kubernetes/DEPLOYMENT-CHECKLIST.md`
- **Architecture**: `../ARCHITECTURE.md`
- **Project Context**: `../CLAUDE.md`

## Quick Reference

```bash
# Create namespace & apply all manifests
kubectl apply -f kubernetes/01-namespace.yaml
kubectl apply -f kubernetes/02-rbac.yaml
# ... (follow DEPLOYMENT-CHECKLIST.md)

# Monitor deployment
kubectl -n jira-analytics get pods -w
kubectl -n jira-analytics get hpa -w

# Debug
kubectl -n jira-analytics describe pod <POD>
kubectl -n jira-analytics logs <POD>

# Update image
kubectl -n jira-analytics set image deployment/fastapi fastapi=<NEW_IMAGE>

# Scale manually (HPA will override)
kubectl -n jira-analytics scale deployment fastapi --replicas=5

# Rollback
kubectl -n jira-analytics rollout undo deployment/fastapi
```

---

**Status:** READY TO DEPLOY  
**Estimated Deployment Time:** 30-60 minutes (includes DNS propagation)  
**Estimated First Sync:** 5 minutes after all pods are running

Start with `kubernetes/README.md` for detailed instructions!
