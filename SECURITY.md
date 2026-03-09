# Security Policy

## Supported Versions

Currently, only the `main` branch is actively supported with security updates. We do not maintain historical release lines for security patches at this time.

| Version | Supported          |
| ------- | ------------------ |
| `main`  | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of `k8s-llm-rca-bench` seriously. 

If you discover a security vulnerability within this project—particularly anything related to prompt injection vulnerabilities that could escape the evaluation sandbox, leaked credentials in the dataset, or unsafe code execution pathways in the `evaluate.py` or chaos scripts—please do NOT disclose it publicly until we've had a chance to fix it.

**To report a vulnerability:**

1. Email the project maintainers directly (check commit history for contact information) or open a **Security Advisory** draft on GitHub if the feature is enabled for this repository.
2. Please provide detailed steps to reproduce the vulnerability.
3. Include any potential impact you've identified.

### What to Expect

- We will acknowledge receipt of your vulnerability report within 3 business days.
- We will provide an estimated timeline for a fix and keep you updated on progress.
- Once the vulnerability is resolved, we will publish a security advisory and credit you for the discovery (unless you prefer to remain anonymous).

### Out of Scope

- Vulnerabilities in the upstream LLM platforms (OpenAI, Anthropic, NVIDIA) themselves are out of scope unless our interaction with them explicitly creates a novel vector.
- Vulnerabilities in the Kubernetes core or AWS EKS are out of scope. Please report those directly to the CNCF or AWS.
