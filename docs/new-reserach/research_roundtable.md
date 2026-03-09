# AI Methodology Committee — 13-Round Debate Summary

This document records the key outputs of a 13-round structured debate between
three frontier AI systems (GPT-4-turbo, Claude Sonnet, Perplexity) that was used
to iteratively design and stress-test the k8s-llm-rca-bench methodology.

The purpose of this document is both historical record and evidence for a
potential second publication on AI-assisted research design.

---

## 1. Why a Multi-AI Debate Was Used

Traditional peer review is slow and asynchronous. For an engineering benchmark
project with a short infrastructure window (one AWS account, one day of compute),
rapid methodology validation was needed. We used three frontier AI systems as a
"methodology committee" — a structured adversarial review process where each
system critiqued and extended the others' suggestions.

The process revealed that:

- **Convergence on a methodology claim** across three independently reasoning
  systems provides stronger validation than any single-system recommendation.
- **Divergence** on a methodology question maps to genuinely open research
  questions where expert disagreement is legitimate.

---

## 2. Convergence Map (62 % convergence rate)

The following table summarises the 13-round convergence across all three systems:

| Methodology Question | GPT-4 | Claude | Perplexity | Outcome |
|---|---|---|---|---|
| Log ablation as decisive experiment | ✅ | ✅ | ✅ | **Locked** |
| 3-tier RCA scoring rubric | ✅ | ✅ | ✅ | **Locked** |
| Keyword anchoring as explanatory mechanism | ✅ | ✅ | ✅ | **Locked** |
| Consensus gate fails on correlated errors | ✅ | ✅ | ✅ | **Locked** |
| Domain-specific metric preferred over RAGAS | ✅ | ✅ | ✅ | **Locked** |
| MTTR as a benchmark metric | 🔶 partial | ❌ | ✅ | Open question |
| Venue (systems vs ML) | 🔶 both | ICSE-SEIP | MLSys | Open question |
| Title framing (normative vs question) | 🔶 | question | normative | Open question |

Converged items = methodologically robust decisions.
Diverged items = genuinely contested research questions for future resolution.

---

## 3. Methodology Contributions From the Debate

The debate produced the following concrete methodology decisions:

### 3.1 Keyword-Controlled Log Ablation

**Origin:** Round 4 (all three systems).

A poisoned condition where telemetry from a different incident (with no
keyword overlap) is substituted to test whether model accuracy depends on
log content or prior knowledge. This turns the Confident Liar pattern from
a correlation into a causal claim.

### 3.2 Rule-Based Deterministic Faithfulness Scorer

**Origin:** Round 11 (Perplexity), confirmed by Claude and GPT-4.

Avoids the circular evaluation problem of LLM-judged metrics. Fully
deterministic, reproducible, no API calls required.

### 3.3 RAGAS Circular Judge Problem Identified

**Origin:** Round 11 (Perplexity).

Both Claude and GPT-4 had previously recommended RAGAS without noting that
its default judge is GPT-4-turbo — which is among the models being evaluated.
This identification prevented a significant methodological vulnerability.

### 3.4 P1 Severity Risk Rate Metric

**Origin:** Round 12 (Perplexity).

A safety-oriented metric that quantifies the most dangerous failure mode:
maximum confidence + maximum hallucination on production-critical incidents.
Revealed an inverse safety profile for open-source models.

### 3.5 GLM4.7 Scale Anomaly

**Origin:** Round 13 (Perplexity).

Identifying that GLM4.7 (~9 B) matches GPT-4-turbo (~1,760 B) breaks the
"scale enables evidence grounding" hypothesis and reframes the finding as
a training data composition story.

### 3.6 Snapshot IDs for Reproducibility

**Origin:** Round 12 (Perplexity).

Five-minute fix with permanent reproducibility implications. OpenAI silently
updates GPT-4-turbo without changing the model string; without pinned snapshot
IDs the benchmark is technically irreproducible.

### 3.7 Zenodo DOI for Dataset Citation

**Origin:** Round 13 (Perplexity).

GitHub URLs are not citable in papers. Zenodo provides a free permanent DOI
in under five minutes. Critical for paper citation and dataset discoverability.

---

## 4. Key Debate Exchanges

### Round 5 — First "Confident Liar" framing
Perplexity surfaced the pattern of correct labels + zero evidence.
Claude and GPT-4 both confirmed it as the central finding.

### Round 8 — RLHF confound hypothesis introduced
Perplexity noted that RLHF-for-helpfulness may be the *mechanism* producing
overconfident hallucination. Neither Claude nor GPT-4 had raised this.

### Round 11 — RAGAS circular judge problem
Perplexity identified that RAGAS uses GPT-4-turbo as default judge.
Claude acknowledged the oversight ("I should have caught this").
GPT-4 confirmed the rule-based scorer as the correct alternative.

### Round 12 — Phase transition theory proposed then broken
GPT-4 proposed a "phase transition at 70B" hypothesis to explain the clusters.
Perplexity identified that GLM4.7 (~9 B) collapses this theory — a smaller
model matches a vastly larger one, disproving scale as the mechanism.

### Round 13 — Debate declared complete
All three systems converged on the same message: stop debating, start writing.
This meta-consensus itself is evidence of robust methodology.

---

## 5. Potential Second Publication

The 13-round structured debate is the subject of a separate proposed paper:

**Title:** "AI as Methodology Committee: Convergence and Divergence in
Multi-LLM Research Design Review"

**Venue:** FAccT 2027 or similar Science-of-Science track.

**Core claim:** When multiple frontier AI systems independently review the
same research methodology and reach identical conclusions, those conclusions
are methodologically robust. Divergence points map to genuinely open questions.
The process is faster, cheaper, and more adversarial than waiting for
traditional peer review.

**Evidence:** The 13-round transcript (this document), convergence table above,
and the list of methodology decisions that were subsequently validated by data.

**Caution:** This paper should be written *after* Paper 1 (the benchmark paper)
is submitted. Paper 1 must stand on its own empirical merits; Paper 2 can
reference it as the subject domain.
