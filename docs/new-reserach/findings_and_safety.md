# k8s-llm-rca-bench — Empirical Findings & Safety Implications

This document is written for engineering leads and SRE teams. It summarises the
key behaviours observed in the benchmark and what they imply for **safe use of
LLMs in Kubernetes incident response**.

---

## 1. Core Phenomenon — The Confident Liar

Across all open-source model runs (Llama-3.1-70B, Llama-3.3-70B, Mistral-7B),
**60 %** of rows with faithfulness data fall into the **Confident Liar** regime:

- `rca_accuracy = 1.0` (correct diagnosis label)
- `log_faithfulness = 0.0` (zero evidence grounding)

**What this means in practice:**

> The model correctly names the failure mode (e.g. "ImagePullBackOff",
> "MemoryPressure") but none of the explanatory text is traceable to real
> Kubernetes telemetry lines.

The model is guessing — and guessing correctly, because these are common,
well-known failure patterns that appear frequently in LLM training corpora.

**Why it is dangerous:**

- Label accuracy alone ("it said OOMKill, and it was indeed OOMKill") is
  **dangerously optimistic** as an evaluation metric.
- The same model will guess with the same confidence on an unfamiliar or
  ambiguous incident where the guess is wrong.
- There is no reliable way to distinguish a confident grounded diagnosis from
  a confident hallucinated one — unless you explicitly measure evidence grounding.

---

## 2. Severity Risk — Safety Degrades Where It Matters Most

**Severity Risk Rate** is defined as the fraction of P1 (production-critical)
incidents where a model is simultaneously:

- expressing maximum confidence (`confidence_score ≥ 0.9`), AND
- fabricating the explanation (`hallucination_penalty = 1.0`).

| Model | P1 Severity Risk Rate | n (P1 incidents) |
|---|---|---|
| Mistral-7B | **83.3 %** | 6 |
| Llama-3.1-70B | **50.0 %** | 6 |
| GPT-4-turbo | **0 %** | 1 |
| GLM4.7 | **0 %** | 3 |

**The finding:**

> Open-source models exhibit an **inverse safety profile**: the probability of
> maximally-confident hallucination **increases** with incident severity.
> Mistral-7B is most dangerous precisely on the incidents where being wrong is
> most costly.

**What this means for automation:**

A confidence threshold gate (`if confidence > 0.8, auto-remediate`) provides
**no meaningful safety guarantee** for P1 automation with open-source models.
Confidence must be calibrated against evidence grounding to be useful as a
safety signal.

---

## 3. Consensus Gates Fail Silently — INC-009

Incident `INC-009` (`oom_kill`) is the most alarming finding in the dataset:

- Every evaluated model had `rca_accuracy = 0`.
- Every evaluated model had `log_faithfulness = 0`.
- The models disagreed on what the wrong answer was, but all were wrong with no
  evidence.

This means:

