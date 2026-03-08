# Kubernetes LLM Incident Response Benchmark

A benchmark measuring how well Large Language Models (like GPT-4 Turbo and Claude 3 Sonnet) can act as First Responders during Kubernetes production incidents.

## Contributors
- **Raj Patil** — Platform Architect (Terraform, EKS, Chaos Engineering, Prometheus, ArgoCD)
- **Soham** — AI Systems Engineer (LLM Pipeline, Evaluation Framework, CI/CD)
- **Pranav** — Infrastructure Reliability & Security Engineer (Ansible, Security Scanning, Cost Monitoring)

## Project Structure
```
kubernetes-llm-incident-response-benchmark/
├── terraform/          # Infrastructure configurations
├── ansible/            # Cluster configuration playbooks (Pranav owns)
├── security/           # Image and infra security scanners (Pranav owns)
├── k8s/                # Kubernetes manifests
├── ai/                 # Application logic for LLM
├── eval/               # Framework evaluating AI's performance
├── data/               # Raw experiment logs and final dataset (.csv)
└── docs/               # Glossary, Context, and Architecture Decision Records
```
