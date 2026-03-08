.PHONY: help deploy destroy chaos capture eval summary

INCIDENT ?= INC-001
SCENARIO ?= pod_kill
MODEL    ?= nvidia-glm47

help:
	@echo "============================================"
	@echo "  Kubernetes LLM Benchmark — Make Commands"
	@echo "============================================"
	@echo "  make deploy                       - Terraform apply + Helm installs"
	@echo "  make destroy                      - Terraform destroy"
	@echo "  make chaos SCENARIO=pod_kill      - Inject chaos (pod_kill|crash_loop|oom_kill)"
	@echo "  make capture INCIDENT=INC-001     - Capture incident evidence"
	@echo "  make eval INCIDENT=INC-001        - Run LLM evaluation and write to incidents.csv"
	@echo "  make summary                      - Print benchmark results table"

deploy:
	@echo "Deploying Terraform infrastructure..."
	cd terraform/environments/dev && terraform init && terraform apply -auto-approve

destroy:
	@echo "WARNING: Destroying infrastructure..."
	cd terraform/environments/dev && terraform destroy -auto-approve

chaos:
	@echo "Injecting chaos scenario: $(SCENARIO)"
	@case "$(SCENARIO)" in \
		pod_kill)    bash k8s/chaos/pod_kill.sh ;; \
		crash_loop)  bash k8s/chaos/crash_loop.sh ;; \
		oom_kill)    bash k8s/chaos/oom_kill.sh ;; \
		*) echo "Unknown SCENARIO=$(SCENARIO). Valid: pod_kill, crash_loop, oom_kill" && exit 1 ;; \
	esac

capture:
	@echo "Capturing incident: $(INCIDENT) | scenario: $(SCENARIO)"
	@bash capture_incident.sh $(INCIDENT) $(SCENARIO) PodCrashLooping

eval:
	@echo "Running LLM evaluation for $(INCIDENT) using $(MODEL)..."
	@export PYTHONPATH=$$(pwd) && \
	  source venv/bin/activate && \
	  python3 -m ai.llm_engine --incident data/raw_logs/$(INCIDENT) --model $(MODEL)
	@echo "--- Tail of incidents.csv ---"
	@tail -1 data/incidents.csv

summary:
	@echo "Generating results summary..."
	@export PYTHONPATH=$$(pwd) && source venv/bin/activate && python3 eval/results_summary.py
