#!/usr/bin/env python3
"""
eval/phase1_migrate.py — Phase 1 CSV migration and re-scoring.

Does four things in one pass:
1. Removes all [MOCK] rows (GPT-4-turbo placeholder data)
2. Adds new columns: scenario, true_severity, severity_risk, regime
3. Re-scores log_faithfulness using rule_based_faithfulness on raw log files
4. Writes a clean k8s_rca_bench_final.csv with full column coverage

Safe: does NOT modify incidents.csv — reads it and writes a new clean file.
"""
import csv
import json
import re
from pathlib import Path
from eval.evaluate import (
    rule_based_faithfulness, score_severity_risk, classify_regime,
    get_true_severity, get_scenario, SCENARIO_LABELS
)

SRC_CSV  = Path("data/incidents.csv")
OUT_CSV  = Path("data/k8s_rca_bench_final.csv")
LOGS_DIR = Path("data/raw_logs")

OLD_FIELDS = [
    "incident_id", "model", "latency_sec", "rca_accuracy",
    "hallucination_penalty", "log_faithfulness", "cmd_executability",
    "remediation_safe", "confidence_score", "root_cause_description"
]

NEW_FIELDS = [
    "incident_id", "model", "scenario", "latency_sec",
    "rca_accuracy", "hallucination_penalty", "log_faithfulness",
    "cmd_executability", "remediation_safe", "confidence_score",
    "true_severity", "severity_risk", "regime", "root_cause_description"
]


def safe_float(val, default=None):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def load_telemetry(incident_id: str) -> dict:
    inc_dir = LOGS_DIR / incident_id
    telem = {"pod_logs": "", "describe_output": "", "events": ""}
    for key, fname in [("pod_logs", "pod_logs.txt"),
                        ("describe_output", "describe_output.txt"),
                        ("events", "events.txt")]:
        p = inc_dir / fname
        if p.exists():
            telem[key] = p.read_text()
    return telem


def get_chaos_type(incident_id: str) -> str:
    meta = LOGS_DIR / incident_id / "metadata.json"
    if meta.exists():
        data = json.loads(meta.read_text())
        return data.get("chaos_type", "")
    return ""


def process():
    rows = list(csv.DictReader(SRC_CSV.open(), fieldnames=OLD_FIELDS))
    # Skip the header row if present
    if rows and rows[0]["incident_id"] == "incident_id":
        rows = rows[1:]

    clean = []
    skipped_mock = 0
    n_rescored = 0

    for row in rows:
        desc = row.get("root_cause_description", "")

        # ── 1. Remove MOCK rows ──────────────────────────────────────────────
        if "[MOCK]" in desc:
            skipped_mock += 1
            continue

        inc_id = row["incident_id"]
        chaos_type = get_chaos_type(inc_id)
        scenario   = get_scenario(chaos_type) if chaos_type else ""
        true_sev   = get_true_severity(chaos_type) if chaos_type else 2

        # ── 2. Re-score log_faithfulness with rule_based_faithfulness ────────
        telem = load_telemetry(inc_id)
        faith_score = rule_based_faithfulness(
            model_output_text=desc,
            pod_logs=telem["pod_logs"],
            describe_output=telem["describe_output"],
            events=telem["events"]
        )
        if safe_float(row.get("log_faithfulness")) is None:
            n_rescored += 1

        # ── 3. Compute severity_risk ─────────────────────────────────────────
        conf_val = safe_float(row.get("confidence_score"), 0.0)
        halluc   = safe_float(row.get("hallucination_penalty"), 0.0)
        rca_acc  = safe_float(row.get("rca_accuracy"), 0.0)
        sev_risk = score_severity_risk(true_sev, conf_val, halluc)

        # ── 4. Classify regime ───────────────────────────────────────────────
        regime = classify_regime(rca_acc, faith_score)

        clean.append({
            "incident_id":          inc_id,
            "model":                row.get("model", ""),
            "scenario":             scenario,
            "latency_sec":          row.get("latency_sec", ""),
            "rca_accuracy":         row.get("rca_accuracy", ""),
            "hallucination_penalty":row.get("hallucination_penalty", ""),
            "log_faithfulness":     round(faith_score, 3),
            "cmd_executability":    row.get("cmd_executability", ""),
            "remediation_safe":     row.get("remediation_safe", ""),
            "confidence_score":     row.get("confidence_score", ""),
            "true_severity":        true_sev,
            "severity_risk":        sev_risk,
            "regime":               regime,
            "root_cause_description": desc,
        })

    # Write output
    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=NEW_FIELDS)
        writer.writeheader()
        writer.writerows(clean)

    print(f"✅ Phase 1 migration complete")
    print(f"   Input rows:       {len(rows)}")
    print(f"   MOCK rows removed:{skipped_mock}")
    print(f"   Final clean rows: {len(clean)}")
    print(f"   Rows re-scored:   {n_rescored}")
    print(f"   Output: {OUT_CSV}")
    print()

    # Print regime distribution
    from collections import Counter
    regimes = Counter(r["regime"] for r in clean)
    total = len(clean)
    print("  Regime Distribution:")
    for regime, count in sorted(regimes.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        print(f"    {regime:<25} {count:>3} ({pct:4.1f}%)")

    # Print severity risk
    p1_rows = [r for r in clean if int(r["true_severity"]) == 1]
    risky   = [r for r in p1_rows if int(r["severity_risk"]) == 1]
    print(f"\n  P1 incidents:      {len(p1_rows)}")
    print(f"  P1 severity risk:  {len(risky)} ({len(risky)/len(p1_rows)*100:.1f}%)" if p1_rows else "  No P1 incidents found")


if __name__ == "__main__":
    process()
