# CommerceOps on Kubernetes (k3s)

This directory targets a lightweight **k3s** cluster on EC2 rather than EKS,
because the EKS control plane is billed (~$0.10/hr, ~$73/month) even on the
AWS free tier. k3s gives the same `kubectl`/manifest workflow at zero
control-plane cost - a good tradeoff to be able to explain in interviews.

## Bootstrap a k3s cluster (single node, EC2 t3.micro/t3.small)
```bash
curl -sfL https://get.k3s.io | sh -
sudo cat /etc/rancher/k3s/k3s.yaml   # kubeconfig - copy to your local ~/.kube/config
                                     # and change the server IP from 127.0.0.1 to the EC2 public IP
```

## Deploy
```bash
kubectl apply -f 00-namespace.yaml
kubectl apply -f 01-configmap.yaml
kubectl apply -f 02-secret.yaml       # edit real secret values first!
kubectl apply -f 03-postgres.yaml
kubectl apply -f 04-redis.yaml
kubectl apply -f 05-rabbitmq.yaml
kubectl apply -f 06-frontend.yaml
kubectl apply -f 07-api-service.yaml
kubectl apply -f 08-auth-service.yaml
kubectl apply -f 09-order-service.yaml
kubectl apply -f 10-ai-recommendation-service.yaml
kubectl apply -f 11-worker-service.yaml
kubectl apply -f 12-ingress.yaml

# or simply: kubectl apply -f .
```

## Observability
Install the kube-prometheus-stack Helm chart for Prometheus + Grafana inside
the cluster instead of the docker-compose versions used for local dev:
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace
```
Each Deployment above already carries `prometheus.io/scrape: "true"`
annotations so Prometheus auto-discovers the `/metrics` endpoints.

## Building images for the cluster
Either push to ECR and reference the full ECR URI in each Deployment's
`image:` field, or (for a fully local demo without AWS) build directly into
k3s's containerd:
```bash
docker build -t commerceops/api-service:latest ../../services/api-services
docker save commerceops/api-service:latest | sudo k3s ctr images import -
```
