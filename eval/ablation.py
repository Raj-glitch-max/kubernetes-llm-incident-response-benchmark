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

LOGS_DIR = Path("data/incidents")
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
    "D-strict": "Metadata only, label fields stripped (chaos_type + ground_truth_category removed)",
}

# Fields that constitute a label leak when present in Condition D
LABEL_LEAK_FIELDS = {"chaos_type", "ground_truth_category", "chaos_scenario", "root_cause_category"}


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


def build_incident_for_condition(raw: dict, condition: str, strict: bool = False) -> IncidentInput:
    """
    Build an IncidentInput with telemetry blanked according to the condition.

    strict=True: for Condition D (or D-strict), strips LABEL_LEAK_FIELDS from
    chaos_metadata so the LLM cannot read the category label from metadata.
    This enables the causal comparison between label-leaked vs label-sanitized D.
    """
    meta     = raw.get("metadata", {})
    pod_logs = raw.get("pod_logs", "")
    describe = raw.get("describe_output", "")
    events   = raw.get("events", "")

    # Normalise condition key
    cond_key = condition.upper().replace("-STRICT", "")

    if cond_key == "A":   # Full
        pl, dsc, evt = pod_logs, describe, events
    elif cond_key == "B": # Structural (no pod_logs)
        pl, dsc, evt = "", describe, events
    elif cond_key == "C": # Logs only
        pl, dsc, evt = pod_logs, "", ""
    elif cond_key == "D": # Metadata only (all telemetry blanked)
        pl, dsc, evt = "", "", ""
    else:
        raise ValueError(f"Unknown condition: {condition}")

    # Strip label-leak fields when strict mode is active for Condition D
    effective_meta = dict(meta)
    if strict and cond_key == "D":
        for field in LABEL_LEAK_FIELDS:
            effective_meta.pop(field, None)
        # Keep only safe identifier fields
        print(f"     [strict] chaos_metadata fields after stripping: {list(effective_meta.keys())}")

    # alert_name: in strict-D strip the ground_truth_category hint from alert_name too
    alert = "UnknownAlert" if (strict and cond_key == "D") else meta.get("ground_truth_category", "UnknownAlert")

    return IncidentInput(
        pod_logs=pl,
        describe_output=dsc,
        events=evt,
        alert_name=alert,
        chaos_metadata=effective_meta
    )


def run_ablation_for_incident(incident_id: str, model: str, dry_run: bool = False,
                               condition_filter: str = None, strict: bool = False):
    """Run 4 conditions for a given incident + model pair.

    strict=True: runs Condition D with label fields stripped (D-strict).
    Results are labelled as 'D-strict' in the output so they can be
    compared against regular 'D' rows in the CSV.
    """
    raw    = load_raw_incident(incident_id)
    meta   = raw.get("metadata", {})
    chaos_type   = meta.get("chaos_type", "")
    ground_truth = meta.get("ground_truth_category", "")
    true_severity = get_true_severity(chaos_type)

    results = []

    # Determine which conditions to run
    if condition_filter:
        target_conditions = [condition_filter]
    elif strict:
        # In strict mode, only D-strict is relevant — the others are identical to normal run
        target_conditions = ["D-strict"]
    else:
        target_conditions = [c for c in CONDITIONS.keys() if c != "D-strict"]

    for cond in target_conditions:
        cond_desc = CONDITIONS.get(cond, cond)
        print(f"\n  [{cond}] {cond_desc}")
        # Pass strict=True when condition includes strict
        is_strict = strict or cond == "D-strict"
        incident = build_incident_for_condition(raw, cond, strict=is_strict)

        if dry_run:
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


def write_results(rows: list, strict: bool = False):
    out_csv = Path("data/ablation_results_strict.csv") if strict else OUT_CSV
    exists = out_csv.exists()
    with open(out_csv, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ABLATION_FIELDS)
        if not exists:
            w.writeheader()
        w.writerows(rows)
    print(f"\n✅ Appended {len(rows)} rows to {out_csv}")


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
    parser.add_argument("--incident", default=None,
                        help="Incident ID (e.g. INC-002)")
    parser.add_argument("--condition", default=None,
                        help="Condition (A, B, C, D, D-strict). If provided, only this one runs.")
    parser.add_argument("--model", default=None,
                        help="Model alias or NVIDIA NIM slug")
    parser.add_argument("--all", action="store_true",
                        help="Run all incidents × models")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip API calls, simulate responses")
    parser.add_argument("--strict", action="store_true",
                        help="Strip label-leak fields (chaos_type, ground_truth_category) from "
                             "chaos_metadata in Condition D. Results written to ablation_results_strict.csv.")
    args = parser.parse_args()

    os.environ.setdefault("PYTHONPATH", str(Path(__file__).parent.parent))

    if args.all:
        incidents = [d.name for d in LOGS_DIR.iterdir()
                     if d.is_dir() and d.name.startswith("INC-")]
        models    = ["nvidia-mistral", "nvidia-llama", "nvidia-glm47"]
    else:
        incidents = [args.incident] if args.incident else ["INC-002"]
        models    = [args.model] if args.model else ["nvidia-mistral"]

    if args.strict:
        print("\n⚠️  STRICT MODE: Condition D will have chaos_type + ground_truth_category stripped")
        print("   Results → data/ablation_results_strict.csv\n")

    all_rows = []
    for model in models:
        for incident_id in sorted(incidents):
            print(f"\n{'='*56}")
            print(f"  Ablation: {incident_id} × {model}{'  [STRICT]' if args.strict else ''}")
            print(f"{'='*56}")
            try:
                rows = run_ablation_for_incident(
                    incident_id, model,
                    dry_run=args.dry_run,
                    condition_filter=args.condition,
                    strict=args.strict
                )
                all_rows.extend(rows)
            except Exception as e:
                print(f"  ⚠️  Error: {e}")

    if all_rows:
        write_results(all_rows, strict=args.strict)
        summarise_ablation(all_rows)


if __name__ == "__main__":
    main()
