# Project Context — Kubernetes LLM Incident Benchmark
> Single source of truth. Paste this into any AI assistant before starting work.
> Last updated: March 2026 | Owners: Raj Patil & Soham

---

## 1. Who We Are

### Raj
- Final-year B.Tech, Electronics & Computer Engineering — MIT ADT University, Pune
- Role: **Platform Architect** — owns all infra, chaos, and observability
- Stack: AWS (EKS, EC2, RDS, VPC, S3, IAM), Terraform, Kubernetes, ArgoCD,
  Prometheus, Grafana, Jenkins, GitHub Actions, Trivy, Ansible
- Style: Direct. Learns by doing. Thinks like an SRE. No theory without practice.

### Soham
- Role: **AI Systems Engineer** — owns LLM pipeline, evaluation, and CI
- Stack: Python, Docker basics, GitHub Actions
- Kubernetes and cloud are newer territory — needs brief infra context when relevant
- Style: Works well with concrete checklists, short feedback loops, runnable examples

### How any AI assistant should treat us
- Raj: skip basics, go straight to trade-offs, design decisions, advanced patterns
- Soham: short infra explanations + working code examples, not long theory
- Both: actionable steps first, theory after. Working rough code > perfect diagrams.

---

## 2. The Project

### One-line description
A **Kubernetes incident response benchmark** that tests how well LLMs (GPT-4 Turbo,
Claude 3 Sonnet) can diagnose real Kubernetes failures from logs, events, and metrics.

### Why it exists
- "AI for DevOps" tools make claims with no hard data behind them
- No open benchmark exists measuring LLM root-cause accuracy on live Kubernetes
  chaos experiments with reproducible infra and public data
- This project produces that data — with real experiments, real scoring, real findings

### What success looks like
1. Public GitHub repo — anyone can clone and reproduce the benchmark
2. `data/incidents.csv` — 50 chaos experiments with ground truth + LLM predictions + scores
3. `docs/benchmark.md` — model-wise results: accuracy, hallucination rate, latency
4. GitHub Actions CI — runs evaluation automatically on every push
5. `make deploy` / `make chaos` / `make eval` — one-command operations
6. Signal injected into 3 engineering communities with real data

---

## 3. Ownership Split

| Area | Owner |
|---|---|
| Terraform modules (VPC, EKS, IAM) | Raj |
| Kubernetes manifests + Helm | Raj |
| Chaos scripts (`k8s/chaos/`) | Raj |
| Prometheus alert rules + Grafana dashboards | Raj |
| ArgoCD setup + GitOps sync | Raj |
| Runbooks (`docs/runbooks/`) | Raj |
| LLM RCA engine (`ai/rca_engine.py`) | Soham |
| Prompt templates (`ai/prompts/`) | Soham |
| Incident schema (`ai/incident_schema.py`) | Soham |
| Evaluation framework (`eval/evaluate.py`) | Soham |
| GitHub Actions CI (`.github/workflows/`) | Soham |
| AWS cost monitoring layer | Soham |
| README, docs, ADRs, posts | Both |

---

## 4. Architecture Decisions (Summary)

| ADR | Decision |
|---|---|
| ADR-001 | Cloud: AWS |
| ADR-002 | IaC: Terraform |
| ADR-003 | LLMs: GPT-4 Turbo (primary) + Claude 3 Sonnet (comparison) |
| ADR-004 | GitOps: ArgoCD |
| ADR-005 | Chaos: Custom Bash/Python scripts (not LitmusChaos) |
| ADR-006 | Evaluation: Custom 4-metric framework (not ROUGE or human-only) |
| ADR-007 | Chaos script ownership: Raj writes + runs chaos. Soham writes eval only. |

Full ADR details: `docs/adr/`

---

## 5. Tech Stack

| Layer | Tool |
|---|---|
| Cloud | AWS EKS (us-east-1), t3.medium × 3 nodes |
| IaC | Terraform (modular: `terraform/modules/vpc`, `eks`, `monitoring`) |
| Kubernetes | v1.29 — Deployments, Services, HPA, RBAC, NetworkPolicies |
| Monitoring | Prometheus + Grafana (Helm, `monitoring` namespace) |
| Alerting | Alertmanager — routes named alerts to pipeline |
| GitOps | ArgoCD — syncs `k8s/` folder to cluster |
| Chaos | Custom Bash scripts in `k8s/chaos/` |
| LLM | OpenAI GPT-4 Turbo + Anthropic Claude 3 Sonnet via Python SDK |
| Evaluation | Custom Python framework in `eval/` |
| CI | GitHub Actions — lint + test + eval on every push |

---

## 6. Data Flow (End to End)

Terraform provisions VPC + EKS cluster

ArgoCD syncs target app + Prometheus + Grafana from Git

Raj runs chaos script → failure injected into cluster

Kubernetes reacts → pods crash / restart / go unready

Prometheus fires named alert (PodCrashLooping, NodeNotReady, etc.)

capture_incident.sh collects:
data/raw_logs/INC-XXX/
metadata.json ← chaos_type, timestamp, ground_truth (set BEFORE LLM)
pod_logs.txt
describe_output.txt
events.txt
metrics_snapshot.json

Soham's rca_engine.py reads INC-XXX folder → sends to LLM → returns LLMOutput JSON

eval/evaluate.py scores: accuracy, hallucination, latency, remediation usefulness

One row appended to data/incidents.csv

