#!/usr/bin/env python3
"""
eval/ablation.py — Keyword-Controlled Log Swap Ablation (Phase 2)

Tests whether open-source model accuracy depends on log CONTENT or prior
knowledge by running 4 telemetry conditions per incident:

  Condition A — Full telemetry   (pod_logs + describe + events)
  Condition B — Structural only  (describe + events, no pod_logs)
  Condition C — Logs only        (pod_logs only, no describe/events)
  Condition D — Metadata only    (chaos_metadata, all telemetry blanked)

If accuracy degrades from Condition A → D, the model uses telemetry.
If accuracy is STABLE from A → D, the model is guessing from prior knowledge —
confirming the "Confident Liar = prior guessing" causal claim.

Design from paper_draft.md §4:
  "If accuracy is stable from condition A (full logs) to condition D
   (metadata only), models are drawing from priors rather than telemetry."

Usage:
  python3 eval/ablation.py --incident INC-002 --model nvidia-llama
  python3 eval/ablation.py --incident INC-002 --model nvidia-mistral
  python3 eval/ablation.py --all  # runs all incidents × models

Results are written to:
  data/ablation_results.csv
"""
import argparse
import csv
import json
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.incident_schema import IncidentInput, LLMOutput
from ai.llm_engine import analyze_incident, NVIDIA_MODELS
from eval.evaluate import (
    rule_based_faithfulness, score_rca_accuracy, score_severity_risk,
    classify_regime, get_true_severity
)

LOGS_DIR = Path("data/raw_logs")
OUT_CSV  = Path("data/ablation_results.csv")

ABLATION_FIELDS = [
    "incident_id", "model", "condition", "latency_sec",
    "rca_accuracy", "log_faithfulness", "confidence_score",
    "regime", "category_label", "root_cause_description"
]

CONDITIONS = {
    "A": "Full telemetry (pod_logs + describe + events)",
    "B": "Structural only (describe + events, no pod_logs)",
    "C": "Logs only (pod_logs, no describe/events)",
    "D": "Metadata only (all telemetry blanked)",
}


def load_raw_incident(incident_id: str) -> dict:
    """Load raw telemetry files for an incident."""
    inc_dir = LOGS_DIR / incident_id
    data = {}
    for key, fname in [
        ("pod_logs",       "pod_logs.txt"),
        ("describe_output","describe_output.txt"),
        ("events",         "events.txt"),
        ("metadata",       "metadata.json"),
    ]:
        p = inc_dir / fname
        if p.exists():
            if fname.endswith(".json"):
                data[key] = json.loads(p.read_text())
            else:
                data[key] = p.read_text()
        else:
            data[key] = {} if fname.endswith(".json") else ""
    return data


def build_incident_for_condition(raw: dict, condition: str) -> IncidentInput:
    """
    Build an IncidentInput with telemetry blanked according to the condition.
    """
    meta     = raw.get("metadata", {})
    pod_logs = raw.get("pod_logs", "")
    describe = raw.get("describe_output", "")
    events   = raw.get("events", "")

    if condition == "A":   # Full
        pl, dsc, evt = pod_logs, describe, events
    elif condition == "B": # Structural (no pod_logs)
        pl, dsc, evt = "", describe, events
    elif condition == "C": # Logs only
        pl, dsc, evt = pod_logs, "", ""
    elif condition == "D": # Metadata only (all blanked)
        pl, dsc, evt = "", "", ""
    else:
        raise ValueError(f"Unknown condition: {condition}")

    return IncidentInput(
        pod_logs=pl,
        describe_output=dsc,
        events=evt,
        alert_name=meta.get("ground_truth_category", "UnknownAlert"),
        chaos_metadata=meta
    )


