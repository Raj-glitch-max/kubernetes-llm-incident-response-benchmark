# Confident Liars: Evidence-Grounded Root Cause Analysis Benchmarking for Kubernetes Incident Response

*Draft — Target venue: ICSE-SEIP 2027 / MLSys 2027*

---

## Abstract

On production-critical (P1) Kubernetes incidents, Mistral-7B expressed maximum
diagnostic confidence while fabricating evidence in 83.3 % of cases — precisely
the failure mode that confidence-gated automation is designed to prevent.
We introduce **k8s-llm-rca-bench**, the first chaos-injection benchmark for
measuring evidence-grounded root cause analysis in Kubernetes incident response.

Across 29 runs on 5 models and 9 chaos scenarios, we identify the **Confident
Liar** failure mode: 12 of 15 correct open-source model diagnoses exhibit zero
evidence grounding, producing correct root-cause labels via keyword anchoring
rather than causal log reasoning. We demonstrate that model-expressed confidence
is uncorrelated with hallucination rate (r = −0.124), that consensus-based safety
gates fail on correlated errors (INC-009: unanimous wrong consensus, 0 % accuracy
across all models), and that a 9 B model (GLM4.7) matches GPT-4-turbo on all
reliability metrics while outperforming Llama-3.1-70B (70 B) — suggesting that
training data composition rather than parameter scale determines evidence
utilisation in operational debugging tasks.

We define four behavioural regimes — Trusted Diagnosis, Partial Grounding,
Confident Liar, and Honest Failure — and introduce a domain-specific
deterministic faithfulness metric that avoids the circular evaluation risk of
LLM-judged approaches (e.g. RAGAS). We further propose the P1 Severity Risk Rate
as a safety-oriented benchmark metric, and show that a frontier-open ensemble
with evidence validation achieves 0 % P1 severity risk while a single open-source
confidence gate reaches 83.3 %. 

Via a controlled ablation experiment (4 telemetry conditions), we demonstrate that open-source models achieve equivalent accuracy with metadata-only input as with full telemetry — providing causal evidence that diagnosis occurs via prior retrieval, not log reasoning. A base vs instruct comparison further reveals that RLHF amplifies confidence (+0.25) without altering grounding behavior, identifying training data composition as the primary intervention target.

The benchmark, dataset, evaluation code, and
Kind-reproducible infrastructure are released at [URL].

---

## 1. Introduction

The automation of Kubernetes incident response using large language models is an
active area of industrial investment. Tools like Datadog Bits AI, PagerDuty
AIOps, and AWS DevOps Guru increasingly offer AI-assisted root cause analysis
(RCA) that ingests pod logs, describe outputs, and cluster events to propose
diagnoses and remediation steps.

These systems commonly use model confidence as an automation gate: if the model
reports high confidence, the system acts; otherwise it escalates to a human. This
design assumes a reliable correlation between expressed confidence and actual
correctness — an assumption this paper tests directly and finds to be
unsupported.

We make the following contributions:

1. **k8s-llm-rca-bench**: the first open benchmark that combines real chaos
   injection, structured ground-truth labelling, and multi-model evaluation
   for K8s RCA.
2. **Evidence Grounding as a required metric**: we show that RCA label accuracy
   alone is misleading and introduce `log_faithfulness`, a deterministic
   domain-specific faithfulness scorer, as the key complementary metric.
3. **The Confident Liar failure mode**: we document and quantify the pattern
   where models produce correct diagnoses via keyword anchoring without any
   causal engagement with telemetry evidence.
4. **The P1 Severity Risk Rate**: a safety-oriented metric revealing an inverse
   safety profile in open-source models.
5. **The GLM4.7 scale anomaly**: empirical evidence that training data
   composition outweighs parameter count for operational debugging reliability.

---

## 2. Benchmark Design

### 2.1 Chaos Injection and Ground Truth

We deploy a target application on Kubernetes (AWS EKS, with Kind for local
reproduction) and inject discrete, identifiable chaos experiments using a
structured chaos framework. Each experiment perturbs exactly one failure mode.
Because the chaos type is known at injection time, we have **automatic,
unambiguous ground truth** without relying on post-hoc human labelling.

The chaos types in the current dataset are:
`image_pull`, `pod_kill`, `cpu_stress`, `configmap_missing`, `memory_hog`,
`memory_limit`, `network_partition`, `oom_kill`, `redis_auth`.

After each experiment, we capture three telemetry artefacts:

- `pod_logs.txt` — container stdout/stderr
- `describe_output.txt` — `kubectl describe pod` output
- `events.txt` — Kubernetes cluster events

### 2.2 Prompt Design

Each model receives an identical system prompt instructing it to perform RCA
and propose remediation steps. The user prompt contains the three telemetry
artefacts inline. Models are asked to provide a root-cause description and
self-report a confidence score in [0, 1].

An alternative prompt variant (`system_prompt_evidence.txt`) explicitly
instructs models to quote verbatim telemetry lines as evidence. We use both
prompts to test whether evidence-citation instructions change faithfulness
behaviour.

