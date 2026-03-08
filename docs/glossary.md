# Glossary — Kubernetes LLM Incident Benchmark

Every technical term used in this project, explained in plain language.
Maintained by: Raj + Soham | Location: `docs/glossary.md`
Rule: Any new jargon added to any doc in this repo must be added here too.

---

## A

### ADR (Architecture Decision Record)
A short document that records WHY a technical decision was made.
Format: what was decided, what alternatives were rejected, what the trade-offs are.
Location in this project: `docs/adr/ADR-001.md` through `docs/adr/ADR-007.md` and growing.
Who maintains it: Both Raj and Soham. Every major decision gets one.

### Alert Rule (Prometheus)
A condition written in PromQL that fires a named alert when a metric crosses a threshold.
Example: "If pod restart count increases more than 3 times in 5 minutes → fire alert `PodCrashLooping`."
Location: `k8s/apps/prometheus/alert-rules.yaml`
Rule in this project: Every new chaos scenario must have a matching alert rule before it counts as complete.

### Alertmanager
A component that receives alerts from Prometheus and routes them — to Slack, email, webhook, or your pipeline.
In this project: Alertmanager routes alerts into the incident capture pipeline so the LLM receives them as input.

### Ansible
An open-source IT configuration management and automation platform.
In this project: Used to configure namespaces, RBAC, and compute quotas on the cluster post-Terraform.
Owner: Pranav.

### Ansible Playbook
A YAML file containing a series of tasks to be executed sequentially on specified hosts.
In this project: Found in `ansible/playbooks/`, describing the high-level configuration goals for the cluster.
Owner: Pranav.

### Ansible Role
A mechanism to break a playbook into multiple files to simplify writing complex playbooks, making them easier to reuse.
In this project: Found in `ansible/roles/`, managing individual domains like namespaces or RBAC.
Owner: Pranav.

### ArgoCD
A GitOps tool that watches your GitHub repo and automatically applies Kubernetes manifests to your cluster.
In plain English: Git is the source of truth. ArgoCD makes the cluster match Git.
Rule: No `kubectl apply` manually. All changes go through ArgoCD.
Different from Argo Workflows (see below).

### Argo Workflows
A separate tool from ArgoCD. It orchestrates multi-step jobs as Kubernetes pods — like a pipeline engine inside the cluster.
In this project: Planned as a stretch goal for auto-remediation (Phase 2+). Not in core build.

---

## B

### Benchmark
A standardized test that produces measurable, comparable results.
In this project: You are running 50 chaos experiments, scoring LLM responses against ground truth, and publishing the results as a dataset. That dataset + scoring methodology = the benchmark.
What makes it real: It is reproducible. Anyone can clone the repo and run the same experiments.

### Branch (Git)
An isolated copy of the codebase where you make changes without affecting `main`.
Rule: Always work on a branch. Never commit directly to `main`.
Naming convention: `feat/`, `infra/`, `chaos/`, `eval/`, `docs/` prefix.
Example: `git checkout -b infra/eks-node-groups`

---

## C

### Cascade Failure
When one failure causes another failure, which causes another — a chain reaction.
Example: Network latency → service timeout → pod restarts → OOM kill → node pressure.
In this project: Cascade chaos scenarios are in the Day 8+ advanced library.

### Chaos Engineering
The practice of intentionally breaking things in a controlled, safe environment to discover weaknesses before real users are affected.
You inject failures, observe how the system reacts, and improve its resilience.
Origin: Netflix invented this with "Chaos Monkey" — randomly killing production servers to force engineers to build resilient systems.
In this project: Raj runs chaos scripts against the EKS cluster. Each run is one experiment.

### Chaos Experiment
One specific, defined test. Includes:
- A named scenario (e.g., `pod_kill_random`)
- A script that triggers it
- An expected system reaction
- A matching Prometheus alert
- A runbook

### Chaos Scenario
A reusable, named failure type in your scenario library.
Examples: `pod_kill_random`, `network_latency_2000ms`, `node_drain`, `cpu_stress_80pct`.
Location: `k8s/chaos/` scripts + `docs/runbooks/`.

### checkov
A static code analysis tool for Infrastructure as Code and Kubernetes manifests.
In this project: Scans the `k8s/` manifests for misconfigurations and security issues.
Owner: Pranav.

### CI/CD (Continuous Integration / Continuous Deployment)
- **CI**: Every time code is pushed, automated tests and checks run immediately.
- **CD**: Passing code is automatically deployed to the target environment.
In this project: GitHub Actions is the CI. ArgoCD is the CD.
Soham owns the GitHub Actions CI pipeline.

