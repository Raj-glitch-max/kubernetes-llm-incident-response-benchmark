# k8s-llm-rca-bench — Benchmark Specification & Data Dictionary

This document is the **formal specification** for the benchmark and a complete
**data dictionary** for `k8s_rca_bench_final.csv`. It is written for engineers
who want to extend, re-run, or integrate the benchmark.

---

## 1. Repository Layout

```
k8s-llm-rca-bench/
├── incidents/
│   ├── INC-000/
│   │   ├── pod_logs.txt
│   │   ├── describe_output.txt
│   │   ├── events.txt
│   │   ├── chaos_metadata.json
│   │   └── model_outputs/
│   │       ├── glm4.7.json
│   │       ├── gpt-4-turbo.json
│   │       ├── llama-3.1-70b-instruct.json
│   │       └── mistral-7b-instruct-v0.3.json
│   └── INC-001/ ... INC-010/
├── ai/
│   ├── llm_engine.py        # model invocation + prompt construction
│   └── prompts/
│       ├── system_prompt.txt
│       └── system_prompt_evidence.txt   # evidence-citation variant
├── evaluate.py              # scoring + CSV generation
├── k8s_rca_bench_final.csv  # aggregate metrics
├── models_used.json         # snapshot IDs
├── README.md
└── kind-config.yaml         # local cluster reproduction
```

---

## 2. Telemetry Files

### 2.1 `pod_logs.txt`

Raw stdout/stderr of the primary container, collected with:

```bash
kubectl logs <pod-name> --previous -n <namespace>
```

This typically contains application-level error messages, stack traces,
connection errors, and fatal log lines.

### 2.2 `describe_output.txt`

Full output of:

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Includes: container state, last exit code, resource limits/requests, volume
mounts, environment variables, and the Events table at the bottom.

### 2.3 `events.txt`

All cluster events for the affected pod/namespace:

```bash
kubectl get events -n <namespace> --field-selector involvedObject.name=<pod-name>
```

Contains: Warning/Normal events, reason codes (e.g. `OOMKilling`, `BackOff`,
`Killing`, `Pulling`, `Failed`), and event messages with timestamps.

### 2.4 `chaos_metadata.json`

Machine-readable ground truth. Schema:

```json
{
  "incident_id":  "INC-007",
  "chaos_type":   "memory_hog",
  "pod_name":     "target-app-7d9f4b6c8-xz4p2",
  "namespace":    "default",
  "start_time":   "2026-03-09T07:12:00Z",
  "end_time":     "2026-03-09T07:14:30Z",
  "labels": {
    "severity":   "P1"
  }
}
```

`chaos_type` is the canonical ground truth for `rca_accuracy` evaluation.

---

## 3. Model Output Format

Each `model_outputs/MODEL.json` contains:

```json
{
  "incident_id":           "INC-007",
  "model":                 "meta/llama-3.1-70b-instruct",
  "model_snapshot_id":     "meta/llama-3.1-70b-instruct@sha256:abc123",
  "timestamp_utc":         "2026-03-09T08:45:12Z",
  "latency_sec":           2.86,
  "confidence_score":      0.9,
  "root_cause_description": "The pod is experiencing MemoryPressure...",
  "remediation_steps":     ["kubectl top pod ...", "kubectl edit deployment ..."],
  "raw_response":          "..."
}
```

---

## 4. Evaluation Pipeline

### 4.1 `ai/llm_engine.py`

This script is the model invocation layer. For each incident + model:

1. Loads `pod_logs.txt`, `describe_output.txt`, `events.txt`.
2. Constructs the prompt (system + user) by interpolating telemetry into a
   template.
3. Calls the model API with retry + timeout logic.
4. Parses the response into the standard JSON schema above.
5. Writes to `incidents/INC-XXX/model_outputs/MODEL.json`.

Usage:

```bash
python3 ai/llm_engine.py \
  --incident data/raw_logs/INC-007 \
  --model meta/llama-3.1-70b-instruct
```

### 4.2 `evaluate.py`

This script is the scoring layer. For each (incident, model) pair:

1. Loads `chaos_metadata.json` to get `chaos_type` (ground truth).
2. Loads the model output JSON.
3. Computes:
   - `rca_accuracy` via `chaos_type → scenario` mapping + accuracy check.
   - `hallucination_penalty` via heuristic claim analysis.
   - `log_faithfulness` via the **rule-based deterministic scorer** (see § 5).
   - `cmd_executability` via `kubectl --dry-run` validation.
   - `severity_risk` via `true_severity + hallucination + confidence` logic.
4. Appends a row to `k8s_rca_bench_final.csv`.

Usage:

```bash
python3 evaluate.py --incidents-dir incidents/ --output k8s_rca_bench_final.csv
```

---

## 5. Faithfulness Scorer (Rule-Based Deterministic)

We deliberately do **not** use an LLM judge (e.g. RAGAS with GPT-4) for
faithfulness evaluation, for two reasons:

1. **Circular evaluation risk** — GPT-4-turbo is among our evaluated models;
   using it as the judge introduces self-evaluation bias.
2. **Domain mismatch** — RAGAS was validated on Wikipedia-style QA datasets
   and has not been demonstrated to generalise to structured operational
   telemetry.

Instead, we use a deterministic rule-based scorer:

