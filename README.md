# Kubernetes LLM Incident Response Benchmark

A benchmark measuring how well Large Language Models can act as First Responders during Kubernetes production incidents.

## Contributors
- **Raj Patil** — Platform Architect (Terraform, EKS, Chaos Engineering, Prometheus, ArgoCD)
- **Soham** — AI Systems Engineer (LLM Pipeline, Evaluation Framework, CI/CD)
- **Pranav** — Infrastructure Reliability & Security Engineer (Ansible, Security Scanning, Cost Monitoring)

## Project Structure
```
kubernetes-llm-incident-response-benchmark/
├── terraform/          # Infrastructure as Code (Raj)
├── ansible/            # Cluster configuration playbooks (Pranav)
├── security/           # Image and infra security scanners (Pranav)
├── k8s/                # Kubernetes manifests + Chaos scripts (Raj)
├── ai/                 # LLM engine + prompts (Soham)
├── eval/               # Evaluation framework and scoring (Soham)
├── data/               # Raw incident logs + incidents.csv
└── docs/               # Glossary, ADRs, Context, Run Session guide
```

## Quick Start
```bash
# 1. Spin up infrastructure
make deploy

# 2. Inject chaos
make chaos SCENARIO=pod_kill

# 3. Capture and evaluate
make capture INCIDENT=INC-001
make eval INCIDENT=INC-001 MODEL=nvidia-qwen3

# 4. View results
make summary
```

## Benchmark Results

| Incident | Scenario          | Model        | RCA Score | Latency | Safe Remediation |
|----------|-------------------|--------------|-----------|---------|-----------------|
| INC-000  | crash_loop (mock) | gpt-4-turbo  | 1.0       | 2.45s   | ✅              |
| INC-001  | pod_kill          | nvidia-qwen3 | —         | —       | —               |
| INC-002  | crash_loop        | nvidia-qwen3 | —         | —       | —               |
| INC-003  | oom_kill          | nvidia-qwen3 | —         | —       | —               |
| INC-004  | pod_kill          | nvidia-qwen3 | —         | —       | —               |
| INC-005  | crash_loop        | nvidia-qwen3 | —         | —       | —               |

> Results will be filled in after `terraform apply` + 5-incident benchmark run.

**Model Tested:** `qwen/qwen3-235b-a22b` via NVIDIA NIM API  
**Evaluation Framework:** Custom RCA Accuracy + Hallucination Penalty + Remediation Safety Scorer  
**Infrastructure:** AWS EKS (us-east-1) + custom Bash Chaos scripts
