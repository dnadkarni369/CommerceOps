#!/usr/bin/env bash
# Renders the commerceops-config ConfigMap and commerceops-secrets Secret
# using real values (RDS endpoint, DB creds, JWT secret) instead of the
# placeholder files checked into git, then applies them with kubectl.
#
# Called from the Jenkins pipeline with values sourced from:
#   - Terraform outputs (RDS endpoint)
#   - Jenkins credentials store (DB password, JWT secret, RabbitMQ creds)
# Nothing here is hardcoded or committed - this script just wires those
# values into the cluster at deploy time.
#
# Required env vars: KUBECONFIG, RDS_ENDPOINT, POSTGRES_USER,
# POSTGRES_PASSWORD, POSTGRES_DB, JWT_SECRET_KEY, RABBITMQ_USER, RABBITMQ_PASSWORD
set -euo pipefail

: "${KUBECONFIG:?KUBECONFIG must be set}"
: "${RDS_ENDPOINT:?RDS_ENDPOINT must be set}"
: "${POSTGRES_USER:?}"
: "${POSTGRES_PASSWORD:?}"
: "${POSTGRES_DB:?}"
: "${JWT_SECRET_KEY:?}"
: "${RABBITMQ_USER:?}"
: "${RABBITMQ_PASSWORD:?}"

# RDS endpoints come back as "host:port" - strip the port, k8s config wants host only
POSTGRES_HOST="${RDS_ENDPOINT%%:*}"

kubectl create namespace commerceops --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap commerceops-config \
  --namespace=commerceops \
  --from-literal=APP_ENV=production \
  --from-literal=POSTGRES_HOST="${POSTGRES_HOST}" \
  --from-literal=POSTGRES_PORT=5432 \
  --from-literal=POSTGRES_DB="${POSTGRES_DB}" \
  --from-literal=REDIS_HOST=redis \
  --from-literal=REDIS_PORT=6379 \
  --from-literal=RABBITMQ_HOST=rabbitmq \
  --from-literal=RABBITMQ_PORT=5672 \
  --from-literal=RABBITMQ_QUEUE=order_queue \
  --from-literal=JWT_ALGORITHM=HS256 \
  --from-literal=API_SERVICE_PORT=8000 \
  --from-literal=AUTH_SERVICE_PORT=8001 \
  --from-literal=ORDER_SERVICE_PORT=8002 \
  --from-literal=AI_SERVICE_PORT=8003 \
  --from-literal=WORKER_SERVICE_PORT=8004 \
  --from-literal=FRONTEND_PORT=3000 \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic commerceops-secrets \
  --namespace=commerceops \
  --from-literal=POSTGRES_USER="${POSTGRES_USER}" \
  --from-literal=POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
  --from-literal=JWT_SECRET_KEY="${JWT_SECRET_KEY}" \
  --from-literal=RABBITMQ_USER="${RABBITMQ_USER}" \
  --from-literal=RABBITMQ_PASSWORD="${RABBITMQ_PASSWORD}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "ConfigMap + Secret applied (postgres host = ${POSTGRES_HOST}, pointing at RDS, not in-cluster postgres)"