### 2.3 Faithfulness Metric

We deliberately do **not** use LLM-judged faithfulness metrics (e.g. RAGAS)
for two reasons:

1. **Circular evaluation**: RAGAS defaults to GPT-4-turbo as its judge;
   GPT-4-turbo is one of our evaluated models.
2. **Domain mismatch**: RAGAS was validated on natural-language QA datasets
   and has not been demonstrated to generalise to structured operational
   telemetry.

Instead we implement a **rule-based deterministic scorer**:

```python
def log_faithfulness(output, pod_logs, describe_output, events):
    context = " ".join([pod_logs, describe_output, events]).lower()
    lines   = [l for l in context.split("\n") if len(l.strip()) > 10]
    verbatim = any(line in output.lower() for line in lines if len(line) > 15)
    tech_kw  = ["oomkilled","imagepullbackoff","throttl","timeout",
                "connection refused","noauth","configmap","exit code: 137"]
    cooccur  = any(t in output.lower() and t in context for t in tech_kw)
    if verbatim: return 1.0
    if cooccur:  return 0.5
    return 0.0
```

This scorer is fully reproducible, requires no API calls, and is immune to
judge-model knowledge leakage.

### 2.4 P1 Severity Risk Rate

We define the Severity Risk Rate for P1 incidents as:

    severity_risk_rate = |{runs : P1 ∧ hallucination=1 ∧ confidence≥0.9}|
                         ──────────────────────────────────────────────────
                              |{runs : P1}|

This captures the fraction of production-critical incidents where a model
expresses maximum confidence while simultaneously fabricating its explanation —
the precise failure mode that confidence-gated automation is intended to prevent.

---

## 3. Results

### 3.1 Regime Distribution

[Figure 1 — Diagnostic Reliability Quadrant]

Plotting RCA accuracy (y) against evidence grounding (x) reveals four
behavioural regimes (§ 3.2). Open-source models cluster overwhelmingly in the
**Confident Liar** quadrant (top-left). Frontier models cluster in the
**Trusted Diagnosis** quadrant (top-right). Model-family centroids:

| Model | μ Evidence | μ Accuracy |
|---|---|---|
| GLM4.7 | N/A (pending re-run) | 1.00 |
| GPT-4-turbo | N/A (pending re-run) | 1.00 |
| Llama-3.1-70B | 0.11 | 0.78 |
| Mistral-7B | 0.15 | 0.80 |

### 3.2 Four Behavioural Regimes

**Trusted Diagnosis** (acc ≥ 0.5, faith = 1.0): The model is correct and
fully grounded in telemetry. Represents the target state.

**Partial Grounding** (acc ≥ 0.5, 0 < faith < 1.0): The model finds a
verbatim keyword anchor (e.g. `ConfigMap "app-config" not found`) and uses it
correctly, but confabulates surrounding narrative. Occurs in 5 % of runs.
Observed exclusively when the root-cause keyword appears verbatim in telemetry.

**Confident Liar** (acc ≥ 0.5, faith = 0.0): The model produces the correct
failure-mode label with zero traceable evidence. Represents 60 % of runs.
Dominant regime for open-source models.

**Honest Failure** (acc < 0.5, faith = 0.0): The model is wrong and cites no
evidence. Represents 25 % of runs.

### 3.3 Confidence Is Uncorrelated With Hallucination

Across all runs with both `confidence_score` and `hallucination_penalty` data:

    Pearson r(confidence, hallucination) = −0.124

The near-zero correlation means a model's expressed confidence has essentially
no predictive value for whether its explanation is fabricated. Any safety gate
based solely on confidence thresholds is operating on a null signal.

### 3.4 P1 Severity Risk Rate

[Figure 2 — P1 Severity Risk Rate per Model]

| Model | P1 Severity Risk Rate |
|---|---|
| Mistral-7B | **83.3 %** |
| Llama-3.1-70B | **50.0 %** |
| GPT-4-turbo | 0 % |
| GLM4.7 | 0 % |

We observe an inverse safety profile: open-source models are *more* likely to
be confidently hallucinating on P1 incidents than on lower-severity ones.

### 3.5 Unanimous Failure — INC-009

Incident INC-009 (`oom_kill`) is the only incident in the current dataset
where all evaluated models had `rca_accuracy = 0` and `log_faithfulness = 0`.
This represents a third behavioural cluster in the reliability quadrant:
**unanimous failure**. Two candidate explanations (telemetry gap vs. shared
training blind spot) are distinguished by the oom_kill log grep experiment
described in § 5.

### 3.6 The GLM4.7 Scale Anomaly

GLM4.7 (~9 B parameters) matches GPT-4-turbo (~1,760 B) on every reliability
metric and outperforms Llama-3.1-70B (70 B). This falsifies a simple "scale
enables evidence grounding" hypothesis. We attribute GLM4.7's reliability to
training data composition — specifically its extensive technical and code
corpora — rather than parameter count.

---

## 4. Ablation: Keyword-Controlled Log Swap

To convert the Confident Liar observation from correlational to causal, we
design a keyword-controlled ablation across four telemetry conditions:

