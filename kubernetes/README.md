# Kubernetes Deployment Guide

This directory contains complete Kubernetes manifests for deploying the Jira Team Performance Analytics platform to production.

## Architecture Overview

The deployment consists of:

- **Frontend**: React app served via Nginx (2 replicas, HPA)
- **Backend API**: FastAPI (3 replicas, HPA)
- **Celery Workers**: Background job processors (2 replicas)
- **Celery Beat**: Scheduler for 5-minute Jira sync (1 replica, singleton)
- **MySQL**: Database (1 StatefulSet, persistent volume)
- **Redis**: Cache & message broker (1 StatefulSet, persistent volume)
- **Ingress**: TLS termination + routing via cert-manager + nginx

## File Structure

```
kubernetes/
├── 01-namespace.yaml              # Namespace, resource quotas, limits
├── 02-rbac.yaml                   # ServiceAccount, ClusterRole, RoleBinding
├── 03-configmap.yaml              # Config maps & environment variables
├── 04-secrets.yaml.example        # Secret template (NOT checked in)
├── 04b-database-credentials.yaml  # Database connection string secret
├── 05-mysql-statefulset.yaml      # MySQL 8.0 StatefulSet
├── 06-redis-statefulset.yaml      # Redis 7 StatefulSet
├── 07-fastapi-deployment.yaml     # FastAPI Deployment + Service + HPA + PDB
├── 08-celery-worker-deployment.yaml  # Celery Worker Deployment + PDB
├── 09-celery-beat-deployment.yaml    # Celery Beat Deployment (singleton)
├── 10-frontend-deployment.yaml       # Frontend Deployment + Service + HPA + PDB
├── 11-ingress.yaml                   # Ingress + cert-manager + basic auth
└── README.md                      # This file
```

## Prerequisites

1. **Kubernetes cluster** (1.24+)
   - At least 4 CPU cores, 8GB RAM for dev/staging
   - 16+ CPU, 32GB+ RAM for production

2. **Installed tools**:
   ```bash
   kubectl         # Kubernetes CLI
   helm           # (optional) for package management
   cert-manager   # For TLS certificate automation
   nginx-ingress  # For Ingress controller
   ```

3. **Cluster preparation**:
   ```bash
   # Install cert-manager
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

   # Install nginx-ingress
   helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
   helm repo update
   helm install nginx-ingress ingress-nginx/ingress-nginx \
     --namespace ingress-nginx \
     --create-namespace \
     --set controller.service.type=LoadBalancer
   ```

4. **Container images**:
   - `docker.io/YOUR_USERNAME/jira-analytics-backend:latest`
   - `docker.io/YOUR_USERNAME/jira-analytics-frontend:latest`

   Build locally:
   ```bash
   # Backend
   cd backend
   docker build -t docker.io/YOUR_USERNAME/jira-analytics-backend:latest .
   docker push docker.io/YOUR_USERNAME/jira-analytics-backend:latest

   # Frontend
   cd frontend
   docker build --target runtime -t docker.io/YOUR_USERNAME/jira-analytics-frontend:latest .
   docker push docker.io/YOUR_USERNAME/jira-analytics-frontend:latest
   ```

## Deployment Steps

### Step 1: Create Secrets

```bash
# Create namespace
kubectl apply -f 01-namespace.yaml

# Generate JWT secret
kubectl -n jira-analytics create secret generic jwt-secret \
  --from-literal=key=$(openssl rand -hex 32)

# Create MySQL credentials
MYSQL_ROOT_PASSWORD=$(openssl rand -hex 16)
MYSQL_JIRA_PASSWORD=$(openssl rand -hex 16)

kubectl -n jira-analytics create secret generic mysql-credentials \
  --from-literal=root-password=$MYSQL_ROOT_PASSWORD \
  --from-literal=jira-password=$MYSQL_JIRA_PASSWORD \
  --from-literal=jira-username=jira

# Create database connection string secret
DB_URL="mysql+pymysql://jira:${MYSQL_JIRA_PASSWORD}@mysql:3306/jira_analytics"
kubectl -n jira-analytics create secret generic database-credentials \
  --from-literal=connection-string=$DB_URL

# Create Jira OAuth credentials (from your Jira app registration)
kubectl -n jira-analytics create secret generic jira-oauth-credentials \
  --from-literal=client-id=YOUR_CLIENT_ID \
  --from-literal=client-secret=YOUR_CLIENT_SECRET
```

