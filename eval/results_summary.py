import csv
import sys
from pathlib import Path

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

CSV_FILE = Path("data/incidents.csv")

if not CSV_FILE.exists():
    print(f"❌ {CSV_FILE} not found. Run at least one `make eval` first.")
    sys.exit(1)

if HAS_PANDAS:
    df = pd.read_csv(CSV_FILE)

    print("=" * 50)
    print("      BENCHMARK RESULTS SUMMARY")
    print("=" * 50)
    print(f"  Total Incidents Evaluated : {len(df)}")
    print(f"  Average RCA Accuracy      : {df['rca_accuracy'].mean():.2f} / 1.0")
    print(f"  Average Latency           : {df['latency_sec'].mean():.2f}s")
    print(f"  Hallucination Penalty Avg : {df['hallucination_penalty'].mean():.2f}")
    print(f"  Remediation Safe Rate     : {(df['remediation_safe'] == 1).sum()}/{len(df)}")
    print(f"  Perfect RCA Accuracy      : {(df['rca_accuracy'] == 1).sum()}/{len(df)}")
    print()
    print("Per-Incident Breakdown:")
    print("-" * 50)
    print(df[["incident_id", "model", "latency_sec", "rca_accuracy", "hallucination_penalty", "remediation_safe"]].to_string(index=False))
    print()
else:
    # Fallback to stdlib csv if pandas is not installed
    with open(CSV_FILE, newline="") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    rca_avg = sum(float(r["rca_accuracy"]) for r in rows) / total
    latency_avg = sum(float(r["latency_sec"]) for r in rows) / total
    remediation_safe = sum(1 for r in rows if float(r["remediation_safe"]) == 1.0)

    print("=" * 50)
    print("      BENCHMARK RESULTS SUMMARY")
    print("=" * 50)
    print(f"  Total Incidents        : {total}")
    print(f"  Avg RCA Accuracy       : {rca_avg:.2f}")
    print(f"  Avg Latency            : {latency_avg:.2f}s")
    print(f"  Safe Remediation Rate  : {remediation_safe}/{total}")
    print()
    print(f"{'INC ID':<12} {'Model':<18} {'Latency':>8} {'RCA':>6} {'Remediaton':>12}")
    print("-" * 60)
    for r in rows:
        print(f"{r['incident_id']:<12} {r['model']:<18} {float(r['latency_sec']):>8.2f} {float(r['rca_accuracy']):>6.1f} {float(r['remediation_safe']):>12.1f}")
