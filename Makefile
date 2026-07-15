.PHONY: up down logs ps health build clean tf-init tf-plan tf-apply tf-destroy ansible-deploy k8s-apply k8s-delete

## --- Local development (docker-compose) ---

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

build:
	docker compose build

clean:
	docker compose down -v --remove-orphans

health:
	@echo "--- frontend ---"; curl -sf http://localhost:3000/health || echo "DOWN"
	@echo "--- api-service ---"; curl -sf http://localhost:8000/health || echo "DOWN"
	@echo "--- auth-service ---"; curl -sf http://localhost:8001/health || echo "DOWN"
	@echo "--- order-service ---"; curl -sf http://localhost:8002/health || echo "DOWN"
	@echo "--- ai-recommendation-service ---"; curl -sf http://localhost:8003/health || echo "DOWN"
	@echo "--- worker-service ---"; curl -sf http://localhost:8004/health || echo "DOWN"

## --- Terraform (AWS infra) ---

tf-init:
	cd infra/terraform && terraform init

tf-plan:
	cd infra/terraform && terraform plan

tf-apply:
	cd infra/terraform && terraform apply

tf-destroy:
	cd infra/terraform && terraform destroy

## --- Ansible (configure/deploy EC2 app servers) ---

ansible-deploy:
	cd infra/ansible && ansible-playbook -i inventory.ini playbook.yml

## --- Kubernetes (k3s) ---

k8s-apply:
	kubectl apply -f infra/k8s/

k8s-delete:
	kubectl delete -f infra/k8s/
