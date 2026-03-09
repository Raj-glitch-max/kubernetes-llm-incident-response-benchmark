# ADR 001: Rule-Based Deterministic Faithfulness Scorer

## Status
Accepted

## Context
Standard RAG evaluation frameworks (e.g., RAGAS) typically use a Large Language Model (often GPT-4) as a "Judge" to determine if a model's response is faithful to the provided context. 

Specifically, we want to measure **Log Faithfulness**: does the LLM's RCA explanation actually derive from the pod logs, describes, and events provided, or is it a "Confident Liar" guessing from parametric priors?

## Decision
We decided to implement a **deterministic, rule-based scorer** rather than an LLM-based judge.

### Rationale
1. **Avoid Circular Logic**: Since GPT-4-turbo is one of the models we are evaluating, using it as a judge for itself (or for models it might be biased against/towards) creates a conflict of interest in the experiment design.
2. **Reproducibility & Cost**: A rule-based scorer runs in milliseconds with zero API costs, ensuring that anyone can run the benchmark without financial barriers.
3. **Domain Specificity**: Kubernetes logs have high structural density (keywords like `OOMKilled`, `ImagePullBackOff`). A regex/keyword-based check is highly effective at catching "keyword anchoring"—the primary mechanism of groundedness in this domain.
4. **Transparency**: The scoring logic is 20 lines of Python code, making it fully auditable for researchers.

## Consequences
- The score is strictly bounded [0.0, 0.5, 1.0]. It lacks the "nuance" of a semantic LLM judge.
- Models that paraphrase very heavily without using technical keywords or verbatim lines might be under-scored. However, in an SRE context, using exact technical terms from logs is considered best practice.