GitHub Actions runs evaluate.py on every push to verify nothing breaks

text

---

## 7. Repo Structure

kubernetes-llm-incident-response-benchmark/
├── terraform/
│ └── modules/
│ ├── vpc/
│ ├── eks/
│ └── monitoring/
├── k8s/
│ ├── apps/ ← target app, prometheus, grafana manifests
│ │ └── prometheus/
│ │ └── alert-rules.yaml
│ └── chaos/ ← chaos scripts (Raj owns)
├── ai/
│ ├── rca_engine.py
│ ├── incident_schema.py
│ └── prompts/
├── eval/
│ ├── evaluate.py
│ └── dataset_schema.md
├── data/
│ ├── incidents.csv ← APPEND ONLY. Never overwrite existing rows.
│ └── raw_logs/
│ └── INC-001/
├── docs/
│ ├── context.md ← this file
│ ├── glossary.md
│ ├── benchmark.md
│ ├── adr/ ← ADR-001 through ADR-007+
│ └── runbooks/ ← one file per chaos type
├── notebooks/ ← Soham's Jupyter analysis
├── .github/
│ └── workflows/
│ └── ci.yml
├── Makefile ← make deploy | make chaos | make eval
├── CONTRIBUTING.md
└── README.md

text

---

## 8. Non-Negotiables

- `main` is always deployable — no broken code ever merges
- CI must be green before any PR merges to main
- Nothing applied to the cluster manually — ArgoCD or Terraform only
- No secrets in Git — AWS via IAM roles, API keys via environment variables only
- Every chaos run = one committed `INC-XXX/` folder + one CSV row — not "done" until logged
- Ground truth in `metadata.json` is set BEFORE the LLM call — never after
- `latest` image tag is forbidden — always pin to a specific version
- Every new chaos type = matching Prometheus alert rule + runbook before it counts as complete

---

## 9. Chaos Scenario Library

### Pod-Level
- `pod_kill_random` — kill random pod in namespace
- `pod_crash_loop` — trigger CrashLoopBackOff via bad image tag
- `pod_oom_kill` — force OOMKilled via memory stress
- `pod_image_pull_error` — invalid image tag

### Network-Level
- `network_latency_500ms` — 500ms delay on service
- `network_latency_2000ms` — 2s delay
- `network_packet_loss_30pct` — 30% packet loss
- `network_dns_failure` — DNS resolution failure

### Node-Level
- `node_drain` — cordon + drain node
- `node_terminate` — terminate EC2 instance

### Resource-Level
- `cpu_stress_80pct` — CPU stress to 80%
- `memory_leak_slow` — gradual memory leak
- `disk_fill_90pct` — fill disk to 90%
- `etcd_stress` — etcd under high write load

### Cascade (Day 8+)
- `cascade_pod_then_node`
- `cascade_network_then_oom`
- `multi_service_failure`

---

## 10. Evaluation Metrics

| Metric | Description | Type |
|---|---|---|
| RCA Accuracy | LLM category vs ground truth category | 0 or 1 |
| Hallucination Rate | LLM cited evidence not present in input | 0 or 1 per incident |
| Response Latency | Time from prompt send to response received (ms) | Float |
| Remediation Usefulness | Would the suggested fix work on a live cluster | Y / N / Partial |
| Cost per Experiment | AWS infra cost + LLM API token cost | USD Float |

---

## 11. Incident Data Schema

Each incident folder (`data/raw_logs/INC-XXX/`) contains:
- `metadata.json` — `incident_id`, `date`, `chaos_type`, `chaos_scenario`, `ground_truth_category`, `actual_root_cause`
- `pod_logs.txt` — last 200 lines of affected pod logs
- `describe_output.txt` — `kubectl describe pod` output
- `events.txt` — `kubectl get events --sort-by=.lastTimestamp` output
- `metrics_snapshot.json` — Prometheus query results at T+2min of chaos

Each row in `data/incidents.csv` contains:
`incident_id`, `date`, `run_by`, `chaos_type`, `chaos_scenario`, `llm_model`,
`actual_root_cause`, `llm_predicted_cause`, `llm_predicted_category`,
`rca_accurate`, `hallucination_detected`, `hallucination_detail`,
`response_latency_ms`, `remediation_useful`, `cost_usd`, `notes`

---

## 12. Sprint Structure (Phases, Not Fixed Days)

**Phase 1 — Build** (5 milestones): Foundation → Integration → Observability → First Chaos → First 10 Experiments + Publish
**Phase 2 — Scale** (5 milestones): Signal Injection → Advanced Chaos → Model Comparison → 50 Experiments → Full Benchmark Doc
**Phase 3 — Convert** (4 milestones): Polish → Interview Prep → Applications → Close the Loop

Phases can compress — Raj and Soham can complete 2-3 milestones in one day if gates are met.
**Fast Forward rule:** Whenever both people finish a milestone gate early, immediately run one
end-to-end chaos → capture → LLM → score → CSV loop together.

---

## 13. For Any AI Assistant Reading This

- Raj knows Kubernetes, AWS, CI/CD at an advanced level. Skip basics with him.
- Soham needs short infra explanations but handles code and AI details fast.
- Always give working code or config first, explanation second.
- When designing anything, ask: does this produce a row in incidents.csv? If not, is it strictly necessary?
- Reality > theory. Rough but working > perfect but imaginary.
- Reference this file as ground truth. If something contradicts it, flag the conflict — don't silently pick one.