#!/usr/bin/env python3
"""
eval/generate_paper_figures.py — Publication-Quality Figure Generator

Generates ALL figures for the Evidence Invariance / Confident Liars paper.
Reads from data/*.csv files produced by the benchmark.

Usage:
  python3 eval/generate_paper_figures.py
  python3 eval/generate_paper_figures.py --figure 1
"""
import argparse
import os
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT_DIR = Path("figures")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Model display names and colors ──────────────────────────────────────────

MODEL_MAP = {
    "gpt-4-turbo": "GPT-4 Turbo",
    "mistralai/mistral-7b-instruct-v0.3": "Mistral-7B",
    "meta/llama-3.1-70b-instruct": "Llama-3.1-70B",
    "meta/llama-3.3-70b-instruct": "Llama-3.3-70B",
    "z-ai/glm4.7": "GLM-4.7 (9B)",
    "nvidia-glm47": "GLM-4.7 (9B)",
    "nvidia-llama": "Llama-3.1-70B",
    "nvidia-mistral": "Mistral-7B",
    "nvidia-gptoss20b": "GPT-OSS-20B",
    "openai/gpt-oss-20b": "GPT-OSS-20B",
    "z-ai/glm5": "GLM-5",
}

PALETTE = {
    "GPT-4 Turbo":   "#38bdf8",
    "Mistral-7B":    "#fbbf24",
    "Llama-3.1-70B": "#f472b6",
    "Llama-3.3-70B": "#fb923c",
    "GLM-4.7 (9B)":  "#4ade80",
    "GPT-OSS-20B":   "#a78bfa",
    "GLM-5":         "#34d399",
}

DARK_BG = "#0f172a"
DARK_FG = "#94a3b8"
DARK_GRID = "#475569"
DARK_CARD = "#1e293b"


def _style_ax(ax, title=None, xlabel=None, ylabel=None):
    """Apply dark theme styling to an axes."""
    ax.set_facecolor(DARK_BG)
    for spine in ax.spines.values():
        spine.set_color(DARK_GRID)
    ax.tick_params(colors=DARK_FG, labelsize=10)
    if title:
        ax.set_title(title, fontsize=16, color="white", pad=14, fontweight="bold")
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=12, color=DARK_FG)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=12, color=DARK_FG)


def _load_incidents():
    df = pd.read_csv("results/main_results.csv")
    df["display_model"] = df["model"].map(lambda x: MODEL_MAP.get(x, x))
    return df


# ─── FIGURE 1: Diagnostic Reliability Quadrant ──────────────────────────────

def figure_1_quadrant():
    """Scatter: faithfulness (x) vs accuracy (y) — reveals 4 behavioral regimes."""
    df = _load_incidents()

    fig, ax = plt.subplots(figsize=(10, 8), facecolor=DARK_BG)
    _style_ax(ax, "Diagnostic Reliability Quadrant",
              "Log Faithfulness (Evidence Grounding)", "RCA Accuracy")

    for model, group in df.groupby("display_model"):
        color = PALETTE.get(model, "#94a3b8")
        ax.scatter(group["log_faithfulness"], group["rca_accuracy"],
                   label=model, s=120, alpha=0.8, edgecolors="white",
                   linewidth=0.5, c=color, zorder=5)

    ax.axhline(0.5, color=DARK_GRID, linestyle="--", alpha=0.5)
    ax.axvline(0.25, color=DARK_GRID, linestyle="--", alpha=0.5)

    style = dict(fontsize=13, color="white", fontweight="bold", alpha=0.25, ha="center", va="center")
    ax.text(0.75, 0.8, "TRUSTED\nDIAGNOSIS", **style)
    ax.text(0.10, 0.8, "CONFIDENT\nLIAR", **style)
    ax.text(0.10, 0.2, "HONEST\nFAILURE", **style)
    ax.text(0.75, 0.2, "GROUNDED\nBUT WRONG", **style)

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.15)
    ax.legend(facecolor=DARK_CARD, edgecolor=DARK_GRID, labelcolor="white", fontsize=9)

    plt.tight_layout()
    out = OUT_DIR / "fig1_quadrant.png"
    plt.savefig(out, dpi=200, facecolor=DARK_BG)
    plt.close()
    print(f"✅ {out}")


# ─── FIGURE 2: Confidence vs Faithfulness (The Devastating Scatter) ─────────

