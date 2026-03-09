#!/usr/bin/env python3
"""
Leaderboard Generator — eval/leaderboard.py

Reads data/incidents.csv, groups by model, computes aggregate scores,
and writes data/leaderboard.json + prints a markdown table to stdout.

Columns handled (new + legacy):
  incident_id, model, latency_sec, rca_accuracy, hallucination_penalty,
  log_faithfulness, cmd_executability, remediation_safe, confidence_score,
  root_cause_description
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

CSV_PATH = Path("data/incidents.csv")
JSON_PATH = Path("data/leaderboard.json")


def load_results() -> list[dict]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"{CSV_PATH} not found — run some evaluations first.")
    with open(CSV_PATH, newline="") as f:
        return list(csv.DictReader(f))


def safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def aggregate(rows: list[dict]) -> dict:
    """Group by model, compute means for all numeric columns."""
    by_model = defaultdict(list)
    for row in rows:
        # Skip mock rows
        if "[MOCK]" in row.get("root_cause_description", ""):
            continue
        by_model[row["model"]].append(row)

    leaderboard = {}
    for model, model_rows in by_model.items():
        n = len(model_rows)
        leaderboard[model] = {
            "incidents_evaluated": n,
            "rca_accuracy":          round(sum(safe_float(r.get("rca_accuracy")) for r in model_rows) / n, 3),
            "hallucination_penalty": round(sum(safe_float(r.get("hallucination_penalty")) for r in model_rows) / n, 3),
            "log_faithfulness":      round(sum(safe_float(r.get("log_faithfulness", 0)) for r in model_rows) / n, 3),
            "cmd_executability":     round(sum(safe_float(r.get("cmd_executability", 0)) for r in model_rows) / n, 3),
            "remediation_safe":      round(sum(safe_float(r.get("remediation_safe")) for r in model_rows) / n, 3),
            "avg_latency_sec":       round(sum(safe_float(r.get("latency_sec")) for r in model_rows) / n, 1),
            "avg_confidence":        round(sum(safe_float(r.get("confidence_score", 0)) for r in model_rows) / n, 3),
        }

    # Sort: highest rca_accuracy first, then lowest hallucination_penalty
    return dict(
        sorted(
            leaderboard.items(),
            key=lambda kv: (-kv[1]["rca_accuracy"], kv[1]["hallucination_penalty"])
        )
    )


def print_markdown_table(leaderboard: dict):
    COL_W = 30
    print(f"\n{'=' * 105}")
    print("  🏆  K8s LLM Benchmark Leaderboard")
    print(f"{'=' * 105}")
    header = (
        f"{'Model':<{COL_W}} | {'n':>4} | "
        f"{'RCA↑':>6} | {'Halluc↓':>7} | {'LogFaith↑':>9} | "
        f"{'CmdExec↑':>8} | {'Remed↑':>6} | {'Latency↓':>9} | {'Conf':>5}"
    )
    print(header)
    print("-" * 105)
    for model, s in leaderboard.items():
        short = model[-28:] if len(model) > 28 else model
        print(
            f"{short:<{COL_W}} | {s['incidents_evaluated']:>4} | "
            f"{s['rca_accuracy']:>6.3f} | {s['hallucination_penalty']:>7.3f} | "
            f"{s['log_faithfulness']:>9.3f} | {s['cmd_executability']:>8.3f} | "
            f"{s['remediation_safe']:>6.3f} | {s['avg_latency_sec']:>8.1f}s | "
            f"{s['avg_confidence']:>5.3f}"
        )
    print(f"{'=' * 105}\n")


if __name__ == "__main__":
    rows = load_results()
    leaderboard = aggregate(rows)

    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_PATH, "w") as f:
        json.dump(leaderboard, f, indent=2)

    print_markdown_table(leaderboard)
    print(f"✅ Leaderboard written to {JSON_PATH}")
    print(f"   Total non-mock rows processed: {len([r for r in rows if '[MOCK]' not in r.get('root_cause_description','')])} from {len(rows)} total")