### Step 2: Create ClusterIssuer for TLS

```bash
# Create Let's Encrypt issuer for TLS certificates
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

### Step 3: Update ConfigMaps & Apply Manifests

Edit `03-configmap.yaml` to match your environment:
- Replace `CORS_ORIGINS` with your domain
- Set `API_BASE_URL` correctly
- Update `JIRA_API_URL` if using custom Jira instance

Then apply:
```bash
kubectl apply -f 02-rbac.yaml
kubectl apply -f 03-configmap.yaml
kubectl apply -f 04b-database-credentials.yaml
kubectl apply -f 05-mysql-statefulset.yaml
kubectl apply -f 06-redis-statefulset.yaml
```

### Step 4: Update Image Names & Deploy

Edit `07-fastapi-deployment.yaml`, `08-celery-worker-deployment.yaml`, `09-celery-beat-deployment.yaml`, and `10-frontend-deployment.yaml`:
- Replace `docker.io/YOUR_DOCKER_USERNAME/` with your actual Docker username

Then apply:
```bash
kubectl apply -f 07-fastapi-deployment.yaml
kubectl apply -f 08-celery-worker-deployment.yaml
kubectl apply -f 09-celery-beat-deployment.yaml
kubectl apply -f 10-frontend-deployment.yaml
```

### Step 5: Update & Deploy Ingress

Edit `11-ingress.yaml`:
- Replace all `jira-analytics.example.com` with your actual domain
- Update the cert-manager email if needed
- Change basic auth credentials for metrics endpoint

Then apply:
```bash
kubectl apply -f 11-ingress.yaml
```

### Step 6: Verify Deployment

```bash
# Check all resources
kubectl -n jira-analytics get all

# Check pod status
kubectl -n jira-analytics get pods -w

# Check service endpoints
kubectl -n jira-analytics get svc

# Check Ingress status and IP
kubectl -n jira-analytics get ingress

# View logs
kubectl -n jira-analytics logs deployment/fastapi -f
kubectl -n jira-analytics logs deployment/celery-worker -f
kubectl -n jira-analytics logs statefulset/mysql -f

# Verify database migrations ran
kubectl -n jira-analytics logs job.batch/fastapi-migrate --tail=20
```

### Step 7: Configure DNS

Point your domain to the Ingress LoadBalancer IP:
```bash
# Get the Ingress IP
kubectl -n jira-analytics get ingress

# Add DNS record:
# jira-analytics.example.com A <INGRESS_IP>
```

Wait for DNS propagation and cert-manager to issue certificates:
```bash
# Check certificate status
kubectl -n jira-analytics get certificate
kubectl -n jira-analytics describe certificate jira-analytics-cert
```

## Post-Deployment

### Health Checks

```bash
# API health
curl https://jira-analytics.example.com/health

# Frontend health
curl https://jira-analytics.example.com/healthz

# Metrics (if exposed)
curl -u prometheus:changeme https://metrics.jira-analytics.example.com/metrics
```

### Monitoring

```bash
# Watch pod status
kubectl -n jira-analytics get pods -w

# View resource usage
kubectl -n jira-analytics top nodes
kubectl -n jira-analytics top pods

# Check HPA status
kubectl -n jira-analytics get hpa -w
```

### Database Access

```bash
# Port-forward to MySQL for backups/maintenance
kubectl -n jira-analytics port-forward statefulset/mysql 3306:3306

# Connect locally:
mysql -h127.0.0.1 -uroot -p<MYSQL_ROOT_PASSWORD>
```

### Scaling

```bash
# Manual scaling
kubectl -n jira-analytics scale deployment fastapi --replicas=5
kubectl -n jira-analytics scale deployment celery-worker --replicas=4

# HPA will auto-scale based on CPU/memory metrics
kubectl -n jira-analytics get hpa -w
```

## Troubleshooting

### Pods not starting

```bash
# Check pod status and events
kubectl -n jira-analytics describe pod <POD_NAME>