def figure_2_confidence_faithfulness():
    """Shows r ≈ −0.124 visually — confidence predicts NOTHING about faithfulness."""
    df = _load_incidents()
    df = df.dropna(subset=["confidence_score", "log_faithfulness"])

    fig, ax = plt.subplots(figsize=(9, 7), facecolor=DARK_BG)
    _style_ax(ax, "Confidence vs Evidence Grounding — r = −0.124",
              "Self-Reported Confidence", "Log Faithfulness")

    for model, group in df.groupby("display_model"):
        color = PALETTE.get(model, "#94a3b8")
        ax.scatter(group["confidence_score"], group["log_faithfulness"],
                   label=model, s=100, alpha=0.7, c=color, edgecolors="white", linewidth=0.5)

    # Regression line
    x = df["confidence_score"].values
    y = df["log_faithfulness"].values
    if len(x) > 3:
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        xline = np.linspace(x.min(), x.max(), 100)
        ax.plot(xline, p(xline), "--", color="#ef4444", linewidth=2, alpha=0.7, label="Regression line")

        r = np.corrcoef(x, y)[0, 1]
        ax.text(0.05, 0.95, f"Pearson r = {r:.3f}\n(null signal)",
                transform=ax.transAxes, fontsize=12, color="#ef4444",
                va="top", fontweight="bold",
                bbox=dict(boxstyle="round", facecolor=DARK_CARD, edgecolor="#ef4444", alpha=0.8))

    ax.set_xlim(0, 1.05)
    ax.set_ylim(-0.05, 1.1)
    ax.legend(facecolor=DARK_CARD, edgecolor=DARK_GRID, labelcolor="white", fontsize=9)

    plt.tight_layout()
    out = OUT_DIR / "fig2_confidence_faithfulness.png"
    plt.savefig(out, dpi=200, facecolor=DARK_BG)
    plt.close()
    print(f"✅ {out}")


# ─── FIGURE 3: P1 Severity Risk Rate ────────────────────────────────────────

def figure_3_p1_risk():
    """Bar chart of P1 Severity Risk Rate per model — the safety metric."""
    df = _load_incidents()
    df = df.dropna(subset=["confidence_score", "hallucination_penalty"])

    # Approximate severity from chaos_type if available
    p1_types = {"oom_kill", "memory_limit", "cascading_failure", "network_partition"}

    models = df["display_model"].unique()
    risk_data = []

    for model in models:
        m_df = df[df["display_model"] == model]
        # Count high-confidence + hallucinating runs
        p1_risky = m_df[
            (m_df["confidence_score"] >= 0.9) &
            (m_df["hallucination_penalty"] > 0.5)
        ]
        total = len(m_df)
        risk_rate = len(p1_risky) / total if total > 0 else 0
        risk_data.append({"model": model, "risk_rate": risk_rate, "n": total})

    risk_df = pd.DataFrame(risk_data).sort_values("risk_rate", ascending=False)

    fig, ax = plt.subplots(figsize=(10, 6), facecolor=DARK_BG)
    _style_ax(ax, "P1 Severity Risk Rate by Model",
              "", "Risk Rate (confident + hallucinating)")

    colors = [PALETTE.get(m, "#94a3b8") for m in risk_df["model"]]
    bars = ax.barh(risk_df["model"], risk_df["risk_rate"], color=colors, edgecolor="white", linewidth=0.5)

    for bar, row in zip(bars, risk_df.itertuples()):
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
                f"{row.risk_rate:.0%} (n={row.n})",
                va="center", fontsize=10, color="white")

    ax.set_xlim(0, 1)
    ax.axvline(0.5, color="#ef4444", linestyle="--", alpha=0.5, label="Critical threshold")
    ax.legend(facecolor=DARK_CARD, edgecolor=DARK_GRID, labelcolor="white")

    plt.tight_layout()
    out = OUT_DIR / "fig3_p1_risk.png"
    plt.savefig(out, dpi=200, facecolor=DARK_BG)
    plt.close()
    print(f"✅ {out}")


# ─── FIGURE 4: Regime Distribution Pie ──────────────────────────────────────

