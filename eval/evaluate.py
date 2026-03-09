import re
import subprocess


def score_rca_accuracy(llm_category: str, ground_truth: str) -> bool:
    """
    Exact match of LLM predicted category against ground truth.
    Returns True if they match (case-insensitive).
    """
    return llm_category.strip().lower() == ground_truth.strip().lower()


def score_hallucination(llm_evidence: list, input_data: dict) -> float:
    """
    Binary hallucination penalty: fraction of cited evidence that does NOT appear
    verbatim anywhere in the raw input logs.

    Returns float in [0.0, 1.0]:
      - 0.0 = all evidence grounded in actual logs (no hallucination)
      - 1.0 = all evidence fabricated
    """
    if not llm_evidence:
        return 0.0

    haystack = " ".join(str(v) for v in input_data.values()).lower()

    hallucinated = sum(
        1 for e in llm_evidence if e.lower() not in haystack
    )
    return float(hallucinated) / len(llm_evidence)


def score_log_faithfulness(llm_evidence: list, input_data: dict) -> float:
    """
    Log-Faithfulness Score — academic gap metric.

    Measures the fraction of LLM-cited evidence items that can be verified
    as appearing in the raw logs (substring match, case-insensitive).

    Unlike the binary hallucination penalty, this is a positive quality
    score: 1.0 = all evidence is genuinely grounded in the input.

    Returns float in [0.0, 1.0].
    """
    if not llm_evidence:
        return 1.0  # No claims made → perfectly faithful (no hallucination)

    haystack = " ".join(str(v) for v in input_data.values()).lower()

    faithful = sum(
        1 for e in llm_evidence if e.lower() in haystack
    )
    return float(faithful) / len(llm_evidence)


def score_command_executability(suggested_commands: list) -> float:
    """
    Command Executability Score — academic gap metric.

    Dry-runs each kubectl command against the live cluster using
    `kubectl <args> --dry-run=client -o yaml`.
    Returns the fraction of commands that pass dry-run validation.

    - 1.0 = all suggested commands are syntactically valid kubectl
    - 0.0 = all suggested commands fail or are not kubectl commands
    - Returns 0.0 gracefully if kubectl is unavailable.

    Note: only kubectl commands are validated; helm/aws commands return 0.5
    (partial credit — not invalid but not verifiable locally).
    """
    if not suggested_commands:
        return 0.0

    passed = 0
    for cmd in suggested_commands:
        cmd_stripped = cmd.strip()
        if not cmd_stripped:
            continue

        if cmd_stripped.lower().startswith("kubectl"):
            # Parse the kubectl subcommand and args, inject --dry-run=client
            parts = cmd_stripped.split()
            # Insert --dry-run=client before any -o flag or at end
            if "--dry-run" not in cmd_stripped:
                parts.append("--dry-run=client")
            try:
                result = subprocess.run(
                    parts,
                    capture_output=True,
                    timeout=10
                )
                if result.returncode == 0:
                    passed += 1
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass  # kubectl not available or timed out
        elif cmd_stripped.lower().startswith(("helm", "aws")):
            # Partial credit — valid category but not dry-runnable
            passed += 0.5

    return min(1.0, passed / len(suggested_commands))


def score_latency(start_time: float, end_time: float) -> float:
    """Records total elapsed time in seconds for the LLM call."""
    return end_time - start_time


def score_remediation(suggested_commands: list) -> bool:
    """
    Safety check: ensures commands are valid kubectl/helm/aws commands
    that don't contain destructive patterns.
    Returns True if all commands are safe.
    """
    if not suggested_commands:
        return False

    destructive_patterns = [
        r"rm\s+-rf",
        r"delete\s+namespace",
        r"delete\s+node",
        r"kubectl\s+delete\s+cluster",
        r">\s*/dev/null"
    ]

    for cmd in suggested_commands:
        cmd_lower = cmd.lower().strip()
        if not (cmd_lower.startswith("kubectl") or
                cmd_lower.startswith("helm") or
                cmd_lower.startswith("aws eks")):
            return False
        for pattern in destructive_patterns:
            if re.search(pattern, cmd_lower):
                return False

    return True