# Check logs
kubectl -n jira-analytics logs <POD_NAME>

# Check resource availability
kubectl describe nodes
```

### Database connection errors

```bash
# Check MySQL StatefulSet
kubectl -n jira-analytics describe statefulset mysql

# Verify secret exists
kubectl -n jira-analytics get secret database-credentials -o yaml

# Test MySQL connectivity
kubectl -n jira-analytics exec -it mysql-0 -- mysql -u root -p<PASSWORD>
```

### WebSocket connection failures

```bash
# Check Nginx Ingress logs
kubectl -n ingress-nginx logs -f deployment/nginx-ingress-controller

# Verify Ingress annotation for WebSocket
kubectl -n jira-analytics get ingress -o yaml | grep websocket
```

### Certificate issues

```bash
# Check cert-manager
kubectl get all -n cert-manager

# Check certificate status
kubectl -n jira-analytics get certificate -o yaml

# Check cert-manager logs
kubectl -n cert-manager logs -f deployment/cert-manager
```

## Environment Variables Reference

| Variable | Source | Purpose |
|----------|--------|---------|
| `DATABASE_URL` | secret: database-credentials | DB connection string |
| `REDIS_URL` | config: jira-analytics-config | Redis broker URL |
| `JWT_SECRET` | secret: jwt-secret | JWT signing key |
| `JIRA_CLIENT_ID` | secret: jira-oauth-credentials | Jira OAuth client ID |
| `JIRA_CLIENT_SECRET` | secret: jira-oauth-credentials | Jira OAuth client secret |
| `LOG_LEVEL` | config: jira-analytics-config | Logging level (info/debug/error) |
| `ENVIRONMENT` | config: jira-analytics-config | Environment (production/staging/dev) |
| `SYNC_INTERVAL_MINUTES` | config: jira-analytics-config | Celery Beat sync interval |

## Resource Limits & Requests

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| FastAPI | 100m | 500m | 256Mi | 512Mi |
| Celery Worker | 200m | 1000m | 512Mi | 1Gi |
| Celery Beat | 50m | 200m | 256Mi | 512Mi |
| Frontend | 50m | 200m | 128Mi | 256Mi |
| MySQL | 200m | 1000m | 512Mi | 1Gi |
| Redis | 100m | 500m | 256Mi | 512Mi |

Adjust based on your workload and cluster capacity.

## Backup & Recovery

### MySQL Backups

```bash
# Create backup
kubectl -n jira-analytics exec mysql-0 -- mysqldump \
  -u root -p$MYSQL_ROOT_PASSWORD \
  jira_analytics > backup.sql

# Restore from backup
kubectl -n jira-analytics exec -i mysql-0 -- mysql \
  -u root -p$MYSQL_ROOT_PASSWORD \
  jira_analytics < backup.sql
```

### Persistent Volume Management

```bash
# List PVCs
kubectl -n jira-analytics get pvc

# Check usage
kubectl -n jira-analytics exec mysql-0 -- df -h /var/lib/mysql
kubectl -n jira-analytics exec redis-0 -- df -h /data
```

## Cleanup

```bash
# Delete entire namespace and all resources
kubectl delete namespace jira-analytics

# Delete individual resources
kubectl delete -f kubernetes/ -n jira-analytics
```

## Production Readiness Checklist

- [ ] All images pushed to private registry with authentication
- [ ] Secrets created and stored in secure key management system (e.g., HashiCorp Vault, AWS Secrets Manager)
- [ ] TLS certificates auto-renewing via cert-manager
- [ ] Resource requests/limits validated against cluster capacity
- [ ] HPA metrics tested and tuned for your workload
- [ ] Database backups configured and tested
- [ ] Monitoring/logging system deployed (Prometheus, ELK, etc.)
- [ ] Disaster recovery plan documented
- [ ] Network policies configured if needed
- [ ] RBAC roles reviewed for least privilege
- [ ] Pod security policies/standards enforced
- [ ] Rate limiting configured on Ingress
- [ ] All health checks validated
- [ ] Load testing completed
- [ ] Runbooks documented for common issues

## Support & Maintenance

See `../KUBERNETES-DEPLOYMENT.md` for detailed infrastructure documentation.
