#!/usr/bin/env python3
"""
eval/statistics.py — Statistical validation for the K8s RCA Benchmark

Implements:
  1. McNemar's test: Are A→D accuracy drops statistically significant?
  2. Bootstrap 95% confidence intervals for leaderboard accuracy figures
  3. Summary table for paper Section 4.2

Usage:
  python3 eval/statistics.py                          # full report
  python3 eval/statistics.py --mcnemar               # just McNemar
  python3 eval/statistics.py --bootstrap              # just bootstrap CIs
  python3 eval/statistics.py --compare-strict-d       # D vs D-strict comparison
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest


# ---------------------------------------------------------------------------
# 1. McNemar's Test — Condition A vs Condition D accuracy
# ---------------------------------------------------------------------------

def mcnemar_ablation(csv_path: str = "data/ablation_results.csv") -> dict:
    """
    For each (incident, model) pair, compare accuracy in Condition A vs D.
    McNemar's test asks: is the drop from A→D significant?

    Discordant pairs:
      b = A correct AND D wrong  (our expected direction)
      c = A wrong  AND D correct (reverse — model guesses accidentally)

    Under H0 (no effect), P(b) = P(c) = 0.5
    We use exact binomial (not chi-squared) because n is small.
    """
    df = pd.read_csv(csv_path)
    results_per_model = {}

    for model in df["model"].unique():
        mdf = df[df["model"] == model]
        pairs = []
        for inc in mdf["incident_id"].unique():
            a_rows = mdf[(mdf["incident_id"] == inc) & (mdf["condition"] == "A")]
            d_rows = mdf[(mdf["incident_id"] == inc) & (mdf["condition"] == "D")]
            if a_rows.empty or d_rows.empty:
                continue
            acc_a = int(a_rows["rca_accuracy"].values[0])
            acc_d = int(d_rows["rca_accuracy"].values[0])
            pairs.append({"inc": inc, "acc_A": acc_a, "acc_D": acc_d})

        if not pairs:
            continue

        res = pd.DataFrame(pairs)
        b = int(((res.acc_A == 1) & (res.acc_D == 0)).sum())  # A right, D wrong
        c = int(((res.acc_A == 0) & (res.acc_D == 1)).sum())  # A wrong, D right
        disc = b + c

        if disc == 0:
            p = 1.0
        else:
            # Exact binomial: how often b ≥ observed, if H0: P(b) = 0.5
            p = float(binomtest(b, disc, 0.5, alternative="greater").pvalue)

        results_per_model[model] = {
            "n_pairs": len(pairs),
            "b_A_right_D_wrong": b,
            "c_A_wrong_D_right": c,
            "discordant": disc,
            "p_value": round(p, 4),
            "significant_p05": p < 0.05,
        }

    return results_per_model


def print_mcnemar(results: dict):
    print("\n" + "=" * 70)
    print("  McNemar's Test — Condition A vs D (does telemetry matter?)")
    print("  H0: accuracy identical with and without telemetry")
    print("  H1: accuracy higher in A (model uses telemetry)")
    print("=" * 70)
    print(f"  {'Model':38} | pairs |  b |  c | disc | p-value | sig?")
    print("  " + "-" * 68)
    for model, r in sorted(results.items()):
        sig = "✅ YES" if r["significant_p05"] else "  no"
        print(
            f"  {model:38} | {r['n_pairs']:5} | {r['b_A_right_D_wrong']:2} | "
            f"{r['c_A_wrong_D_right']:2} | {r['discordant']:4} | "
            f"{r['p_value']:.4f}  | {sig}"
        )
    print("=" * 70)
    print("  b = A correct & D wrong (telemetry helped)")
    print("  c = A wrong & D correct (telemetry hurt / model guessed right)")
    print()


# ---------------------------------------------------------------------------
# 2. Strict-D comparison — how much does label stripping change accuracy?
# ---------------------------------------------------------------------------

def compare_strict_d(
    regular_csv: str = "data/ablation_results.csv",
    strict_csv: str = "data/ablation_results_strict.csv",
) -> pd.DataFrame:
    """
    Compare Condition D (with label fields) vs D-strict (label fields stripped).
    If accuracy drops when labels are stripped, that proves the label leak is
    the causal driver of Condition D accuracy — not prior knowledge alone.
    """
    reg = pd.read_csv(regular_csv)
    reg = reg[reg["condition"] == "D"][["incident_id", "model", "rca_accuracy"]].rename(
        columns={"rca_accuracy": "acc_D_leaked"}
    )

    strict = pd.read_csv(strict_csv)
    strict = strict[strict["condition"] == "D-strict"][["incident_id", "model", "rca_accuracy"]].rename(
        columns={"rca_accuracy": "acc_D_strict"}
    )

    merged = pd.merge(reg, strict, on=["incident_id", "model"], how="inner")
    merged["delta"] = merged["acc_D_leaked"] - merged["acc_D_strict"]
    return merged


def print_strict_d_comparison(df: pd.DataFrame):
    print("\n" + "=" * 70)
    print("  Condition D vs D-strict comparison")
    print("  (positive delta = label leak caused the correct answer)")
    print("=" * 70)
    print(f"  {'Incident':8} {'Model':35} | D-leaked | D-strict | Δ")
    print("  " + "-" * 65)
    for _, row in df.iterrows():
        print(
            f"  {row['incident_id']:8} {row['model']:35} | "
            f"    {int(row['acc_D_leaked'])}     |    {int(row['acc_D_strict'])}     | {int(row['delta']):+d}"
        )

    avg_delta = df["delta"].mean()
    print("  " + "-" * 65)
    print(f"  {'Average drop from stripping labels':44} |          |          | {avg_delta:+.2f}")
    print("=" * 70)
    print()


# ---------------------------------------------------------------------------
# 3. Bootstrap Confidence Intervals
# ---------------------------------------------------------------------------

def bootstrap_ci(values: list, n: int = 10000, ci: float = 0.95) -> tuple:
    """Bootstrap confidence interval for the mean of a list of values."""
    vals = np.array(values, dtype=float)
    if len(vals) == 0:
        return (float("nan"), float("nan"))
    boot = [np.mean(np.random.choice(vals, len(vals), replace=True)) for _ in range(n)]
    alpha = (1 - ci) / 2
    lo, hi = np.percentile(boot, [alpha * 100, (1 - alpha) * 100])
    return (round(float(lo), 3), round(float(hi), 3))


def leaderboard_with_ci(
    csv_path: str = "results/main_results.csv",
    leaderboard_path: str = "data/leaderboard.json",
    n_bootstrap: int = 10000,
) -> pd.DataFrame:
    """
    Augment the leaderboard with 95% bootstrap CIs on rca_accuracy.
    Returns a DataFrame ready for the paper table.
    """
    df = pd.read_csv(csv_path)
    lb = json.loads(Path(leaderboard_path).read_text()) if Path(leaderboard_path).exists() else {}

    rows = []
    for model in df["model"].unique():
        accs = df[df["model"] == model]["rca_accuracy"].tolist()
        n = len(accs)
        mean_acc = float(np.mean(accs))
        lo, hi = bootstrap_ci(accs, n=n_bootstrap)
        rows.append({
            "model": model,
            "n": n,
            "rca_accuracy": round(mean_acc, 3),
            "ci_lo": lo,
            "ci_hi": hi,
            "ci_str": f"[{lo:.3f}, {hi:.3f}]",
            # Pull extra metrics from leaderboard.json if available
            "hallucination_penalty": lb.get(model, {}).get("hallucination_penalty", float("nan")),
            "log_faithfulness": lb.get(model, {}).get("log_faithfulness", float("nan")),
        })

    return pd.DataFrame(rows).sort_values("rca_accuracy", ascending=False).reset_index(drop=True)


def print_leaderboard_ci(df: pd.DataFrame):
    print("\n" + "=" * 80)
    print("  Leaderboard — RCA Accuracy with 95% Bootstrap Confidence Intervals")
    print("=" * 80)
    print(f"  {'Model':38} | n  | Acc   | 95% CI            | Halluc | Faith")
    print("  " + "-" * 78)
    for _, row in df.iterrows():
        print(
            f"  {row['model']:38} | {int(row['n']):2} | {row['rca_accuracy']:.3f} | "
            f"{row['ci_str']:17} | {row['hallucination_penalty']:.3f}  | {row['log_faithfulness']:.3f}"
        )
    print("=" * 80)
    print("  Note: Wide CIs on small-n models (GLM4.7 n=5) are honest, not a weakness.")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Statistical validation for K8s RCA benchmark")
    parser.add_argument("--mcnemar", action="store_true", help="McNemar A vs D test only")
    parser.add_argument("--bootstrap", action="store_true", help="Bootstrap CI table only")
    parser.add_argument("--compare-strict-d", action="store_true",
                        help="Compare D (label-leaked) vs D-strict (label-stripped)")
    parser.add_argument("--ablation-csv", default="data/ablation_results.csv")
    parser.add_argument("--incidents-csv", default="results/main_results.csv")
    parser.add_argument("--leaderboard-json", default="data/leaderboard.json")
    args = parser.parse_args()

    run_all = not (args.mcnemar or args.bootstrap or args.compare_strict_d)

    if run_all or args.mcnemar:
        mcn = mcnemar_ablation(args.ablation_csv)
        print_mcnemar(mcn)
        # Save JSON
        Path("data/mcnemar_results.json").write_text(json.dumps(mcn, indent=2))
        print("  💾 Saved data/mcnemar_results.json")

    if run_all or args.bootstrap:
        lb_df = leaderboard_with_ci(args.incidents_csv, args.leaderboard_json)
        print_leaderboard_ci(lb_df)
        lb_df.to_csv("data/leaderboard_with_ci.csv", index=False)
        print("  💾 Saved data/leaderboard_with_ci.csv")

    if args.compare_strict_d:
        if not Path("data/ablation_results_strict.csv").exists():
            print("\n⚠️  data/ablation_results_strict.csv not found.")
            print("   Run: python3 eval/ablation.py --strict --incident INC-XXX --model <model>")
        else:
            cmp_df = compare_strict_d(args.ablation_csv, "data/ablation_results_strict.csv")
            print_strict_d_comparison(cmp_df)
            cmp_df.to_csv("data/strict_d_comparison.csv", index=False)
            print("  💾 Saved data/strict_d_comparison.csv")


if __name__ == "__main__":
    main()
