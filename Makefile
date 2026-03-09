.PHONY: help deploy destroy chaos capture eval summary leaderboard

INCIDENT ?= INC-001
SCENARIO ?= pod_kill
MODEL    ?= nvidia-glm47

help:
	@echo "============================================"
	@echo "  Kubernetes LLM Benchmark — Make Commands"
	@echo "============================================"
	@echo "  make deploy                               - Terraform apply + infra"
	@echo "  make destroy                              - Terraform destroy"
	@echo "  make chaos SCENARIO=pod_kill              - Inject chaos scenario"
	@echo "     Scenarios: pod_kill | crash_loop | oom_kill | cpu_stress |"
	@echo "                memory_hog | network_partition | adversarial_logs"
	@echo "  make capture INCIDENT=INC-001             - Capture incident evidence"
	@echo "  make eval INCIDENT=INC-001 MODEL=<model> - Run LLM evaluation"
	@echo "     Models: nvidia-glm47 | nvidia-llama | nvidia-mistral | gpt-4-turbo"
	@echo "             or any NVIDIA NIM model slug"
	@echo "  make summary                              - Print benchmark results table"
	@echo "  make leaderboard                          - Generate data/leaderboard.json"
	@echo "  make run INCIDENT=INC-006 SCENARIO=cpu_stress MODEL=nvidia-llama"
	@echo "         Shortcut: chaos + capture + eval in one command"

deploy:
	@echo "Deploying Terraform infrastructure..."
	cd terraform/environments/dev && AWS_PROFILE=terraform-admin terraform init && AWS_PROFILE=terraform-admin terraform apply -auto-approve

destroy:
	@echo "WARNING: Destroying infrastructure..."
	cd terraform/environments/dev && AWS_PROFILE=terraform-admin terraform destroy -auto-approve

chaos:
	@echo "Injecting chaos scenario: $(SCENARIO)"
	@case "$(SCENARIO)" in \
		pod_kill)          bash k8s/chaos/pod_kill.sh ;; \
		crash_loop)        bash k8s/chaos/crash_loop.sh ;; \
		oom_kill)          bash k8s/chaos/oom_kill.sh ;; \
		cpu_stress)        bash k8s/chaos/cpu_stress.sh ;; \
		memory_hog)        bash k8s/chaos/memory_hog.sh ;; \
		network_partition) bash k8s/chaos/network_partition.sh ;; \
		adversarial_logs)  bash k8s/chaos/adversarial_logs.sh ;; \
		*) echo "Unknown SCENARIO=$(SCENARIO)." && \
		   echo "Valid: pod_kill, crash_loop, oom_kill, cpu_stress, memory_hog, network_partition, adversarial_logs" && \
		   exit 1 ;; \
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

# One-shot: chaos + capture + eval (useful in a loop)
run:
	@$(MAKE) chaos SCENARIO=$(SCENARIO)
	@$(MAKE) capture INCIDENT=$(INCIDENT) SCENARIO=$(SCENARIO)
	@$(MAKE) eval INCIDENT=$(INCIDENT) MODEL=$(MODEL)

summary:
	@echo "Generating results summary..."
	@export PYTHONPATH=$$(pwd) && source venv/bin/activate && python3 eval/results_summary.py

leaderboard:
	@echo "Generating leaderboard..."
	@export PYTHONPATH=$$(pwd) && source venv/bin/activate && python3 eval/leaderboard.py
