#!/usr/bin/env bash
set -euo pipefail

OUT=/usr/share/nginx/html/runtime-config.js

cat > "${OUT}" <<EOF
window.__APP_CONFIG__ = {
  API_BASE_URL: "${API_BASE_URL:-/api}",
  WS_URL: "${WS_URL:-/ws}",
  ENVIRONMENT: "${ENVIRONMENT:-production}"
};
EOF