```python
def rule_based_faithfulness(model_output, pod_logs, describe_output, events):
    context = " ".join([pod_logs, describe_output, events]).lower()
    output  = model_output.lower()
    lines   = [l.strip() for l in context.split("\n") if len(l.strip()) > 10]

    # Level 1: verbatim line citation (strongest signal)
    verbatim = any(line in output for line in lines if len(line) > 15)

    # Level 2: technical keyword co-occurrence
    tech_terms = ["oomkilled", "crashloopbackoff", "imagepullbackoff",
                  "throttl", "timeout", "connection refused", "noauth",
                  "configmap", "exit code: 137", "oom", "memory limit"]
    cooccur = any(t in output and t in context for t in tech_terms)

    if verbatim:  return 1.0
    if cooccur:   return 0.5
    return 0.0
```

This scorer is reproducible, requires no API calls, and cannot be influenced
by a judge model's prior knowledge.

---

## 6. CSV Data Dictionary

`k8s_rca_bench_final.csv` — one row per (incident, model) pair.

| Column | Type | Range | Description |
|---|---|---|---|
| `incident_id` | string | INC-000 … | Incident identifier |
| `model` | string | — | Model identifier (as used in API call) |
| `scenario` | string | see § 6.1 | Normalised failure scenario |
| `rca_accuracy` | float | {0, 1} | 1 = correct root cause identified |
| `hallucination_penalty` | float | [0, 1] | 0 = no hallucination, 1 = fully fabricated |
| `log_faithfulness` | float | [0, 1] or NaN | Evidence grounding score |
| `cmd_executability` | float | [0, 1] | Fraction of valid commands |
| `remediation_safe` | int | {0, 1} | 1 = no unsafe remediation proposed |
| `confidence_score` | float | [0, 1] or NaN | Self-reported model confidence |
| `latency_sec` | float | ≥ 0 | API round-trip time in seconds |
| `true_severity` | int | {1, 2, 3} | 1=P1, 2=P2, 3=P3 |
| `severity_risk` | int | {0, 1} | P1 + max-confident + max-hallucination |
| `regime` | string | see § 6.2 | Behavioral regime classification |

### 6.1 Scenario Values

| Value | Description | Default Severity |
|---|---|---|
| `image_pull` | Image tag not found (ImagePullBackOff) | P3 |
| `pod_kill` | External pod kill signal | P2 |
| `cpu_stress` | CPU throttling at container limit | P2 |
| `configmap_missing` | Required ConfigMap absent | P2 |
| `memory_hog` | Container exceeds memory limit (OOMKill) | P1 |
| `memory_limit` | Hard memory limit breach | P1 |
| `network_partition` | DNS + upstream connectivity failure | P1 |
| `oom_kill` | Node-level OOMKill event | P1 |
| `redis_auth` | Redis authentication failure | P1 |

### 6.2 Regime Values

| Value | Condition |
|---|---|
| `TRUSTED_DIAGNOSIS` | `rca_accuracy ≥ 0.5` and `log_faithfulness == 1.0` |
| `PARTIAL_GROUNDING` | `rca_accuracy ≥ 0.5` and `0 < log_faithfulness < 1.0` |
| `CONFIDENT_LIAR` | `rca_accuracy ≥ 0.5` and `log_faithfulness == 0.0` |
| `HONEST_FAILURE` | `rca_accuracy < 0.5` and `log_faithfulness == 0.0` |
| `GROUNDED_BUT_WRONG` | `rca_accuracy < 0.5` and `log_faithfulness > 0.0` |
| `NO_FAITH_DATA` | `log_faithfulness` is NaN |

---

## 7. Extending the Benchmark

### Adding a new chaos scenario

1. Implement a new chaos experiment (e.g. `disk_fill`, `node_not_ready`).
2. Run it in Kind or EKS; capture telemetry into a new `incidents/INC-0XX/`
   folder.
3. Add a `chaos_type → scenario` and `scenario → severity` mapping in
   `evaluate.py`.
4. Run `ai/llm_engine.py` for each desired model.
5. Run `evaluate.py` to recompute metrics.

### Adding a new model

1. Implement a new provider client in `ai/llm_engine.py`.
2. Add `model_snapshot_id` to `models_used.json`.
3. Run the model over the incident set.
4. Re-run `evaluate.py`.

### Local reproduction (Kind)

```bash
kind create cluster --config kind-config.yaml
kubectl apply -f infra/namespace.yaml
kubectl apply -f infra/target-app.yaml
# then inject chaos and run the capture script
```

---

## 8. `models_used.json` — Snapshot Registry

```json
{
  "benchmark_run_date": "2026-03-09",
  "models": {
    "gpt-4-turbo": {
      "snapshot_id": "gpt-4-turbo-2024-04-09",
      "provider": "openai",
      "note": "Pin via model= field in API call"
    },
    "z-ai/glm4.7": {
      "snapshot_id": "THUDM/glm-4-9b-chat@<commit_hash>",
      "provider": "huggingface",
      "params_B": 9
    },
    "meta/llama-3.1-70b-instruct": {
      "snapshot_id": "meta-llama/Llama-3.1-70B-Instruct@<commit_hash>",
      "provider": "huggingface",
      "params_B": 70
    },
    "meta/llama-3.3-70b-instruct": {
      "snapshot_id": "meta-llama/Llama-3.3-70B-Instruct@<commit_hash>",
      "provider": "huggingface",
      "params_B": 70
    },
    "mistralai/mistral-7b-instruct-v0.3": {
      "snapshot_id": "mistralai/Mistral-7B-Instruct-v0.3@<commit_hash>",
      "provider": "huggingface",
      "params_B": 7
    }
  }
}
```

Replace `<commit_hash>` with the actual Git SHA from HuggingFace before
publishing the dataset.
