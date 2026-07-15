# CommerceOps

A microservices e-commerce platform built to demonstrate a full DevOps toolchain:
**Docker, Terraform, Kubernetes (k3s), AWS (VPC/ALB/ASG/Lambda/ECR/RDS/CloudWatch/SNS),
Prometheus, Grafana, Ansible, Jenkins, and Git/GitHub Actions.**

The application itself is intentionally simple (register/login, place an order,
get a recommendation) — the point of this project is the infrastructure and
operations around it, not the business logic.

## Architecture

```
                              ┌────────────┐
                     ┌───────►│  frontend  │  (static UI, calls /api/*)
                     │        └────────────┘
                     │
   ┌─────────┐   ┌───┴────────┐      ┌───────────────┐
   │  nginx  │──►│ api-service│─────►│  auth-service  │──► Postgres (users)
   │ (proxy) │   │  (gateway) │──┐   └───────────────┘
   └─────────┘   └────────────┘  │   ┌───────────────┐
                                  ├──►│ order-service  │──► Postgres (orders)
                                  │   └───────┬───────┘
                                  │           │ publishes event
                                  │           ▼
                                  │      ┌─────────┐      ┌────────────────┐
                                  │      │RabbitMQ │◄─────│ worker-service │──► Redis
                                  │      └─────────┘      └────────────────┘
                                  │
                                  └──►┌───────────────────────────┐
                                      │ ai-recommendation-service │──► Redis (cache)
                                      └───────────────────────────┘

  Prometheus scrapes /metrics on every service → Grafana dashboards
```

| Service | Responsibility | Port |
|---|---|---|
| `frontend` | Minimal HTML/JS UI | 3000 |
| `api-service` | Gateway — routes `/api/*` to the right backend service | 8000 |
| `auth-service` | Register/login, JWT issuance, bcrypt password hashing (Postgres) | 8001 |
| `order-service` | Order CRUD, publishes order-created events to RabbitMQ (Postgres) | 8002 |
| `ai-recommendation-service` | Mock recommendation engine with Redis caching | 8003 |
| `worker-service` | Consumes the RabbitMQ order queue, processes orders async | 8004 |

Every service exposes `/health` (used by Docker/K8s health checks) and
`/metrics` (Prometheus format, via `prometheus-client`).

## Repository layout

```
commerceops/
├── services/                    # application code, one Flask app per service
│   ├── frontend/
│   ├── api-services/            # gateway
│   ├── auth-services/
│   ├── order-services/
│   ├── ai-recommendation-service/
│   └── worker-service/
├── infra/
│   ├── terraform/                # VPC, ALB, ASG, ECR, RDS, Lambda, CloudWatch
│   ├── ansible/                   # provisions EC2 app servers, deploys via docker compose
│   ├── k8s/                       # manifests for a k3s deployment (EKS-alternative)
│   └── nginx/                     # reverse proxy config for local dev
├── monitoring/
│   ├── prometheus/prometheus.yml
│   └── grafana/                   # provisioned datasource + dashboard
├── lambda/order-notification/     # Lambda triggered by CloudWatch alarm via SNS
├── .github/workflows/ci.yml       # lint + build check on every push
├── Jenkinsfile                    # the "real" CI/CD pipeline (build → ECR → deploy)
├── docker-compose.yml             # local dev / demo environment
├── Makefile
└── .env.example
```

## Quick start (local, docker-compose)

```bash
cp .env.example .env        # then edit secrets in .env
make up                     # build + start everything
make health                 # curl every service's /health endpoint
```

- App UI: http://localhost:8080 (via nginx) or http://localhost:3000 (direct)
- RabbitMQ management: http://localhost:15672
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (default admin/admin — set via `.env`)

Try it end to end:
```bash
curl -X POST localhost:8080/api/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"a@b.com","password":"secret123"}'

curl -X POST localhost:8080/api/orders -H 'Content-Type: application/json' \
  -d '{"user_email":"a@b.com","item":"laptop","quantity":1}'

curl "localhost:8080/api/recommend?item=laptop"
```

```bash
make down                   # stop everything
```

## Deploying to AWS

Two deployment paths are provided; both fit within AWS free-tier limits if
resources are destroyed when not in use.

### Path A — EC2 + Auto Scaling Group (Terraform + Ansible + Jenkins)
1. `cd infra/terraform && terraform init && terraform apply` — creates VPC,
   ALB, ASG (t3.micro), ECR repos, RDS (db.t3.micro), Lambda + CloudWatch alarm.
2. Jenkins pipeline (`Jenkinsfile`) builds each service, pushes to ECR.
3. Ansible (`infra/ansible/playbook.yml`) configures the EC2 instances and
   pulls the latest images via `docker compose`.
4. Access the app at the ALB DNS name (`terraform output alb_dns_name`).

### Path B — Kubernetes (k3s on EC2)
See [`infra/k8s/README.md`](infra/k8s/README.md). **Note:** this project uses
**k3s instead of EKS** — the EKS control plane costs ~$0.10/hr regardless of
usage and isn't free-tier eligible, while k3s gives the same `kubectl`
workflow at zero control-plane cost.

## Free-tier cost notes
- **No NAT Gateway** is provisioned (hourly-billed, not free) — app instances
  sit in public subnets behind security groups instead.
- **RDS**: `db.t3.micro` + 20GB storage is free for 12 months from account creation.
- **EC2**: `t3.micro`, 750 free hours/month for 12 months — keep the ASG at
  1-2 instances and run `terraform destroy` when not actively demoing.
- **EKS is intentionally avoided** in favor of k3s (see above).
- **Lambda**: 1M free requests/month — the alerting function here runs
  rarely, well within the free tier indefinitely.

## What each tool is doing in this project
- **Docker** — every service has a multi-stage Dockerfile (slim runtime image, non-root user, healthcheck).
- **Terraform** — VPC, subnets, security groups, ALB, ASG + launch template, ECR, RDS, Lambda, SNS, CloudWatch alarm.
- **Ansible** — installs Docker on EC2, logs into ECR, deploys the stack via `docker compose`.
- **Kubernetes** — Deployments/Services for all 6 microservices, StatefulSet for Postgres, ConfigMap/Secret, Ingress (Traefik).
- **AWS services** — VPC, ALB, Auto Scaling Group, RDS, ECR, Lambda, SNS, CloudWatch alarms.
- **Prometheus/Grafana** — every service instrumented with `prometheus-client`; pre-built dashboard in `monitoring/grafana/dashboards/`.
- **Jenkins** — multi-stage pipeline: lint → build → scan (Trivy) → push to ECR → deploy (Ansible or kubectl).
- **Git/GitHub Actions** — lint + Docker build matrix + Terraform validate on every push.

## Known limitations / next steps
- App logic is intentionally minimal (no real ML in the "recommendation" service, no payment processing).
- Secrets in `.env.example`/`02-secret.yaml` are placeholders — swap for AWS Secrets Manager or SSM Parameter Store before any real deployment.
- No TLS/HTTPS termination configured on the ALB/Ingress (would need an ACM cert + Route 53 domain).
- No automated tests yet (unit tests would be a good next addition per service).
