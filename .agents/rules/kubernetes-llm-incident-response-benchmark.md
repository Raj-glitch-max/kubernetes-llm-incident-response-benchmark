---
trigger: always_on
---

# Workspace Rules — kubernetes-llm-incident-response-benchmark

## Project Context
- This is a Kubernetes incident response benchmark measuring LLM (GPT-4 Turbo + Claude 3 Sonnet) accuracy on diagnosing real chaos experiments.
- Raj owns: Terraform, EKS, Chaos scripts, Prometheus alert rules, ArgoCD.
- Soham owns: LLM RCA engine, prompt templates, evaluation framework, GitHub Actions CI.

## Tech Stack
- Cloud: AWS EKS (us-east-1), t3.medium nodes
- IaC: Terraform (modules pattern — no flat configs)
- Kubernetes: 1.29, Deployments + Services + HPA + RBAC
- Monitoring: Prometheus + Grafana via Helm
- GitOps: ArgoCD (sync from `k8s/` folder)
- LLM: OpenAI GPT-4 Turbo + Anthropic Claude 3 Sonnet via Python SDK
- CI: GitHub Actions
- Data: `data/incidents.csv` is the sacred dataset — never overwrite, only append
- Chaos: Custom Bash scripts in `k8s/chaos/`

## Folder Rules
- `terraform/` — Raj's domain. Never touch without Raj's context.
- `k8s/` — Kubernetes manifests, synced via ArgoCD.
- `ai/` — LLM engine and prompts. Soham's domain.
- `eval/` — Evaluation scripts. Soham's domain.
- `data/` — Dataset. Append only. Never reformat existing rows.
- `docs/` — All documentation. Both owners.

## Experiment Rules
- Every chaos experiment produces a folder: `data/raw_logs/INC-XXX/` with exactly 4 files:
  `metadata.json`, `pod_logs.txt`, `describe_output.txt`, `events.txt`
- Every experiment appends exactly one row to `data/incidents.csv`
- Ground truth is set in `metadata.json` BEFORE the LLM is called — never after

## LLM Rules
- LLM must only reference evidence present in the input JSON — no external knowledge
- Output must always be valid JSON matching the `LLMOutput` schema in `ai/incident_schema.py`
- Never suggest changing the `LLMOutput` schema without updating evaluation scripts simultaneously

## Prometheus Rules
- Every new chaos scenario must have a matching alert rule in `k8s/apps/prometheus/alert-rules.yaml`
- Alert severity labels must be one of: `critical`, `warning`, `info`
- Alert names must match the chaos scenario naming convention (PascalCase): `PodCrashLooping`, `NodeNotReady`