### Cost Explorer (AWS)
A tool that enables you to view and analyze your AWS costs and usage explicitly.
In this project: Pranav tracks the EKS and AWS utilization against API token costs for the benchmarking metrics.
Owner: Pranav.

### CrashLoopBackOff
A Kubernetes pod state meaning: "the container keeps starting, crashing, and restarting in a loop."
Kubernetes adds increasing delays between restarts (backoff) to prevent resource waste.
Common causes: app bug, missing environment variable, bad config, OOM kill.
How to detect: `kubectl get pods` shows `CrashLoopBackOff` in STATUS column.

### CSV (incidents.csv)
Your primary dataset file. One row per chaos experiment.
Location: `data/incidents.csv`
Sacred rule: APPEND ONLY. Never modify or delete existing rows. Scripts append. Humans never edit manually.

---

## D

### Dataset
A structured collection of data points used for analysis.
In this project: `data/incidents.csv` is your dataset — 50 rows, one per experiment, with ground truth and LLM scores.
Why it matters: Publishing a real dataset is what makes this a benchmark, not just a demo.

### Deployment (Kubernetes)
A Kubernetes object that manages running a set of identical pods.
It handles: how many replicas to run, what container image to use, how to roll out updates, how to restart crashed pods.
Example: "Run 2 replicas of the target HTTP service. If one crashes, restart it."

### describe (kubectl describe)
A kubectl command that shows detailed information about a Kubernetes object.
Example: `kubectl describe pod my-pod-abc123`
Output includes: events, resource requests/limits, container state, restart count, recent error messages.
In this project: `describe_output.txt` in each incident folder is the output of this command — it's part of what the LLM reads.

### DORA Metrics
Four metrics used industry-wide to measure DevOps team performance:
1. **Deployment Frequency** — how often you deploy
2. **Lead Time for Changes** — time from commit to production
3. **Change Failure Rate** — % of deployments that cause incidents
4. **MTTR (Mean Time to Recovery)** — how fast you recover from failures
In this project: your benchmark directly measures AI's impact on MTTR and incident resolution quality.

---

## E

### EKS (Elastic Kubernetes Service)
AWS's managed Kubernetes service. AWS handles the control plane (the Kubernetes master). You manage the worker nodes.
Why you use it: Raj already has EKS experience. It integrates natively with AWS IAM, VPC, and Cost Explorer.
Node type in this project: t3.medium × 3 nodes.

### EOD Gate (End-Of-Day Gate)
A non-negotiable checkpoint. The defined condition that must be true before moving to the next phase.
Example: "EOD Gate for Foundation phase: `terraform plan` runs clean + repo structure is committed."
Not literally "end of day" — it means "this milestone is not done until these conditions are true."

### Evaluation Framework
The set of scripts and logic that score LLM responses against ground truth.
Location: `eval/evaluate.py` + scoring functions.
Owner: Soham.
Outputs: Scores written to `data/incidents.csv` — accuracy, hallucination, latency, remediation usefulness.

### Events (Kubernetes Events)
A stream of timestamped messages Kubernetes generates as things happen in the cluster.
Example events: "Pod scheduled to node X", "Container OOMKilled", "Failed to pull image".
How to get them: `kubectl get events --sort-by=.lastTimestamp`
In this project: `events.txt` in each incident folder — key evidence for the LLM.

---

## F

### Feature Branch
A Git branch created specifically for one piece of work.
Naming: `feat/add-hallucination-scorer`, `infra/eks-autoscaling`, `chaos/network-latency`.
Rule: Every task gets its own branch. Merge to `main` only via PR.

---

## G

### GitOps
A practice where Git is the single source of truth for all infrastructure and application configuration.
Changes follow this path: `Git commit → PR → review → merge → ArgoCD applies to cluster`.
Rule in this project: No manual cluster changes. Everything in Git.

### Grafana
A dashboarding tool that visualizes metrics from Prometheus.
In this project: Grafana shows live pod CPU/memory, chaos impact, and benchmark results.
Namespace: `monitoring`.

### Ground Truth
The actual correct answer — known because YOU created the incident.
Set in `metadata.json` BEFORE the LLM is called. Never changed after.
Example: `"actual_root_cause": "Container OOMKilled due to memory limit of 64Mi being too low"`.
Why it matters: Without ground truth, you cannot score the LLM's answer.

---

## H

