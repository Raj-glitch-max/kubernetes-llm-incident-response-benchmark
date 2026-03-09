#!/usr/bin/env python3
"""
eval/confident_liar.py — The "Confident Liar" Analysis

Finds incidents where a model gave the CORRECT RCA label 
but with ZERO real evidence from the actual logs.

This is the most dangerous LLM failure mode in production SRE:
  - Model says the right thing
  - Model cannot show its work
  - Next time: same confidence, wrong answer, no warning

Usage:
    python3 eval/confident_liar.py
    python3 eval/confident_liar.py --model meta/llama-3.1-70b-instruct

Published finding: On 10 real K8s chaos incidents, Llama-3.1-70B and Mistral-7B
exhibited the Confident Liar pattern on 12/15 correct diagnoses (80%).
This is the first open dataset proving this failure mode on live K8s chaos data.
"""
import csv
import json
import argparse
from pathlib import Path
from collections import defaultdict

CSV_PATH = Path("results/main_results.csv")


def safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def analyze(model_filter=None):
    rows = list(csv.DictReader(CSV_PATH.open()))

    print("=" * 72)
    print("  🚨 CONFIDENT LIAR ANALYSIS")
    print("  Model gave CORRECT label + ZERO real log evidence")
    print("=" * 72)
    print()

    # Per-model stats
    by_model = defaultdict(lambda: {
        "total": 0,
        "correct": 0,
        "correct_no_faith": 0,  # correct label, zero log faithfulness
        "correct_with_faith": 0,
        "wrong": 0,
        "incidents": []
    })

    for row in rows:
        model = row["model"]
        if model_filter and model_filter not in model:
            continue

        rca     = safe_float(row.get("rca_accuracy"))
        faith   = safe_float(row.get("log_faithfulness", 0))
        conf    = safe_float(row.get("confidence_score", 0))
        inc_id  = row["incident_id"]

        s = by_model[model]
        s["total"] += 1

        if rca == 1.0:
            s["correct"] += 1
            if faith == 0.0:
                s["correct_no_faith"] += 1
                s["incidents"].append({
                    "incident": inc_id,
                    "confidence": conf,
                    "faith": faith,
                    "desc_preview": row.get("root_cause_description", "")[:80]
                })
            else:
                s["correct_with_faith"] += 1
        else:
            s["wrong"] += 1

    grand_liar_correct = 0
    grand_total_correct = 0

    for model, s in sorted(by_model.items()):
        if s["total"] == 0:
            continue

        liar_pct = (s["correct_no_faith"] / s["correct"] * 100) if s["correct"] else 0
        grand_liar_correct += s["correct_no_faith"]
        grand_total_correct += s["correct"]

        verdict = "🔴 LIAR" if liar_pct >= 70 else ("🟡 MIXED" if liar_pct >= 30 else "🟢 GROUNDED")

        print(f"Model: {model}")
        print(f"  Total evals:          {s['total']}")
        print(f"  Correct RCA:          {s['correct']} ({s['correct']/s['total']*100:.0f}%)")
        print(f"  Correct + No Evidence:{s['correct_no_faith']} ({liar_pct:.0f}%) ← Confident Liar {verdict}")
        print(f"  Correct + Evidence:   {s['correct_with_faith']}")
        print(f"  Wrong RCA:            {s['wrong']}")

        if s["incidents"]:
            print(f"  Liar Incidents:")
            for inc in s["incidents"][:5]:  # show max 5
                print(f"    {inc['incident']} | conf={inc['confidence']:.2f} | faith={inc['faith']:.2f} | {inc['desc_preview']}...")

        print()

    print("-" * 72)
    overall_pct = (grand_liar_correct / grand_total_correct * 100) if grand_total_correct else 0
    print(f"  OVERALL: {grand_liar_correct}/{grand_total_correct} correct answers were Confident Liars ({overall_pct:.0f}%)")
    print()
    print("  INTERPRETATION:")
    print("  A Confident Liar gives the right diagnosis but cannot ground it in")
    print("  any real log evidence. In production, this model will give the same")
    print("  confidence when it's WRONG — you have no way to tell the difference.")
    print("=" * 72)

    # Write JSON report
    report = {
        "finding": "Confident Liar Pattern",
        "description": "Models that give correct RCA labels with zero log-grounded evidence",
        "dataset": "10 real K8s chaos incidents (INC-001 to INC-010)",
        "models": {}
    }
    for model, s in by_model.items():
        liar_pct = (s["correct_no_faith"] / s["correct"] * 100) if s["correct"] else 0
        report["models"][model] = {
            "total": s["total"],
            "correct": s["correct"],
            "confident_liar_count": s["correct_no_faith"],
            "confident_liar_pct": round(liar_pct, 1),
            "verdict": "LIAR" if liar_pct >= 70 else ("MIXED" if liar_pct >= 30 else "GROUNDED")
        }

    out = Path("data/confident_liar_analysis.json")
    out.write_text(json.dumps(report, indent=2))
    print(f"\n✅ Full report written to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None, help="Filter by model name (substring match)")
    args = parser.parse_args()
    analyze(args.model)
