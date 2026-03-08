# Running a Benchmark Session

This document outlines the standard operating procedure for running a chaos engineering simulation and evaluating the LLMs (GPT-4 Turbo & Claude 3 Sonnet).

## Prerequisites
1. **Infrastructure**: AWS EKS cluster provisioned via Terraform (`make deploy`).
2. **Setup**: ArgoCD synced and Target Application deployed into the `default` namespace.
3. **Environment**: Ensure `.env` contains:
   - `OPENAI_API_KEY`
   - `ANTHROPIC_API_KEY`

## Step 1: Inject Chaos
Run the designated chaos module to break the target application.
```bash
make chaos
```
*Select a scenario (e.g., `pod_kill`, `crash_loop`, or `oom_kill`).*

## Step 2: Capture Evidence
Once Prometheus fires an alert, capture the cluster state.
```bash
./capture_incident.sh <INC-ID> <ChaosType> <GroundTruth>
# Example: ./capture_incident.sh INC-001 pod_kill PodCrashLooping
```
This extracts logs, described output, and events into `data/raw_logs/INC-XXX`.

## Step 3: Run Evaluation
Trigger the Python evaluation suite.
```bash
make eval
```
The framework orchestrates the LLMs, parses their JSON outputs against the `INC-XXX` logs, scores the results, and appends the final telemetry to `data/incidents.csv`.
