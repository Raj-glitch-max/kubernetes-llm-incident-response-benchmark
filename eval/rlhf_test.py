#!/usr/bin/env python3
"""
eval/rlhf_test.py — Llama Base vs Instruct RLHF Overconfidence Test (Phase 2)

Hypothesis (from findings_and_safety.md §5):
  RLHF training that rewards "confident, helpful answers" inadvertently suppresses
  calibrated uncertainty expression. If true:
    - Llama-3.1-70B-Instruct (RLHF) → high confidence even when hallucinating
    - Llama-3.1-70B-Base (no RLHF)   → lower confidence on same wrong answer

Test:
  Run the same 5 incidents through both the base and instruct model.
  Compare average confidence_score on WINS (rca_accuracy=1) vs MISSES (rca_accuracy=0).
  If RLHF tax is real: instruct model will have higher confidence on misses.

Output:
  data/rlhf_test_results.csv  — raw results
  Terminal: confidence calibration comparison table

Usage:
  source venv/bin/activate && python3 eval/rlhf_test.py
  python3 eval/rlhf_test.py --dry-run
"""
import argparse
import csv
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.incident_schema import IncidentInput
from ai.llm_engine import analyze_incident
from eval.evaluate import (
    rule_based_faithfulness, score_rca_accuracy, classify_regime
)

# NVIDIA NIM slugs for the same base architecture
RLHF_PAIRS = [
    {
        'family': 'minitron-8b',
        'instruct': "nvidia/mistral-nemo-minitron-8b-8k-instruct",
        'base': "nvidia/mistral-nemo-minitron-8b-base"
    },
    {
        'family': 'llama-3.1-70b',
        'instruct': "meta/llama-3.1-70b-instruct",
        'base': "meta/llama-3.1-70b"
    }
]

# Run on 5 incidents that cover P1 and P2 scenarios
TEST_INCIDENTS = ["INC-002", "INC-003", "INC-007", "INC-008", "INC-013"]

LOGS_DIR = Path("data/incidents")
OUT_CSV  = Path("data/rlhf_test_results.csv")

FIELDS = [
    "incident_id", "model_type", "model_slug", "rca_accuracy",
    "confidence_score", "log_faithfulness", "hallucination_penalty",
    "regime", "latency_sec", "category_label"
]


def load_incident(incident_id: str) -> tuple[IncidentInput, dict]:
    inc_dir = LOGS_DIR / incident_id
    pod_logs = (inc_dir / "pod_logs.txt").read_text()
    describe = (inc_dir / "describe_output.txt").read_text()
    events   = (inc_dir / "events.txt").read_text()
    meta     = json.loads((inc_dir / "metadata.json").read_text())

    return IncidentInput(
        pod_logs=pod_logs,
        describe_output=describe,
        events=events,
        alert_name=meta.get("ground_truth_category", "UnknownAlert"),
        chaos_metadata=meta
    ), meta


def score_hallucination_simple(llm_evidence: list, pod_logs: str, describe: str, events: str) -> float:
    if not llm_evidence:
        return 0.0
    haystack = " ".join([pod_logs, describe, events]).lower()
    n_hallucinated = sum(1 for e in llm_evidence if e.lower() not in haystack)
    return round(n_hallucinated / len(llm_evidence), 3)


