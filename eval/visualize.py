import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path

MODEL_MAP = {
    "gpt-4-turbo": "GPT-4 Turbo",
    "mistralai/mistral-7b-v0.3": "Mistral-7B",
    "mistralai/mistral-7b-instruct-v0.3": "Mistral-7B",
    "meta/llama-3.1-70b-instruct": "Llama-3.1-70B",
    "meta/llama-3.3-70b-instruct": "Llama-3.3-70B",
    "z-ai/glm4.7": "GLM-4.7 (9B)",
    "nvidia-glm47": "GLM-4.7 (9B)",
    "nvidia-llama": "Llama-3.1-70B",
    "nvidia-mistral": "Mistral-7B",
}

MODEL_COLORS = {
    "GPT-4 Turbo": "#38bdf8",
    "Mistral-7B": "#fbbf24",
    "Llama-3.1-70B": "#f472b6",
    "Llama-3.3-70B": "#fb923c",
    "GLM-4.7 (9B)": "#4ade80",
}

def generate_diagnostic_quadrant():
    csv_path = "results/main_results.csv"
    if not os.path.exists(csv_path):
        print(f"❌ {csv_path} not found. Run evaluations first.")
        return

    df = pd.read_csv(csv_path)
    df['display_model'] = df['model'].map(lambda x: MODEL_MAP.get(x, x))

    plt.figure(figsize=(10, 8), facecolor='#0f172a')
    ax = plt.gca()
    ax.set_facecolor('#0f172a')

    for model, group in df.groupby('display_model'):
        color = MODEL_COLORS.get(model, "#94a3b8")
        plt.scatter(group['log_faithfulness'], group['rca_accuracy'],
                    label=model, s=100, alpha=0.7, edgecolors='white', c=color)

    # Quadrant Lines
    plt.axhline(0.5, color='#475569', linestyle='--', alpha=0.5)
    plt.axvline(0.5, color='#475569', linestyle='--', alpha=0.5)

    # Labels and Titles
    plt.title("Diagnostic Reliability Quadrant", fontsize=18, color='white', pad=20)
    plt.xlabel("Log Faithfulness (Evidence Grounding)", fontsize=12, color='#94a3b8')
    plt.ylabel("RCA Accuracy", fontsize=12, color='#94a3b8')

    # Annotate Quadrants
    quadrant_style = dict(fontsize=14, color='white', fontweight='bold', alpha=0.3)
    plt.text(0.75, 0.75, "TRUSTED\nDIAGNOSIS", ha='center', va='center', **quadrant_style)
    plt.text(0.25, 0.75, "CONFIDENT\nLIAR", ha='center', va='center', **quadrant_style)
    plt.text(0.25, 0.25, "HONEST\nFAILURE", ha='center', va='center', **quadrant_style)
    plt.text(0.75, 0.25, "GROUNDED\nBUT WRONG", ha='center', va='center', **quadrant_style)

    # Aesthetics
    ax.spines['bottom'].set_color('#475569')
    ax.spines['top'].set_color('#475569')
    ax.spines['left'].set_color('#475569')
    ax.spines['right'].set_color('#475569')
    ax.tick_params(colors='#94a3b8', labelsize=10)

    legend = plt.legend(facecolor='#1e293b', edgecolor='#475569', labelcolor='white')

    plt.tight_layout()
    output_path = "figures/diagnostic_quadrant.png"
    plt.savefig(output_path, dpi=150)
    print(f"✅ Generated {output_path}")


def calibration_curve(
    csv_path: str = "results/main_results.csv",
    out: str = "figures/calibration_curve.png",
    n_bins: int = 10,
):
    """
    Reliability diagram: confidence bins (x-axis) vs actual accuracy (y-axis).

    Perfect calibration = diagonal line.
    Models scattered above/below = confidence is not predictive of correctness.
    This proves r=-0.124 visually — reviewers expect this figure.
    """
    df = pd.read_csv(csv_path)
    if "confidence_score" not in df.columns or "rca_accuracy" not in df.columns:
        print("❌ Missing confidence_score or rca_accuracy columns.")
        return

    df["display_model"] = df["model"].map(lambda x: MODEL_MAP.get(x, x))

    bins = np.linspace(0, 1, n_bins + 1)

    fig, ax = plt.subplots(figsize=(7, 7), facecolor="#0f172a")
    ax.set_facecolor("#0f172a")

    # Perfect calibration line
    ax.plot([0, 1], [0, 1], "k--", alpha=0.5, linewidth=1.5, label="Perfect calibration")
    ax.fill_between([0, 1], [0, 1], alpha=0.04, color="white")

    for model, group in df.groupby("display_model"):
        if len(group) < 2:
            continue
        color = MODEL_COLORS.get(model, "#94a3b8")
        bx, by, bn = [], [], []
        for i in range(len(bins) - 1):
            mask = (group["confidence_score"] >= bins[i]) & (group["confidence_score"] < bins[i + 1])
            if mask.sum() > 0:
                bx.append(group.loc[mask, "confidence_score"].mean())
                by.append(group.loc[mask, "rca_accuracy"].mean())
                bn.append(mask.sum())
        if bx:
            ax.plot(bx, by, "o-", label=model, color=color, markersize=7,
                    linewidth=1.8, alpha=0.9)

    ax.set_xlabel("Mean Predicted Confidence", fontsize=12, color="#94a3b8")
    ax.set_ylabel("Fraction Correct (RCA Accuracy)", fontsize=12, color="#94a3b8")
    ax.set_title("Confidence Calibration — K8s RCA Benchmark", fontsize=15, color="white", pad=14)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.tick_params(colors="#94a3b8", labelsize=10)
    for spine in ax.spines.values():
        spine.set_color("#475569")

    ax.legend(facecolor="#1e293b", edgecolor="#475569", labelcolor="white", fontsize=9)
    ax.text(
        0.05, 0.93,
        "Points above diagonal = overconfident\nPoints below diagonal = underconfident",
        transform=ax.transAxes, fontsize=8, color="#94a3b8", va="top",
    )

    plt.tight_layout()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=150)
    print(f"✅ Generated {out}")
    plt.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--quadrant", action="store_true", help="Generate diagnostic quadrant")
    parser.add_argument("--calibration", action="store_true", help="Generate calibration curve")
    args = parser.parse_args()

    run_all = not (args.quadrant or args.calibration)
    if run_all or args.quadrant:
        generate_diagnostic_quadrant()
    if run_all or args.calibration:
        calibration_curve()

