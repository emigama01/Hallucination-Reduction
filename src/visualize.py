"""
Generate visualization charts for the hallucination reduction experiment.
"""

import json
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import seaborn as sns

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")


def load_results():
    df = pd.read_csv(os.path.join(RESULTS_DIR, "experiment_results.csv"))
    with open(os.path.join(RESULTS_DIR, "summary.json")) as f:
        summary = json.load(f)
    return df, summary


def plot_hallucination_rates(summary):
    """Bar chart of hallucination rates across methods."""
    phase_names = {
        "baseline": "Vanilla\nBaseline",
        "cot": "Chain-of-\nThought",
        "few_shot": "Few-Shot",
        "self_consistency": "Self-\nConsistency",
        "rag": "RAG\nPipeline",
        "rag_optimized": "RAG +\nOptimized"
    }
    phases = ["baseline", "cot", "few_shot", "self_consistency", "rag", "rag_optimized"]
    rates = [summary[p]["hallucination_rate"] * 100 for p in phases if p in summary]
    names = [phase_names[p] for p in phases if p in summary]

    colors = ['#e74c3c', '#f39c12', '#f39c12', '#f39c12', '#27ae60', '#2ecc71']

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(names, rates, color=colors, edgecolor='white', linewidth=1.5)

    # Add value labels on bars
    for bar, rate in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
                f'{rate:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=11)

    ax.set_ylabel('Hallucination Rate (%)', fontsize=12)
    ax.set_title('Hallucination Rates Across Methods\n(LLaMA 3.2 3B on TruthfulQA-inspired Dataset)', fontsize=13, fontweight='bold')
    ax.set_ylim(0, max(rates) + 15)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "hallucination_rates.png"), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: hallucination_rates.png")


def plot_accuracy_comparison(summary):
    """Grouped bar chart of accuracy metrics."""
    phase_names = {
        "baseline": "Baseline",
        "cot": "CoT",
        "few_shot": "Few-Shot",
        "self_consistency": "Self-Consist.",
        "rag": "RAG",
        "rag_optimized": "RAG+Opt."
    }
    phases = ["baseline", "cot", "few_shot", "self_consistency", "rag", "rag_optimized"]
    available = [p for p in phases if p in summary]

    rouge_scores = [summary[p]["avg_rouge_l"] for p in available]
    accuracy_scores = [summary[p]["avg_factual_accuracy"] for p in available]
    names = [phase_names[p] for p in available]

    x = np.arange(len(names))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width/2, rouge_scores, width, label='ROUGE-L Score', color='#3498db', alpha=0.85)
    bars2 = ax.bar(x + width/2, accuracy_scores, width, label='Factual Accuracy', color='#e67e22', alpha=0.85)

    ax.set_ylabel('Score', fontsize=12)
    ax.set_title('Factual Accuracy and ROUGE-L Scores by Method', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.legend()
    ax.set_ylim(0, 1.0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "accuracy_comparison.png"), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: accuracy_comparison.png")


def plot_category_heatmap(df):
    """Heatmap of hallucination rates by category and method."""
    phase_order = ["baseline", "cot", "few_shot", "self_consistency", "rag", "rag_optimized"]
    phase_labels = {
        "baseline": "Baseline",
        "cot": "CoT",
        "few_shot": "Few-Shot",
        "self_consistency": "Self-Consist.",
        "rag": "RAG",
        "rag_optimized": "RAG+Opt."
    }

    pivot = df.pivot_table(
        values='is_hallucinated',
        index='category',
        columns='phase',
        aggfunc='mean'
    )

    # Reorder columns
    available_phases = [p for p in phase_order if p in pivot.columns]
    pivot = pivot[available_phases]
    pivot.columns = [phase_labels[p] for p in available_phases]

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(pivot * 100, annot=True, fmt='.0f', cmap='RdYlGn_r',
                ax=ax, vmin=0, vmax=100, linewidths=0.5,
                cbar_kws={'label': 'Hallucination Rate (%)'})
    ax.set_title('Hallucination Rate (%) by Category and Method', fontsize=13, fontweight='bold')
    ax.set_ylabel('Category')
    ax.set_xlabel('Method')

    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "category_heatmap.png"), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: category_heatmap.png")


def plot_reduction_waterfall(summary):
    """Waterfall chart showing progressive hallucination reduction."""
    phases = ["baseline", "self_consistency", "rag", "rag_optimized"]
    phase_labels = ["Baseline", "Self-Consistency", "RAG Pipeline", "RAG + Optimized"]
    available = [(p, l) for p, l in zip(phases, phase_labels) if p in summary]

    if not available:
        return

    rates = [summary[p]["hallucination_rate"] * 100 for p, _ in available]
    labels = [l for _, l in available]

    fig, ax = plt.subplots(figsize=(8, 6))

    colors = []
    for i, rate in enumerate(rates):
        if i == 0:
            colors.append('#e74c3c')
        elif rate < rates[0]:
            colors.append('#27ae60')
        else:
            colors.append('#f39c12')

    ax.bar(labels, rates, color=colors, edgecolor='white', linewidth=1.5)

    for i, (label, rate) in enumerate(zip(labels, rates)):
        ax.text(i, rate + 1.5, f'{rate:.1f}%', ha='center', fontweight='bold', fontsize=12)
        if i > 0:
            reduction = rates[0] - rate
            if reduction > 0:
                ax.annotate(f'-{reduction:.1f}pp',
                           xy=(i, rate), fontsize=9, ha='center',
                           color='green', fontweight='bold',
                           xytext=(i, rate - 5))

    ax.set_ylabel('Hallucination Rate (%)', fontsize=12)
    ax.set_title('Progressive Hallucination Reduction', fontsize=13, fontweight='bold')
    ax.set_ylim(0, max(rates) + 15)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "reduction_waterfall.png"), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: reduction_waterfall.png")


def plot_radar_chart(summary):
    """Radar chart comparing methods across metrics."""
    phases = ["baseline", "cot", "rag", "rag_optimized"]
    phase_labels = ["Baseline", "CoT", "RAG", "RAG+Opt."]
    available = [(p, l) for p, l in zip(phases, phase_labels) if p in summary]

    if len(available) < 2:
        return

    metrics = ['Accuracy Rate', 'Avg ROUGE-L', 'Factual Accuracy']
    n_metrics = len(metrics)

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    angles = np.linspace(0, 2 * np.pi, n_metrics, endpoint=False).tolist()
    angles += angles[:1]

    colors = ['#e74c3c', '#f39c12', '#27ae60', '#2ecc71']

    for idx, (phase, label) in enumerate(available):
        s = summary[phase]
        values = [
            s["accuracy_rate"],
            s["avg_rouge_l"],
            s["avg_factual_accuracy"]
        ]
        values += values[:1]
        ax.plot(angles, values, 'o-', linewidth=2, label=label, color=colors[idx % len(colors)])
        ax.fill(angles, values, alpha=0.1, color=colors[idx % len(colors)])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metrics, fontsize=10)
    ax.set_ylim(0, 1)
    ax.set_title('Method Comparison Across Metrics', fontsize=13, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    ax.grid(True)

    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "radar_comparison.png"), dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: radar_comparison.png")


def main():
    print("Generating visualizations...")
    df, summary = load_results()

    plot_hallucination_rates(summary)
    plot_accuracy_comparison(summary)
    plot_category_heatmap(df)
    plot_reduction_waterfall(summary)
    plot_radar_chart(summary)

    print("\nAll charts saved to results/ directory.")


if __name__ == "__main__":
    main()
