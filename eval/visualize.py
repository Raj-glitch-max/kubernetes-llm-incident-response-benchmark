import pandas as pd
import matplotlib.pyplot as plt
import os
from pathlib import Path

def generate_diagnostic_quadrant():
    csv_path = "data/incidents.csv"
    if not os.path.exists(csv_path):
        print(f"❌ {csv_path} not found. Run evaluations first.")
        return

    df = pd.read_csv(csv_path)
    
    # Mapping old models to display names
    model_map = {
        "gpt-4-turbo": "GPT-4 Turbo",
        "mistralai/mistral-7b-v0.3": "Mistral-7B",
        "meta/llama-3.1-70b-instruct": "Llama-3.1-70B",
        "z-ai/glm4.7": "GLM-4.7 (9B)",
        "nvidia-glm47": "GLM-4.7 (9B)",
        "nvidia-llama": "Llama-3.1-70B",
        "nvidia-mistral": "Mistral-7B"
    }
    df['display_model'] = df['model'].map(lambda x: model_map.get(x, x))

    plt.figure(figsize=(10, 8), facecolor='#0f172a')
    ax = plt.gca()
    ax.set_facecolor('#0f172a')

    # Color mapping for models
    colors = {
        "GPT-4 Turbo": "#38bdf8",
        "Mistral-7B": "#fbbf24",
        "Llama-3.1-70B": "#f472b6",
        "GLM-4.7 (9B)": "#4ade80"
    }

    for model, group in df.groupby('display_model'):
        color = colors.get(model, "#94a3b8")
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
    output_path = "docs/assets/diagnostic_quadrant.png"
    plt.savefig(output_path, dpi=150)
    print(f"✅ Generated {output_path}")

if __name__ == "__main__":
    generate_diagnostic_quadrant()