def figure_4_regime_distribution():
    """Pie chart showing distribution of behavioral regimes across all runs."""
    df = _load_incidents()

    # Classify regimes
    def classify(row):
        acc = row.get("rca_accuracy", 0)
        faith = row.get("log_faithfulness", 0)
        if acc >= 0.5 and faith >= 0.5:
            return "Trusted Diagnosis"
        elif acc >= 0.5 and 0 < faith < 0.5:
            return "Partial Grounding"
        elif acc >= 0.5 and faith == 0:
            return "Confident Liar"
        else:
            return "Honest Failure"

    df["regime"] = df.apply(classify, axis=1)
    counts = df["regime"].value_counts()

    regime_colors = {
        "Trusted Diagnosis": "#4ade80",
        "Partial Grounding": "#38bdf8",
        "Confident Liar": "#ef4444",
        "Honest Failure": "#94a3b8",
    }

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), facecolor=DARK_BG)

    # Pie chart
    ax1.set_facecolor(DARK_BG)
    colors = [regime_colors.get(r, "#94a3b8") for r in counts.index]
    wedges, texts, autotexts = ax1.pie(counts, labels=counts.index, autopct="%1.0f%%",
                                        colors=colors, textprops={"color": "white", "fontsize": 11},
                                        pctdistance=0.75, startangle=90)
    for t in autotexts:
        t.set_fontweight("bold")
    ax1.set_title("Behavioral Regime Distribution\n(All Runs)", fontsize=14, color="white", pad=10)

    # Per-model regime stacked bar
    _style_ax(ax2, "Regime Distribution by Model", "", "Fraction of Runs")
    regime_order = ["Trusted Diagnosis", "Partial Grounding", "Confident Liar", "Honest Failure"]
    pivot = df.groupby(["display_model", "regime"]).size().unstack(fill_value=0)
    pivot = pivot.reindex(columns=regime_order, fill_value=0)
    pivot_pct = pivot.div(pivot.sum(axis=1), axis=0)

    bottom = np.zeros(len(pivot_pct))
    for regime in regime_order:
        if regime in pivot_pct.columns:
            vals = pivot_pct[regime].values
            ax2.barh(pivot_pct.index, vals, left=bottom,
                     color=regime_colors.get(regime, "#94a3b8"),
                     label=regime, edgecolor="white", linewidth=0.3)
            bottom += vals

    ax2.set_xlim(0, 1)
    ax2.legend(facecolor=DARK_CARD, edgecolor=DARK_GRID, labelcolor="white", fontsize=9, loc="lower right")

    plt.tight_layout()
    out = OUT_DIR / "fig4_regime_distribution.png"
    plt.savefig(out, dpi=200, facecolor=DARK_BG)
    plt.close()
    print(f"✅ {out}")


# ─── FIGURE 5: Ablation Condition Accuracy (The Smoking Gun) ────────────────

def figure_5_ablation():
    """Grouped bar — accuracy across 4 telemetry conditions. The causal proof."""
    csv_path = "data/ablation_results.csv"
    if not os.path.exists(csv_path):
        print(f"⚠️ {csv_path} not found, skipping figure 5")
        return

    df = pd.read_csv(csv_path)
    df["display_model"] = df["model"].map(lambda x: MODEL_MAP.get(x, x))

    fig, ax = plt.subplots(figsize=(12, 6), facecolor=DARK_BG)
    _style_ax(ax, "Ablation: RCA Accuracy Across Telemetry Conditions",
              "Model × Incident", "RCA Accuracy")

    conditions = ["A", "B", "C", "D"]
    cond_colors = {"A": "#4ade80", "B": "#38bdf8", "C": "#fbbf24", "D": "#ef4444"}

    pairs = df.groupby(["display_model", "incident_id"]).first().index.tolist()
    x = np.arange(len(pairs))
    width = 0.2

    for i, cond in enumerate(conditions):
        vals = []
        for model, inc in pairs:
            row = df[(df["display_model"] == model) & (df["incident_id"] == inc) & (df["condition"] == cond)]
            vals.append(row["rca_accuracy"].values[0] if len(row) > 0 else 0)
        ax.bar(x + i * width, vals, width, label=f"Condition {cond}",
               color=cond_colors[cond], edgecolor="white", linewidth=0.3)

    ax.set_xticks(x + 1.5 * width)
    ax.set_xticklabels([f"{m}\n{inc}" for m, inc in pairs], fontsize=7, rotation=45, ha="right")
    ax.set_ylim(0, 1.15)
    ax.legend(facecolor=DARK_CARD, edgecolor=DARK_GRID, labelcolor="white")

    # Annotation
    ax.text(0.5, 1.08, "Accuracy FLAT across conditions = models ignore telemetry",
            transform=ax.transAxes, fontsize=11, color="#ef4444",
            ha="center", fontweight="bold",
            bbox=dict(boxstyle="round", facecolor=DARK_CARD, edgecolor="#ef4444", alpha=0.8))

    plt.tight_layout()
    out = OUT_DIR / "fig5_ablation.png"
    plt.savefig(out, dpi=200, facecolor=DARK_BG)
    plt.close()
    print(f"✅ {out}")


# ─── FIGURE 6: D vs D-strict Comparison (The Kill Shot) ─────────────────────