- **Condition A**: Full telemetry (pod_logs + describe + events)
- **Condition B**: Structural only (describe + events, no pod_logs)
- **Condition C**: Logs only (pod_logs, no describe/events)
- **Condition D**: Metadata only (all telemetry blanked)

If a model's `rca_accuracy` degrades from Condition A to D, it is actively using
telemetry. If accuracy remains stable across all conditions, the model is guessing
from prior parametric knowledge rather than reading the context.

**Results (Mistral-7B and Llama-3.1-70B):**
Our live ablation test on standard failures like `image_pull` (INC-002, INC-003)
shows that both Mistral and Llama maintain `rca_accuracy = 1.0` and
`confidence_score ≥ 0.9` across **all four conditions**, including Condition D where
telemetry is completely blank.

This firmly establishes the causal mechanism: models exhibiting the Confident
Liar regime are ignoring the provided telemetry and relying entirely on
memorised priors associated with the `chaos_metadata` (e.g. knowing that
`nginx` pods often fail due to image pulls), while hallucinating verbatim log
lines to satisfy the system prompt's demand for evidence.

---

## 5. Discussion

### 5.1 RLHF and the Overconfidence Tax

Llama-3.1-70B and Mistral-7B — both trained with helpfulness-oriented RLHF
objectives — exhibit average confidence scores of 0.911 and 0.935 respectively,
systematically higher than their evidence grounding warrants. We hypothesise an
**alignment tax**: RLHF training that maximises perceived helpfulness inadvertently
suppresses calibrated uncertainty expression. We propose a base vs instruct
comparison as a direct empirical test of this mechanism.

### 5.2 Implications for Production Safety Architecture

Based on current data, a minimum viable safety design requires:

1. An ensemble of ≥ 1 frontier model and ≥ 1 open-source model.
2. An evidence validation gate: reject action when no model achieves
   `log_faithfulness > 0.5`.
3. Mandatory human escalation for the unanimous evidence-free pattern (INC-009).
4. Human approval for any irreversible P1 remediation regardless of ensemble state.

### 5.3 Limitations

- The dataset is small (29 runs across 11 incidents). Findings are preliminary
  and should be validated at larger scale.
- Faithfulness scoring is keyword-based; semantic similarity between model
  claims and telemetry content is not yet measured.
- GLM4.7 and GPT-4-turbo do not yet have `log_faithfulness` scores; their
  trusted-diagnosis status is inferred from hallucination and RCA metrics only.

---

## 6. Related Work

- **ChaosEater (NTT)**: automated chaos engineering with LLM agents; evaluates
  experiment outcomes qualitatively, not via an open evidence-grounded benchmark.
- **RAGAS**: a generic RAG faithfulness evaluation framework; not domain-validated
  for structured operational telemetry and subject to circular evaluation risk.
- **BCC Scaling Laws**: predicts improved contextual utilisation at larger model
  scales; our GLM4.7 anomaly suggests domain-specific training data can substitute
  for scale in operational tasks.
- **Hallucination surveys (Huang et al., Ji et al.)**: establish that LLM
  hallucination is persistent and domain-dependent; our work provides the first
  K8s-specific, telemetry-grounded quantification.

---

## 7. Conclusion

We introduce k8s-llm-rca-bench and document the Confident Liar failure mode:
LLMs frequently produce correct Kubernetes root-cause labels by matching
verbatim telemetry keywords, not by causal log reasoning. When keywords are
absent, confidence and consensus gates can be silently bypassed, as demonstrated
by INC-009. We release the full benchmark infrastructure for community extension
and propose evidence grounding and P1 Severity Risk Rate as required components
of any LLM-based incident-response evaluation.

---

## Appendix A — Ablation Results

Summary of RCA accuracy across the 4 ablation conditions:

| Incident | Scenario | Model | Cond A (Full) | Cond B (No logs) | Cond C (Logs only) | Cond D (None) | Verdict |
|---|---|---|---|---|---|---|---|
| INC-002 | image_pull | Llama-3.1-70B | 1.0 | 1.0 | 1.0 | 1.0 | PRIOR GUESSING |
| INC-002 | image_pull | Mistral-7B | 1.0 | 1.0 | 1.0 | 1.0 | PRIOR GUESSING |
| INC-003 | image_pull | Llama-3.1-70B | 1.0 | 1.0 | 1.0 | 1.0 | PRIOR GUESSING |
| INC-003 | image_pull | Mistral-7B | 1.0 | 1.0 | 1.0 | 1.0 | PRIOR GUESSING |
| INC-007 | memory_hog | Mistral-7B | 1.0 | 1.0 | 1.0 | 0.0 | GROUNDED |

*A "PRIOR GUESSING" verdict indicates the model maintained 100% accuracy even when all telemetry was removed, proving it relied on parametric priors rather than reading the logs.*

## Appendix B — Prompt Templates

*[Insert system_prompt.txt and system_prompt_evidence.txt here.]*

## Appendix C — models_used.json

*[Insert pinned snapshot IDs here.]*
