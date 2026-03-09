#!/usr/bin/env python3
"""
eval/bayesian_violation.py — Bayesian Violation Measurement (Evidence Invariance Experiment 4)

Measures whether model confidence updates when strongly contradicting evidence is provided.
If Evidence Invariance holds, confidence should be unchanged regardless of evidence content.

Works with any OpenAI-compatible API (NVIDIA NIM, OpenAI, Ollama, vLLM).

Test structure per incident:
  Prompt A: Metadata + SUPPORTING logs  → confidence for correct label
  Prompt D: Metadata only              → confidence for correct label
  Prompt X: Metadata + CONTRADICTING logs (from a different incident type) → confidence

If P(label|X) ≈ P(label|D): Bayesian violation confirmed (evidence ignored).
A proper Bayesian agent: P(label|X) << P(label|D) when evidence contradicts.

Usage:
  python3 eval/bayesian_violation.py --dry-run
  python3 eval/bayesian_violation.py --model nvidia-llama
  python3 eval/bayesian_violation.py --all
"""
import argparse
import csv
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.incident_schema import IncidentInput, LLMOutput
from ai.llm_engine import analyze_incident, NVIDIA_MODELS

LOGS_DIR = Path("data/incidents")
OUT_CSV  = Path("data/bayesian_violation_results.csv")

FIELDS = [
    "incident_id", "model", "true_label",
    "confidence_prior", "confidence_supporting", "confidence_contradicting",
    "bayesian_update_support", "bayesian_update_contra",
    "violation_magnitude", "is_evidence_invariant"
]

# Cross-incident pairs for contradiction testing
# Each maps: incident → which incident's logs to use as contradicting evidence
CONTRADICTION_MAP = {
    "INC-000": "INC-007",   # pod_kill vs memory_hog
    "INC-001": "INC-002",   # pod_kill vs pod_kill (different instance)
    "INC-002": "INC-007",   # pod_kill vs memory_hog
    "INC-003": "INC-009",   # image_pull vs oom_kill
    "INC-004": "INC-003",   # cpu_stress vs image_pull
    "INC-005": "INC-004",   # configmap_missing vs cpu_stress
    "INC-006": "INC-005",   # memory_hog vs configmap_missing
    "INC-007": "INC-003",   # memory_hog vs image_pull
    "INC-008": "INC-004",   # memory_limit vs cpu_stress
    "INC-009": "INC-002",   # oom_kill vs pod_kill
    "INC-010": "INC-007",   # network_partition vs memory_hog
    "INC-011": "INC-003",   # redis_auth vs image_pull
    "INC-012": "INC-009",   # cascading_failure vs oom_kill
    "INC-013": "INC-003",   # image_pull vs image_pull (different instance)
    "INC-014": "INC-007",   # pod_kill vs memory_hog
    "INC-015": "INC-004",   # cascading_failure vs cpu_stress
}


def load_raw_incident(incident_id: str) -> dict:
    """Load raw telemetry files for an incident."""
    inc_dir = LOGS_DIR / incident_id
    data = {"incident_id": incident_id}
    for key, fname in [
        ("pod_logs",        "pod_logs.txt"),
        ("describe_output", "describe_output.txt"),
        ("events",          "events.txt"),
        ("metadata",        "metadata.json"),
    ]:
        p = inc_dir / fname
        if p.exists():
            data[key] = json.loads(p.read_text()) if fname.endswith(".json") else p.read_text()
        else:
            data[key] = {} if fname.endswith(".json") else ""
    return data


def build_prior_prompt(raw: dict) -> IncidentInput:
    """Condition D — metadata only, telemetry blanked."""
    meta = raw.get("metadata", {})
    return IncidentInput(
        pod_logs="",
        describe_output="",
        events="",
        alert_name=meta.get("ground_truth_category", "UnknownAlert"),
        chaos_metadata=meta
    )


def build_supporting_prompt(raw: dict) -> IncidentInput:
    """Condition A — full telemetry (logs consistent with label)."""
    meta = raw.get("metadata", {})
    return IncidentInput(
        pod_logs=raw.get("pod_logs", ""),
        describe_output=raw.get("describe_output", ""),
        events=raw.get("events", ""),
        alert_name=meta.get("ground_truth_category", "UnknownAlert"),
        chaos_metadata=meta
    )


def build_contradicting_prompt(raw: dict, contra_raw: dict) -> IncidentInput:
    """Condition X — metadata from incident A + logs from incident B (contradicting)."""
    meta = raw.get("metadata", {})
    return IncidentInput(
        pod_logs=contra_raw.get("pod_logs", ""),
        describe_output=contra_raw.get("describe_output", ""),
        events=contra_raw.get("events", ""),
        alert_name=meta.get("ground_truth_category", "UnknownAlert"),
        chaos_metadata=meta
    )


def extract_confidence(result: LLMOutput) -> float:
    """Extract confidence score from LLM output."""
    return round(result.confidence_score, 3)