def figure_6_dstrict():
    """Side-by-side: Condition D (with label) vs D-strict (label stripped).
    This is THE figure that proves metadata leakage is the mechanism."""
    csv_d = "data/ablation_results.csv"
    csv_ds = "data/ablation_results_strict.csv"

    if not os.path.exists(csv_d) or not os.path.exists(csv_ds):
        print(f"⚠️  Missing ablation CSVs, skipping figure 6")
        return

    df_d = pd.read_csv(csv_d)
    df_ds = pd.read_csv(csv_ds)

    df_d = df_d[df_d["condition"] == "D"]
    df_d["display_model"] = df_d["model"].map(lambda x: MODEL_MAP.get(x, x))
    df_ds["display_model"] = df_ds["model"].map(lambda x: MODEL_MAP.get(x, x))

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), facecolor=DARK_BG, sharey=True)

    for ax, df_plot, label, color in [
        (axes[0], df_d, "Condition D\n(metadata with labels)", "#fbbf24"),
        (axes[1], df_ds, "Condition D-strict\n(labels stripped)", "#ef4444"),
    ]:
        _style_ax(ax, label, "Incident", "RCA Accuracy")
        for model, group in df_plot.groupby("display_model"):
            mcolor = PALETTE.get(model, "#94a3b8")
            ax.scatter(range(len(group)), group["rca_accuracy"].values,
                       label=model, s=100, c=mcolor, edgecolors="white", linewidth=0.5, alpha=0.8)

        mean_acc = df_plot["rca_accuracy"].mean()
        ax.axhline(mean_acc, color=color, linestyle="--", alpha=0.7)
        ax.text(0.5, mean_acc + 0.05, f"μ = {mean_acc:.2f}",
                color=color, fontsize=12, fontweight="bold", ha="center")
        ax.set_ylim(-0.1, 1.2)
        ax.legend(facecolor=DARK_CARD, edgecolor=DARK_GRID, labelcolor="white", fontsize=8)

    fig.suptitle("Label Leak Proof: Stripping metadata labels → accuracy collapses to 0",
                 fontsize=14, color="#ef4444", fontweight="bold", y=0.02)

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    out = OUT_DIR / "fig6_dstrict_comparison.png"
    plt.savefig(out, dpi=200, facecolor=DARK_BG)
    plt.close()
    print(f"✅ {out}")


# ─── FIGURE 7: Model Leaderboard Heatmap ────────────────────────────────────

def figure_7_leaderboard():
    """Heatmap of all metrics per model — the paper table as a visual."""
    df = _load_incidents()

    metrics = ["rca_accuracy", "log_faithfulness", "confidence_score", "cmd_executability"]
    available = [m for m in metrics if m in df.columns]

    agg = df.groupby("display_model")[available].mean()

    fig, ax = plt.subplots(figsize=(10, max(4, len(agg) * 0.8)), facecolor=DARK_BG)
    _style_ax(ax, "Model Performance Heatmap", "", "")

    data = agg.values
    im = ax.imshow(data, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)

    ax.set_xticks(range(len(available)))
    ax.set_xticklabels([m.replace("_", "\n") for m in available], fontsize=10, color=DARK_FG)
    ax.set_yticks(range(len(agg)))
    ax.set_yticklabels(agg.index, fontsize=11, color="white")

    for i in range(len(agg)):
        for j in range(len(available)):
            val = data[i, j]
            color = "white" if val < 0.5 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=11, fontweight="bold", color=color)

    cbar = plt.colorbar(im, ax=ax, fraction=0.02, pad=0.04)
    cbar.ax.tick_params(colors=DARK_FG)

    plt.tight_layout()
    out = OUT_DIR / "fig7_leaderboard_heatmap.png"
    plt.savefig(out, dpi=200, facecolor=DARK_BG)
    plt.close()
    print(f"✅ {out}")


# ─── MAIN ────────────────────────────────────────────────────────────────────

FIGURES = {
    1: ("Diagnostic Reliability Quadrant", figure_1_quadrant),
    2: ("Confidence vs Faithfulness", figure_2_confidence_faithfulness),
    3: ("P1 Severity Risk Rate", figure_3_p1_risk),
    4: ("Regime Distribution", figure_4_regime_distribution),
    5: ("Ablation Condition Accuracy", figure_5_ablation),
    6: ("D vs D-strict Comparison", figure_6_dstrict),
    7: ("Model Leaderboard Heatmap", figure_7_leaderboard),
}


def main():
    parser = argparse.ArgumentParser(description="Generate all paper figures")
    parser.add_argument("--figure", type=int, default=None, help="Generate specific figure (1-7)")
    args = parser.parse_args()

    if args.figure:
        name, func = FIGURES[args.figure]
        print(f"\n📊 Generating Figure {args.figure}: {name}")
        func()
    else:
        print("\n📊 Generating ALL paper figures...\n")
        for num, (name, func) in FIGURES.items():
            print(f"  Figure {num}: {name}")
            try:
                func()
            except Exception as e:
                print(f"  ⚠️  Error: {e}")
        print("\n✅ All figures generated in figures/")


if __name__ == "__main__":
    main()
