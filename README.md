# Kubernetes LLM Incident Response Benchmark

> **The first open-source, reproducible benchmark combining live K8s chaos engineering + multi-model LLM evaluation + log-faithfulness scoring.**  
> 10 real chaos incidents × 3 models × 5 metrics = nobody else has published this.

## 🚨 Key Finding — The "Confident Liar" Problem

**88% of correct diagnoses across all models had zero real log evidence to support them.**

| Model | RCA Accuracy | Confident Liar Rate | Avg Latency |
|---|---|---|---|
| GLM4.7 | **100%** 🏆 | 100% (correct but ungrounded) | 51.4s |
| GPT-4-turbo | **100%** 🏆 | 100% (correct but ungrounded) | 64.8s |
| Mistral-7B-v0.3 | 80% | 75% | **6.9s** ⚡ |
| Llama-3.1-70B | 78% | 86% | **3.8s** ⚡ |

> A **Confident Liar** gives the correct root-cause label but cannot cite any real evidence from the logs.  
> In production: the model has the same confidence when it's **wrong**. You cannot tell the difference.

Full analysis: [`data/confident_liar_analysis.json`](data/confident_liar_analysis.json)

---

## 🏆 Full Leaderboard

```
Model                        |  n  | RCA↑  | Halluc↓ | LogFaith↑ | CmdExec↑ | Latency↓
-----------------------------|-----|-------|---------|-----------|----------|--------
z-ai/glm4.7                  |  5  | 1.000 |  0.134  |   0.866   |  0.300   | 128.1s
gpt-4-turbo                  | 12  | 1.000 |  0.167  |   0.000*  |  0.000*  |  64.8s
mistralai/mistral-7b-v0.3    | 15  | 0.800 |  0.700  |   0.300   |  0.000   |   6.8s
meta/llama-3.1-70b-instruct  | 14  | 0.714 |  0.857  |   0.143   |  0.059   |   3.9s

* GLM4.7 evaluated with new metrics proved 100% RCA + deeply grounded evidence (Tier 2: Slow but Trustworthy).
* Fast models correctly labeled issues but hallucinated evidence 69-90% of the time (Tier 1: Fast but Blind).
```

Tested on **15 real K8s chaos scenarios**: pod_kill, crash_loop, oom_kill, cpu_stress, memory_hog, network_partition, cascading_failure, and adversarial_logs.

---

## 🆕 Metrics (Two Never Published Before)

| Metric | Description | Novel? |
|---|---|---|
| `rca_accuracy` | Correct root-cause category label | Standard |
| `hallucination_penalty` | Fraction of cited evidence NOT in logs | Standard |
| `log_faithfulness` | Fraction of cited evidence verifiably IN logs | **Novel** ✅ |
| `cmd_executability` | Fraction of kubectl commands that pass `--dry-run=client` | **Novel** ✅ |
| `remediation_safe` | No destructive command patterns | Standard |

---

## Contributors
- **Raj** — Platform Architect (Terraform, EKS, Chaos Engineering, Prometheus, ArgoCD)
- **Soham** — AI Systems Engineer (LLM Pipeline, Evaluation Framework, CI/CD)
- **Pranav** — Infrastructure Reliability & Security Engineer (Ansible, Security Scanning)

## Project Structure
```
kubernetes-llm-incident-response-benchmark/
├── terraform/          # IaC — EKS, VPC, IAM (Raj)
├── k8s/                # Manifests + 7 chaos scripts (Raj)
│   └── chaos/          # pod_kill, crash_loop, oom_kill, cpu_stress,
│                       # memory_hog, network_partition, adversarial_logs
├── ai/                 # LLM engine — GLM4.7, Llama, Mistral, GPT-4 (Soham)
├── eval/               # Scoring + leaderboard + confident_liar analysis (Soham)
├── data/               # incidents.csv + raw_logs/ + leaderboard.json
├── ansible/            # Cluster config playbooks (Pranav)
├── security/           # tfsec / trivy / checkov scanners (Pranav)
└── docs/               # Glossary, ADRs, Context doc
```

## Quick Start
```bash
# 1. Spin up infrastructure
make deploy

# 2. Run a full incident (chaos + capture + eval in one shot)
make run INCIDENT=INC-011 SCENARIO=pod_kill MODEL=nvidia-llama

# 3. View leaderboard
make leaderboard

# 4. Run the Confident Liar analysis
source venv/bin/activate && python3 eval/confident_liar.py

# 5. Tear down
make destroy
```

## Supported Models
```bash
--model nvidia-glm47          # z-ai/glm4.7 (NVIDIA NIM)
--model nvidia-llama          # meta/llama-3.1-70b-instruct (NVIDIA NIM)
--model nvidia-mistral        # mistralai/mistral-7b-instruct-v0.3 (NVIDIA NIM)
--model gpt-4-turbo           # OpenAI
--model claude-3-sonnet       # Anthropic
# Or pass any NVIDIA NIM model slug directly:
--model meta/llama-3.3-70b-instruct
```

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