def run_bayesian_test(incident_id: str, model: str, dry_run: bool = False) -> dict:
    """Run the 3-condition Bayesian violation test for a single incident × model."""
    raw = load_raw_incident(incident_id)
    meta = raw.get("metadata", {})
    true_label = meta.get("ground_truth_category", "Unknown")

    # Find contradicting incident
    contra_id = CONTRADICTION_MAP.get(incident_id)
    if not contra_id:
        print(f"  ⚠️  No contradiction mapping for {incident_id}, skipping")
        return None
    contra_raw = load_raw_incident(contra_id)

    # Build 3 prompts
    prompt_prior = build_prior_prompt(raw)
    prompt_support = build_supporting_prompt(raw)
    prompt_contra = build_contradicting_prompt(raw, contra_raw)

    if dry_run:
        conf_prior = 0.90
        conf_support = 0.92
        conf_contra = 0.88
    else:
        _, _ = analyze_incident(prompt_prior, model_choice=model)
        result_prior, _ = analyze_incident(prompt_prior, model_choice=model)
        conf_prior = extract_confidence(result_prior)

        result_support, _ = analyze_incident(prompt_support, model_choice=model)
        conf_support = extract_confidence(result_support)

        result_contra, _ = analyze_incident(prompt_contra, model_choice=model)
        conf_contra = extract_confidence(result_contra)

    update_support = round(conf_support - conf_prior, 3)
    update_contra = round(conf_contra - conf_prior, 3)
    violation_mag = round(abs(conf_contra - conf_prior), 3)
    is_ei = violation_mag < 0.05

    row = {
        "incident_id": incident_id,
        "model": model,
        "true_label": true_label,
        "confidence_prior": conf_prior,
        "confidence_supporting": conf_support,
        "confidence_contradicting": conf_contra,
        "bayesian_update_support": update_support,
        "bayesian_update_contra": update_contra,
        "violation_magnitude": violation_mag,
        "is_evidence_invariant": int(is_ei),
    }

    print(f"  P(label|prior):       {conf_prior:.3f}")
    print(f"  P(label|supporting):  {conf_support:.3f}")
    print(f"  P(label|contradicting): {conf_contra:.3f}")
    print(f"  Bayesian update (contra): {update_contra:+.3f}")
    print(f"  Evidence Invariant: {is_ei}")

    return row


def write_results(rows: list):
    exists = OUT_CSV.exists()
    with open(OUT_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            w.writeheader()
        w.writerows(rows)
    print(f"\n✅ Written {len(rows)} rows to {OUT_CSV}")


def summarise(rows: list):
    """Print Bayesian violation summary."""
    ei_count = sum(1 for r in rows if r["is_evidence_invariant"])
    total = len(rows)
    mean_violation = sum(r["violation_magnitude"] for r in rows) / total if total else 0

    print("\n" + "=" * 60)
    print("  BAYESIAN VIOLATION SUMMARY")
    print("=" * 60)
    print(f"  Total tests:                 {total}")
    print(f"  Evidence Invariant (|Δ|<0.05): {ei_count}/{total} ({100*ei_count/total:.0f}%)")
    print(f"  Mean violation magnitude:    {mean_violation:.3f}")
    print("=" * 60)

    # Per-model breakdown
    models = set(r["model"] for r in rows)
    for m in sorted(models):
        m_rows = [r for r in rows if r["model"] == m]
        m_ei = sum(1 for r in m_rows if r["is_evidence_invariant"])
        m_viol = sum(r["violation_magnitude"] for r in m_rows) / len(m_rows)
        print(f"  {m:30s} | EI rate: {m_ei}/{len(m_rows)} | μ violation: {m_viol:.3f}")
    print()


def main():
    from dotenv import load_dotenv
    load_dotenv(override=True)

    parser = argparse.ArgumentParser(description="Bayesian violation measurement")
    parser.add_argument("--incident", default=None, help="Single incident ID")
    parser.add_argument("--model", default="nvidia-llama", help="Model alias or slug")
    parser.add_argument("--all", action="store_true", help="Run all incidents × models")
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls")
    args = parser.parse_args()

    if args.all:
        incidents = sorted([d.name for d in LOGS_DIR.iterdir()
                           if d.is_dir() and d.name.startswith("INC-")])
        models = ["nvidia-llama", "nvidia-mistral", "nvidia-glm47", "nvidia-gptoss20b"]
    else:
        incidents = [args.incident] if args.incident else ["INC-002", "INC-003", "INC-007"]
        models = [args.model]

    all_rows = []
    for model in models:
        for inc in incidents:
            print(f"\n{'='*56}")
            print(f"  Bayesian Test: {inc} × {model}")
            print(f"{'='*56}")
            try:
                row = run_bayesian_test(inc, model, dry_run=args.dry_run)
                if row:
                    all_rows.append(row)
            except Exception as e:
                print(f"  ⚠️  Error: {e}")

    if all_rows:
        write_results(all_rows)
        summarise(all_rows)


if __name__ == "__main__":
    main()
