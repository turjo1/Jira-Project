#!/bin/bash
# Validation script for Kubernetes manifests
# Checks that all required files exist and YAML is valid

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Kubernetes Manifest Validation ==="
echo ""

# Required manifest files
REQUIRED_FILES=(
  "01-namespace.yaml"
  "02-rbac.yaml"
  "03-configmap.yaml"
  "04-secrets.yaml.example"
  "04b-database-credentials.yaml"
  "05-mysql-statefulset.yaml"
  "06-redis-statefulset.yaml"
  "07-fastapi-deployment.yaml"
  "08-celery-worker-deployment.yaml"
  "09-celery-beat-deployment.yaml"
  "10-frontend-deployment.yaml"
  "11-ingress.yaml"
  "README.md"
  "DEPLOYMENT-CHECKLIST.md"
)

echo "Step 1: Checking required files exist..."
MISSING_FILES=()
for file in "${REQUIRED_FILES[@]}"; do
  if [ -f "$file" ]; then
    echo "  ✓ $file"
  else
    echo "  ✗ $file (MISSING)"
    MISSING_FILES+=("$file")
  fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
  echo ""
  echo "ERROR: Missing files:"
  for file in "${MISSING_FILES[@]}"; do
    echo "  - $file"
  done
  exit 1
fi

echo ""
echo "Step 2: Validating YAML syntax..."
YAML_FILES=(
  "01-namespace.yaml"
  "02-rbac.yaml"
  "03-configmap.yaml"
  "04b-database-credentials.yaml"
  "05-mysql-statefulset.yaml"
  "06-redis-statefulset.yaml"
  "07-fastapi-deployment.yaml"
  "08-celery-worker-deployment.yaml"
  "09-celery-beat-deployment.yaml"
  "10-frontend-deployment.yaml"
  "11-ingress.yaml"
)

INVALID_YAML=()
for file in "${YAML_FILES[@]}"; do
  if command -v yq &> /dev/null; then
    if yq eval '.' "$file" > /dev/null 2>&1; then
      echo "  ✓ $file (valid YAML)"
    else
      echo "  ✗ $file (invalid YAML)"
      INVALID_YAML+=("$file")
    fi
  elif command -v python3 &> /dev/null; then
    if python3 -c "import yaml; yaml.safe_load(open('$file'))" 2> /dev/null; then
      echo "  ✓ $file (valid YAML)"
    else
      echo "  ✗ $file (invalid YAML)"
      INVALID_YAML+=("$file")
    fi
  else
    echo "  ⚠ $file (skipped - no YAML validator found)"
  fi
done

if [ ${#INVALID_YAML[@]} -gt 0 ]; then
  echo ""
  echo "ERROR: Invalid YAML files:"
  for file in "${INVALID_YAML[@]}"; do
    echo "  - $file"
  done
  exit 1
fi

echo ""
echo "Step 3: Checking for common issues..."

# Check that 04-secrets.yaml.example is not committed as real secret
if [ -f "04-secrets.yaml" ]; then
  echo "  ✗ WARNING: 04-secrets.yaml found (should not commit real secrets)"
  echo "    → Use 04-secrets.yaml.example as template instead"
fi

# Check Celery Beat replica count
if grep -q "replicas: 1" "09-celery-beat-deployment.yaml"; then
  echo "  ✓ Celery Beat has exactly 1 replica (singleton)"
else
  echo "  ✗ Celery Beat replica count incorrect (should be 1)"
  exit 1
fi

# Check that image names have placeholders
if grep -q "YOUR_DOCKER_USERNAME" "07-fastapi-deployment.yaml" || \
   grep -q "YOUR_DOCKER_USERNAME" "10-frontend-deployment.yaml"; then
  echo "  ✓ Image names have placeholders (need updating before deploy)"
else
  echo "  ⚠ Image names may already be set (verify before deploy)"
fi

# Check resource requests are set
for file in "07-fastapi-deployment.yaml" "08-celery-worker-deployment.yaml" "10-frontend-deployment.yaml"; do
  if grep -q "requests:" "$file" && grep -q "limits:" "$file"; then
    echo "  ✓ $file has resource requests and limits"
  else
    echo "  ✗ $file missing resource configuration"
    exit 1
  fi
done

echo ""
echo "Step 4: Checking documentation..."
if [ -f "README.md" ]; then
  LINES=$(wc -l < README.md)
  echo "  ✓ README.md ($LINES lines)"
fi

if [ -f "DEPLOYMENT-CHECKLIST.md" ]; then
  LINES=$(wc -l < DEPLOYMENT-CHECKLIST.md)
  echo "  ✓ DEPLOYMENT-CHECKLIST.md ($LINES lines)"
fi

echo ""
echo "=== Validation Summary ==="
echo ""
echo "All required Kubernetes manifests are present and valid."
echo ""
echo "Next steps:"
echo "  1. Review kubernetes/README.md for deployment guide"
echo "  2. Update image names (docker.io/YOUR_DOCKER_USERNAME/)"
echo "  3. Generate secrets using kubectl create secret commands"
echo "  4. Follow DEPLOYMENT-CHECKLIST.md for step-by-step deployment"
echo ""
echo "To deploy:"
echo "  kubectl apply -f kubernetes/01-namespace.yaml"
echo "  kubectl apply -f kubernetes/02-rbac.yaml"
echo "  kubectl apply -f kubernetes/03-configmap.yaml"
echo "  kubectl apply -f kubernetes/04b-database-credentials.yaml"
echo "  kubectl apply -f kubernetes/05-mysql-statefulset.yaml"
echo "  kubectl apply -f kubernetes/06-redis-statefulset.yaml"
echo "  kubectl apply -f kubernetes/07-fastapi-deployment.yaml"
echo "  kubectl apply -f kubernetes/08-celery-worker-deployment.yaml"
echo "  kubectl apply -f kubernetes/09-celery-beat-deployment.yaml"
echo "  kubectl apply -f kubernetes/10-frontend-deployment.yaml"
echo "  kubectl apply -f kubernetes/11-ingress.yaml"
echo ""
echo "✓ Validation passed!"