### Hallucination (LLM)
When an LLM states something confidently that is not supported by the input data — or is factually wrong.
In this project:
- LLM mentions a pod name that does not appear anywhere in the input logs.
- LLM says "alert PodOOMKilled fired" but that alert is not in the input.
- LLM invents a metric value that was never captured.
Scored by: `hallucination_detected` (Y/N) and `hallucination_detail` fields in `incidents.csv`.

### Helm Chart
A package format for Kubernetes that bundles multiple templated YAML manifests together.
In this project: Used to install standard tools (Prometheus, Grafana). Custom application configurations might be packaged later.
Owner: Pranav.

### HPA (Horizontal Pod Autoscaler)
A Kubernetes object that automatically scales the number of pod replicas based on CPU/memory usage.
Example: "When average CPU > 70%, add more pods. When it drops below 30%, remove pods."

---

## I

### IAM (Identity and Access Management)
AWS's permission system. Controls who (users, services, pods) can do what in AWS.
Rule in this project: No hardcoded AWS credentials anywhere. Use IAM roles for all access.

### IaC (Infrastructure as Code)
Managing infrastructure (servers, networks, clusters) using code files instead of clicking in a UI.
Tool in this project: Terraform.
Why: Reproducible, version-controlled, reviewable infrastructure.

### Incident
Something broken or degraded enough that it needs attention.
In this project: Each chaos experiment produces one incident.
The chaos is the cause. The incident is what the system is suffering.

### Incident ID
A unique sequential label like `INC-001`, `INC-002` used to track and reference incidents.
Convention: 3-digit zero-padded number. `INC-001` through `INC-050` for 50 experiments.
Shows up in: folder names, CSV rows, commit messages, runbooks.

### IncidentInput (Schema)
The structured JSON object that Soham's RCA engine sends to the LLM.
Contains: alert JSON, pod logs, describe output, events, metadata.
Location: defined as a Python dataclass in `ai/incident_schema.py`.
Rule: LLM can only use what's in this object — no external knowledge.

---

## K

### kubectl
The command-line tool for interacting with a Kubernetes cluster.
Key commands in this project:
- `kubectl get pods` — list pods and their status
- `kubectl describe pod <name>` — detailed pod info
- `kubectl get events` — cluster events stream
- `kubectl logs <pod>` — container logs
- `kubectl apply -f <file>` — apply a manifest (via ArgoCD only in this project)

---

## L

### LLM (Large Language Model)
An AI model trained on large text datasets that can generate, summarize, and reason about text.
Models in this project: GPT-4 Turbo (OpenAI) and Claude 3 Sonnet (Anthropic).
Role: Given logs, events, and alerts — diagnose the root cause of the Kubernetes incident.

### LLMOutput (Schema)
The structured JSON object the LLM must return.
Fields: `cause`, `category`, `confidence`, `evidence`, `suggested_fix`, `suggested_commands`.
Location: defined in `ai/incident_schema.py`.
Rule: Output must always be valid JSON. Enforced by prompt design and output parsing.

---

## M

### Makefile
A file defining shortcut commands for common project tasks.
Commands in this project:
- `make deploy` — run Terraform + ArgoCD sync
- `make chaos` — run a chaos experiment
- `make eval` — run the evaluation framework

### Manifest (Kubernetes)
A YAML file that defines a Kubernetes object (Deployment, Service, ConfigMap, etc.).
Example: a Deployment manifest says "run 2 replicas of image X with these resource limits."
Location: `k8s/apps/`.

### metrics_snapshot.json
One of the 4 files in every incident folder.
Contains: Prometheus query results captured at T+2 minutes after chaos injection.
Why T+2: Gives Prometheus time to scrape and reflect the failure in metrics.

### MTTR (Mean Time to Recovery)
Average time from when an incident starts to when it is fully resolved.
In this project: One of the metrics the industry cares about that your benchmark speaks to.

---

## N

### Namespace (Kubernetes)
A logical partition inside a Kubernetes cluster. Like folders for your workloads.
Namespaces in this project:
- `default` — target application
- `monitoring` — Prometheus + Grafana
- `argocd` — ArgoCD

### NodeNotReady
A Kubernetes node state meaning the node is unavailable — pods on it cannot be scheduled or run.
Common causes: node terminated, disk pressure, memory pressure, network failure.
In this project: triggered by `node_drain` or `node_terminate` chaos scenarios.

---

## O