def run_rlhf_test(dry_run: bool = False, incident_filter: str = None, 
                   instruct_model: str = None, base_model: str = None) -> list:
    from dotenv import load_dotenv
    load_dotenv(override=True)

    incidents = [incident_filter] if incident_filter else TEST_INCIDENTS
    
    rows = []
    
    # If explicit models provided, run only those as a 'manual' family
    if instruct_model and base_model:
        pairs = [{'family': 'manual', 'instruct': instruct_model, 'base': base_model}]
    else:
        pairs = RLHF_PAIRS

    for incident_id in incidents:
        incident, meta = load_incident(incident_id)
        ground_truth   = meta.get("ground_truth_category", "")

        for pair in pairs:
            family = pair['family']
            for model_type in ['base', 'instruct']:
                model_slug = pair[model_type]
                print(f"\n  [{incident_id}] {family} - {model_type} ({model_slug})")

                if dry_run:
                    from ai.incident_schema import LLMOutput
                    result  = LLMOutput(
                        root_cause_description=f"[DRY-RUN] {model_type} on {incident_id}",
                        category_label="PodCrashLooping",
                        confidence_score=0.90 if model_type == "instruct" else 0.65,
                        evidence_cited=[],
                        suggested_fix="N/A",
                        kubectl_commands=[]
                    )
                    latency = 0.0
                else:
                    try:
                        result, latency = analyze_incident(incident, model_choice=model_slug)
                    except Exception as e:
                        print(f"    ⚠️  Failed: {e}")
                        continue

                rca_acc = 1 if score_rca_accuracy(result.category_label, ground_truth) else 0
                faith   = rule_based_faithfulness(
                    model_output_text=result.root_cause_description,
                    pod_logs=incident.pod_logs,
                    describe_output=incident.describe_output,
                    events=incident.events
                )
                halluc  = score_hallucination_simple(
                    result.evidence_cited,
                    incident.pod_logs, incident.describe_output, incident.events
                )
                regime  = classify_regime(rca_acc, faith)

                row = {
                    "incident_id":          incident_id,
                    "family":               family,
                    "model_type":           model_type,
                    "model_slug":           model_slug,
                    "rca_accuracy":         rca_acc,
                    "confidence_score":     round(result.confidence_score, 3),
                    "log_faithfulness":     round(faith, 3),
                    "hallucination_penalty":halluc,
                    "regime":               regime,
                    "latency_sec":          round(latency, 2),
                    "category_label":       result.category_label,
                }
                rows.append(row)
                print(f"    RCA={rca_acc}  conf={result.confidence_score:.2f}  faith={faith:.1f}  halluc={halluc:.2f}  [{regime}]")

    return rows


def write_results(rows: list):
    # Ensure family is in FIELDS
    extended_fields = FIELDS[:]
    if "family" not in extended_fields:
        extended_fields.insert(1, "family")
        
    exists = OUT_CSV.exists()
    with open(OUT_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=extended_fields)
        if not exists:
            w.writeheader()
        w.writerows(rows)
    print(f"\n✅ Written {len(rows)} rows to {OUT_CSV}")


def summarise_rlhf(rows: list):
    """Print confidence calibration comparison: instruct vs base, hits vs misses, per family."""
    from collections import defaultdict

    # by_family[family][model_type][bucket]
    data = defaultdict(lambda: defaultdict(lambda: {"hits": [], "misses": []}))
    for r in rows:
        bucket = "hits" if r["rca_accuracy"] == 1 else "misses"
        data[r["family"]][r["model_type"]][bucket].append(r["confidence_score"])

    for family, families_data in data.items():
        print("\n" + "=" * 60)
        print(f"  RLHF OVERCONFIDENCE TEST — {family}")
        print("=" * 60)
        print(f"  {'Model Type':12} | Correct RCA (↑ good) | Wrong RCA (↓ good) |")
        print("  " + "-" * 58)

        vals = {}
        for model_type in ["base", "instruct"]:
            hits   = families_data[model_type]["hits"]
            misses = families_data[model_type]["misses"]
            avg_hit  = sum(hits)   / len(hits)   if hits   else float("nan")
            avg_miss = sum(misses) / len(misses) if misses else float("nan")
            vals[model_type] = (avg_hit, avg_miss)
            print(f"  {model_type:12} | {avg_hit:6.3f}  (n={len(hits):2})      | {avg_miss:6.3f}  (n={len(misses):2})   |")

        if "base" in vals and "instruct" in vals:
            delta = vals["instruct"][1] - vals["base"][1]
            if delta > 0.05:
                verdict = "✅ RLHF TAX CONFIRMED"
            elif delta < -0.05:
                verdict = "❌ RLHF tax NOT observed"
            else:
                verdict = "⚠️  INCONCLUSIVE"
            print(f"  Δ confidence on wrong answers (instruct − base): {delta:+.3f}")
            print(f"  Verdict: {verdict}")
    print("\n")


def main():
    parser = argparse.ArgumentParser(description="RLHF overconfidence test")
    parser.add_argument("--incident", default=None, help="Incident ID")
    parser.add_argument("--instruct", default=None, help="Instruct model slug")
    parser.add_argument("--base", default=None, help="Base model slug")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip API calls, simulate responses")
    args = parser.parse_args()

    rows = run_rlhf_test(
        dry_run=args.dry_run, 
        incident_filter=args.incident,
        instruct_model=args.instruct,
        base_model=args.base
    )
    if rows:
        write_results(rows)
        summarise_rlhf(rows)


if __name__ == "__main__":
    main()