def run_ablation_for_incident(incident_id: str, model: str, dry_run: bool = False):
    """Run all 4 conditions for a given incident + model pair."""
    raw    = load_raw_incident(incident_id)
    meta   = raw.get("metadata", {})
    chaos_type   = meta.get("chaos_type", "")
    ground_truth = meta.get("ground_truth_category", "")
    true_severity = get_true_severity(chaos_type)

    results = []
    for cond, cond_desc in CONDITIONS.items():
        print(f"\n  [{cond}] {cond_desc}")
        incident = build_incident_for_condition(raw, cond)

        if dry_run:
            # Dry run — simulate without actual API call
            result = LLMOutput(
                root_cause_description=f"[DRY-RUN] Condition {cond}",
                category_label="PodCrashLooping",
                confidence_score=0.90,
                evidence_cited=[],
                suggested_fix="N/A",
                kubectl_commands=[]
            )
            latency = 0.0
        else:
            result, latency = analyze_incident(incident, model_choice=model)

        rca_acc  = 1 if score_rca_accuracy(result.category_label, ground_truth) else 0
        faith    = rule_based_faithfulness(
            model_output_text=result.root_cause_description,
            pod_logs=raw.get("pod_logs", ""),
            describe_output=raw.get("describe_output", ""),
            events=raw.get("events", "")
        )
        regime   = classify_regime(rca_acc, faith)

        row = {
            "incident_id":        incident_id,
            "model":              model,
            "condition":          cond,
            "latency_sec":        round(latency, 2),
            "rca_accuracy":       rca_acc,
            "log_faithfulness":   round(faith, 3),
            "confidence_score":   round(result.confidence_score, 2),
            "regime":             regime,
            "category_label":     result.category_label,
            "root_cause_description": result.root_cause_description[:120].replace("\n", " "),
        }
        results.append(row)
        print(f"     RCA={rca_acc}  faith={faith:.1f}  conf={result.confidence_score:.2f}  regime={regime}")

    return results


def write_results(rows: list):
    exists = OUT_CSV.exists()
    with open(OUT_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ABLATION_FIELDS)
        if not exists:
            w.writeheader()
        w.writerows(rows)
    print(f"\n✅ Appended {len(rows)} rows to {OUT_CSV}")


def summarise_ablation(rows: list):
    """Print a 4-condition accuracy table for each (incident, model)."""
    from collections import defaultdict
    by_pair = defaultdict(dict)  # (incident, model) → {condition: rca}
    for r in rows:
        key = (r["incident_id"], r["model"])
        by_pair[key][r["condition"]] = (r["rca_accuracy"], r["log_faithfulness"])

    print("\n" + "=" * 72)
    print("  ABLATION SUMMARY — RCA accuracy across telemetry conditions")
    print("=" * 72)
    print(f"  {'Incident':8} {'Model':35} | A    B    C    D  | Verdict")
    print("  " + "-" * 70)

    for (inc, model), conds in sorted(by_pair.items()):
        accs = [conds.get(c, (None, None))[0] for c in "ABCD"]
        # If accuracy drops when telemetry removed → model uses telemetry
        # If accuracy stable across all 4 → model guesses from prior
        verdict = "PRIOR" if accs.count(1) == 4 else ("GROUNDED" if accs[0] != accs[-1] else "MIXED")
        acc_str = "  ".join(str(a) if a is not None else "?" for a in accs)
        print(f"  {inc:8} {model:35} | {acc_str} | {verdict}")

    print("=" * 72)


def main():
    import os
    from dotenv import load_dotenv
    load_dotenv(override=True)

    parser = argparse.ArgumentParser(
        description="Keyword-controlled ablation experiment"
    )
    parser.add_argument("--incident", default="INC-002",
                        help="Incident ID (e.g. INC-002)")
    parser.add_argument("--model", default="nvidia-mistral",
                        help="Model alias or NVIDIA NIM slug")
    parser.add_argument("--all", action="store_true",
                        help="Run all incidents × models")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip API calls, simulate responses")
    args = parser.parse_args()

    os.environ.setdefault("PYTHONPATH", str(Path(__file__).parent.parent))

    if args.all:
        incidents = [d.name for d in LOGS_DIR.iterdir()
                     if d.is_dir() and d.name.startswith("INC-")]
        models    = ["nvidia-mistral", "nvidia-llama", "nvidia-glm47"]
    else:
        incidents = [args.incident]
        models    = [args.model]

    all_rows = []
    for model in models:
        for incident_id in sorted(incidents):
            print(f"\n{'='*56}")
            print(f"  Ablation: {incident_id} × {model}")
            print(f"{'='*56}")
            try:
                rows = run_ablation_for_incident(incident_id, model, dry_run=args.dry_run)
                all_rows.extend(rows)
            except Exception as e:
                print(f"  ⚠️  Error: {e}")

    if all_rows:
        write_results(all_rows)
        summarise_ablation(all_rows)


if __name__ == "__main__":
    main()