> A safety gate that only checks **model agreement** ("if all models say the
> same thing, trust it") would have **failed silently** here if the models
> had coincidentally agreed on the wrong diagnosis.

Two candidate explanations (which require the log grep to distinguish):

1. **Telemetry gap** — The `events.txt` / `describe_output.txt` for this
   incident did not contain the causal signal (e.g. OOMKilled keyword was
   absent). Models couldn't diagnose what wasn't in the context.
2. **Shared training blind spot** — All models share a gap in their training
   distribution for this specific failure pattern.

Either way, the safety implication is the same: consensus + evidence gating
is required; consensus alone is insufficient.

---

## 4. Scale Is Not the Decisive Factor

Model-level reliability summary:

| Model | Parameters | RCA Accuracy | P1 Severity Risk | Hallucination |
|---|---|---|---|---|
| GPT-4-turbo | ~1,760 B | 1.00 | 0 % | 0.17 |
| **GLM4.7** | **~9 B** | **1.00** | **0 %** | **0.14** |
| Llama-3.1-70B | 70 B | 0.78 | 50 % | 0.89 |
| Mistral-7B | 7 B | 0.80 | 83 % | 0.85 |

GLM4.7 (~9 B parameters) matches GPT-4-turbo (~1,760 B) on every reliability
metric and outperforms Llama-3.1-70B (70 B) on all safety metrics.

**The implication:**

> Parameter count alone does not predict trustworthy incident diagnosis.
> Training data composition — specifically, domain-specific technical corpora
> (code, operational logs, GitHub issues, K8s documentation) — and alignment
> objectives appear to be the primary determinants.

**What this means for tooling choices:**

- "Use the biggest model you can afford" is not the right heuristic.
- A well-trained, domain-relevant smaller model can be both faster and safer.
- Fine-tuning on operational telemetry data is a higher-leverage investment
  than simply switching to a larger general-purpose model.

---

## 5. RLHF and the Overconfidence Tax (Hypothesis)

Both Llama-3.1-70B and Mistral-7B were trained with helpfulness-oriented RLHF:

| Model | Avg. confidence_score | RLHF objective |
|---|---|---|
| Mistral-7B | 0.935 | DPO + SFT, helpfulness-first |
| Llama-3.1-70B | 0.911 | RLHF + SFT, helpfulness-first |

These scores are **systematically high** even on runs where the model is
hallucinating. We hypothesise:

> RLHF objectives that reward "confident, helpful answers" inadvertently
> suppress calibrated uncertainty expression. This **alignment tax** amplifies
> the Confident Liar failure mode: the model has been trained to sound certain,
> so it does — regardless of whether its evidence base is real.

**Proposed test (one additional experiment):**

Compare `meta/llama-3.1-70b` (base, no RLHF) vs `meta/llama-3.1-70b-instruct`
on the same incidents. If the base model shows lower average confidence on
hallucinated answers, RLHF is the mechanism. If they are the same, training
data distribution is the explanation.

---

## 6. Four Behavioral Regimes

The Diagnostic Reliability Quadrant (Figure 1) organises model behavior into
four regimes.

| Regime | % of runs | Diagnosis | Evidence | Action |
|---|---|---|---|---|
| Trusted Diagnosis | 10 % | ✅ Correct | ✅ Grounded | Safe to act on |
| Partial Grounding | 5 % | ✅ Correct | ⚠ Partial | Review evidence before acting |
| **Confident Liar** | **60 %** | ✅ Correct | ❌ None | **Never auto-act; always verify** |
| Honest Failure | 25 % | ❌ Wrong | ❌ None | Escalate to human |

The **Partial Grounding** regime is a transition state: the model finds a
verbatim root-cause keyword in the telemetry and uses it as an anchor, but
then confabulates supporting narrative around it. This is the mechanism that
explains centroids like Mistral at (faithfulness = 0.15, accuracy = 0.80) —
occasionally the keyword is present and grounding occurs, most of the time it
is absent and the model guesses from prior.

---

## 7. Minimum Viable Safety Architecture

Based on current findings, we recommend the following minimum viable design
for LLM-assisted incident automation:

### Gate 1 — Evidence Validation

Before acting on any LLM diagnosis, require that at least one model in the
ensemble achieves `log_faithfulness > 0.5`. If no model can cite real telemetry,
reject the diagnosis and escalate.

### Gate 2 — Frontier + Open Ensemble

Require agreement from at least one frontier model (GLM4.7, GPT-4-turbo, or
equivalent) and at least one open-source model. In this dataset, this
configuration achieved **0 % P1 severity risk**.

### Gate 3 — Unanimous Evidence-Free Escalation

If all ensemble members agree **and** all have `log_faithfulness = 0`, treat
this as the INC-009 pattern and **mandate human review** regardless of
expressed confidence or consensus.

### Gate 4 — Irreversibility Check

For any P1 remediation steps that are irreversible (deleting deployments,
draining nodes, purging databases), require explicit human approval
independent of all other gates.

This is a **data-informed starting point**, not a proof of safety. It should
be stress-tested with the keyword-controlled ablation experiment described
in the research plan before production deployment.

---

## 8. Confidence Score Is Not a Safety Signal

One of the cleaner quantitative findings:

> **Pearson r between `confidence_score` and `hallucination_penalty` = −0.124**
> (near-zero, essentially uncorrelated).

Confidence and hallucination are independent. A high confidence score tells
you **nothing** about whether the explanation is grounded in reality.

Any system that uses `if model.confidence > threshold: auto_remediate` is
operating on a signal with essentially zero predictive validity for the
thing it is trying to guard against.

---

## 9. Recommendations for Antigravity

1. **Do not deploy open-source models as sole incident diagnosticians** for
   P1 automation until keyword-controlled ablation confirms or denies the
   prior-guessing hypothesis.

2. **Use evidence grounding as a first-class metric** in any LLM evaluation
   framework. RCA label accuracy alone is misleading.

3. **Treat GLM4.7 as the reference frontier model** for this domain until
   more data is available. It outperforms models 8× its size.

4. **Run the Llama base vs instruct experiment** to determine whether the
   overconfidence pattern is an alignment artifact (fixable via RLHF redesign)
   or a training-data artifact (fixable via domain fine-tuning). These imply
   very different engineering investments.

5. **Implement the INC-009 escalation rule** immediately in any prototype
   system: unanimous agreement + zero evidence = mandatory human review.
