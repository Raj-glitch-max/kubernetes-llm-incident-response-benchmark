# Contributing to k8s-llm-rca-bench

First off, thank you for considering contributing to the Kubernetes LLM Incident Response Benchmark! It's people like you that make this tool better for the entire DevOps and SRE community.

We welcome all contributions, big or small. Whether it's adding a new chaos scenario, evaluating a new LLM, fixing a typo, or improving documentation, your help is appreciated.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
  - [Evaluating a New LLM](#evaluating-a-new-llm)
  - [Adding a New Chaos Scenario](#adding-a-new-chaos-scenario)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
- [Pull Request Process](#pull-request-process)
- [Development Workflow](#development-workflow)

---

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

---

## Getting Started

To get started with local development:

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/kubernetes-llm-incident-response-benchmark.git
   cd kubernetes-llm-incident-response-benchmark
   ```
3. **Set up the environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Copy the environment template**:
   ```bash
   cp .env.example .env
   # Add your API keys to .env
   ```

---

## How to Contribute

### Evaluating a New LLM

We actively welcome adding new models to the benchmark leaderboard.

1. Ensure the model is accessible via an API (OpenAI, Anthropic, or NVIDIA NIM preferred for standardization).
2. Register the specific, pinned model version in `data/models_used.json`. **Do not use rolling tags (like `gpt-4` or `llama-3-latest`)**. Pin to a specific snapshot id (e.g., `gpt-4-turbo-2024-04-09`) to guarantee reproducibility.
3. Update `ai/llm_engine.py` to route API calls to your new model if it requires a custom payload.
4. Run the benchmark across all incidents:
   ```bash
   python3 ai/llm_engine.py --incident all --model your-new-model
   ```
5. Do NOT manually edit `data/incidents.csv`. Commits that manually alter the dataset rows will be rejected.
6. Submit a PR!

### Adding a New Chaos Scenario

Expanding the dataset is highly encouraged. See `docs/new-reserach/benchmark_spec.md` for full technical details.

1. **Write the Chaos Script**: Create a bash script mapping to the failure mode in `k8s/chaos/`.
2. **Add Prometheus Rule**: Add a corresponding alert rule in `k8s/apps/prometheus/alert-rules.yaml`.
3. **Run the Experiment**: Execute the chaos against a live cluster and capture the telemetry in a new `data/raw_logs/INC-XXX` directory.
   - You MUST include exactly 4 files: `metadata.json`, `events.txt`, `pod_logs.txt`, and `describe_output.txt`.
   - The `metadata.json` establishes the ground truth BEFORE LLM evaluation.
4. After creating the incident, run the suite of existing models against it to populate the baseline data.

### Reporting Bugs

We use GitHub Issues to track bugs. When reporting a bug, please include:

- A clear, descriptive title.
- The exact steps to reproduce the issue.
- Expected vs. actual behavior.
- Details about your environment (OS, Python version, Kubernetes flavor if relevant).

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub Issues. Please provide:
- A clear description of the proposed enhancement.
- The problem it solves or the value it adds.
- Any potential alternatives you've considered.

---

## Pull Request Process

1. Ensure any changes or new data conform to the schemas defined in `ai/incident_schema.py`.
2. Do NOT alter historical data rows in `data/incidents.csv`. The dataset is append-only.
3. Update relevant documentation (`README.md`, docs folder) if your PR introduces new features or structural changes.
4. Ensure your PR description clearly outlines the problem and the solution.
5. A maintainer will review your PR. You may be asked to make changes before it can be merged.

## Development Workflow

- **Branching**: Create a feature branch from `main` (e.g., `feature/add-mistral-8x22b` or `fix/json-parsing`).
- **Committing**: Write clear, concise commit messages.
- **Testing**: While we don't currently mandate full unit test coverage, ensure new scripts run cleanly without throwing tracebacks on standard inputs.

Thank you for contributing!
