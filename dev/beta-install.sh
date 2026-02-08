#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${KUBECONFIG:=}"
: "${PLATFORM_GITOPS_ROOT:=${ROOT_DIR}/platform/gitops/app-of-apps/root.yaml}"

echo "[beta-install] Applying app-of-apps manifest: ${PLATFORM_GITOPS_ROOT}"
kubectl apply -f "${PLATFORM_GITOPS_ROOT}"

echo "[beta-install] Waiting for management namespace resources (best effort)"
kubectl get pods -A | grep -E 'platform-api|platform-worker|argocd|keycloak|vault|harbor|grafana|loki|prometheus' || true

echo "[beta-install] Done"