### OOMKilled (Out Of Memory Killed)
A container was killed by the Linux kernel because it exceeded its memory limit.
Exit code: 137.
How to detect: `kubectl describe pod` shows `OOMKilled` in last state, or `kubectl get events` shows OOM event.
In this project: triggered by `pod_oom_kill` chaos scenario.

---

## P

### Pod
The smallest deployable unit in Kubernetes. One or more containers running together on the same node.
Think of it as: one instance of your application.
If it crashes: Kubernetes restarts it (up to a limit, then CrashLoopBackOff).

### Prometheus
An open-source monitoring tool that scrapes metrics from Kubernetes and your apps at regular intervals.
In this project: captures CPU, memory, restart counts, network metrics, and fires alerts when thresholds are crossed.
Namespace: `monitoring`.

### PromQL
Prometheus Query Language. Used to write alert rules and Grafana dashboard queries.
Example: `rate(kube_pod_container_status_restarts_total[5m]) > 0` detects recent restarts.

### PR (Pull Request)
A request to merge your feature branch into `main`.
Rule in this project: Every change goes through a PR. No direct pushes to `main`. CI must be green before merge.

### Prompt
The full text sent to the LLM. Includes: instructions, constraints, evidence (logs/events/alerts), and required output format.
Owner: Soham designs all prompts.
Location: `ai/prompts/`.
Key rule: The prompt must instruct the LLM to only use provided evidence — no making things up.

---

## R

### RBAC (Role-Based Access Control)
Method of regulating access to computer or network resources based on the roles of individual users within an enterprise.
In this project: Defines what users and automated tools can do within the EKS cluster.
Owner: Pranav.

### RCA (Root Cause Analysis)
Finding the real underlying reason an incident happened, not just the surface symptom.
Symptom: pod is CrashLoopBackOff.
Direct cause: container keeps exiting.
Root cause: memory limit is too low, container gets OOMKilled every time it starts.
In this project: the LLM performs RCA. The evaluation checks if it found the correct root cause.

### Remediation
The action taken to fix an incident.
In this project: the LLM suggests fix steps and kubectl commands.
Scored by `remediation_useful` (Y / N / Partial) in `incidents.csv`.

### Resource Quota
A constraint that limits aggregate resource consumption per Kubernetes namespace.
In this project: Limits blast radius of experiments and applications.
Owner: Pranav.

### Runbook
A step-by-step guide for handling a specific incident type.
Contents: how to detect it, what to check, common causes, safe fix steps.
Location: `docs/runbooks/<scenario_name>.md`
Rule: Every chaos scenario must have a matching runbook before it counts as complete.

---

## S

### SRE (Site Reliability Engineer)
An engineer who owns the reliability, availability, and performance of production systems.
Their tools: monitoring, alerting, incident response, postmortems, runbooks, chaos engineering.
This project simulates what an SRE does during incident triage — and tests whether an LLM can do it.

---

## T

### Terraform
Infrastructure as Code tool. Defines AWS resources (VPC, EKS, IAM, etc.) in `.tf` files.
Commands:
- `terraform init` — initialize providers
- `terraform plan` — preview changes (no real changes made)
- `terraform apply` — apply changes to AWS
- `terraform destroy` — DELETE everything (never run without explicit confirmation)
Structure in this project: `terraform/modules/vpc/`, `terraform/modules/eks/`, `terraform/modules/monitoring/`.

### tfsec
A static analysis security scanner for Terraform code.
In this project: Runs across the `terraform/` directory checking for IAM policy permissiveness, open ports, and encryption omissions.
Owner: Pranav.

### trivy
A comprehensive and versatile vulnerability scanner for containers and artifacts.
In this project: Scans docker images referenced in the `k8s/apps/` manifesting before deployment.
Owner: Pranav.

---

## V

### VPC (Virtual Private Cloud)
Your isolated private network inside AWS.
Contains: subnets, routing tables, internet gateways, security groups.
In this project: EKS cluster lives inside a VPC Raj defines via Terraform.

---

## W

### Workflow (Antigravity)
An on-demand agent task in Google Antigravity — triggered by name, runs a defined sequence of actions.
Workflows set up for this project:
- `new-chaos-scenario` — scaffolds a new chaos type end to end
- `log-experiment` — creates incident folder + CSV row skeleton
- `write-adr` — creates a formatted ADR file with next sequential number

---

## How to Use This File

1. Save as `docs/glossary.md`
2. Any time a new term appears in any project doc → add it here immediately
3. Format: term as `###`, 2–4 line plain explanation, project-specific context below
4. Who updates it: all members — in the same PR as the doc that introduced the term
