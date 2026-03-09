# System Architecture — K8s LLM RCA Bench

## 1. Overview
The K8s LLM RCA Benchmark is built on a four-tier architecture: **Infrastructure (Chaos Layer)**, **Telemetry Extraction**, **LLM Inference Engine**, and **Evaluation/Scoring**.

## 2. The RCA Engine Core
The engine (`eval/run_benchmark.py`) orchestrates the diagnostic lifecycle. Unlike standard LLM benchmarks (MMLU, HumanEval), KLRB uses **Causal Ablation** (Conditions A, B, C, D) to distinguish between *actual reasoning* and *prior-based guessing*.

### 2.1 Causal Ablation Framework
| Condition | Input | Purpose |
|---|---|---|
| **A (Full)** | Metadata + Logs + Events | Baseline performance |
| **B (No Logs)**| Metadata + Events | Sensitivity to log data |
| **C (No Context)**| Logs only | Sensitivity to categorical priors |
| **D (Minimal)** | Metadata only | The "Prior Guessing" control |

## 3. Faithfulness Scoring Algorithm
To prevent circular reasoning (where an LLM judges an LLM), we utilize a **Deterministic Deterministic Scorer** (`eval/faithfulness.py`):

$$S_f = w_v \cdot V + w_k \cdot K$$

Where:
- $V \in \{0, 1\}$ is a verbatim line match.
- $K \in \{0, 1\}$ is a technical keyword co-occurrence match.
- Weights are set to $w_v = 1.0, w_k = 0.5$ by default.

## 4. $\Delta$-Decoding: The Causal Fix
The repository includes a novel inference-time wrapper (`eval/delta_decoding.py`) that restores model faithfulness without fine-tuning. It works by subtracting the logit distribution of the "Metadata Only" prompt from the "Full Telemetry" prompt:

$$z_{\Delta} = \text{Softmax}(Logits(Metadata+Logs) - Logits(Metadata))$$

This forces the model to decode tokens that are uniquely supported by the logs, bypassing the **Evidence Invariance** trap.

## 5. Directory Structure Principles
Standardized pathing is enforced across the codebase to ensure reproducibility:
- `data/incidents/`: Canonical test cases (INC-001 to INC-016).
- `infra/`: Reproducible chaos injection scripts (Kind/EKS compatible).
- `results/`: Standardized CSV exports for paper-ready statistics.
- `figures/`: Automated visualization output (matplotlib/seaborn).
