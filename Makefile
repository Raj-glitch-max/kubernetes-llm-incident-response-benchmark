.PHONY: help deploy destroy chaos eval

help:
	@echo "Available commands:"
	@echo "  make deploy   - Apply Terraform and sync ArgoCD (stub)"
	@echo "  make destroy  - Tear down everything (Terraform destroy)"
	@echo "  make chaos    - Menu to run a specific chaos script"
	@echo "  make eval     - Run the LLM evaluation pipeline across all incidents"

deploy:
	@echo "Deploying Terraform infrastructure..."
	cd terraform/environments/dev && terraform init && terraform apply -auto-approve

destroy:
	@echo "WARNING: Destroying infrastructure..."
	cd terraform/environments/dev && terraform destroy -auto-approve

chaos:
	@echo "Available Chaos Scripts:"
	@echo "1. pod_kill"
	@echo "2. crash_loop"
	@echo "3. oom_kill"
	@read -p "Select chaos to inject (1-3): " choice; \
	case "$$choice" in \
		1) bash k8s/chaos/pod_kill.sh ;; \
		2) bash k8s/chaos/crash_loop.sh ;; \
		3) bash k8s/chaos/oom_kill.sh ;; \
		*) echo "Invalid selection" ;; \
	esac

eval:
	@echo "Running Python LLM Evaluation Framework..."
	export PYTHONPATH=$$(pwd) && python3 -m pytest eval/
