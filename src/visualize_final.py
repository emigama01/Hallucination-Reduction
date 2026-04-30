"""Final-phase charts: accuracy with 95% CI error bars, error-type stacked bars."""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"

METHODS = ["baseline", "cot", "few_shot", "self_consistency", "rag", "rag_optimized"]
LABELS = ["Baseline", "Chain-of-Thought", "Few-Shot", "Self-Consistency", "RAG", "RAG + Optimized"]
COLORS = ["#9aa0a6", "#d97757", "#5b9bd5", "#70ad47", "#ffc000", "#7030a0"]


def chart_accuracy_with_ci():
    s = json.load(open(RES / "stats_summary.json"))
    means = [s[m]["accuracy"]["mean"] for m in METHODS]
    los = [s[m]["accuracy"]["ci_lo"] for m in METHODS]
    his = [s[m]["accuracy"]["ci_hi"] for m in METHODS]
    err_lo = [m - l for m, l in zip(means, los)]
    err_hi = [h - m for m, h in zip(means, his)]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(METHODS))
    bars = ax.bar(x, means, yerr=[err_lo, err_hi], capsize=6,
                  color=COLORS, edgecolor="#222", linewidth=0.8)
    for b, m in zip(bars, means):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.012,
                f"{m:.3f}", ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(LABELS, rotation=15, ha="right")
    ax.set_ylabel("Factual Accuracy (mean ± 95% CI)")
    ax.set_title("Factual Accuracy by Method with Bootstrap 95% Confidence Intervals")
    ax.set_ylim(0, 0.75)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(RES / "accuracy_with_ci.png", dpi=160)
    plt.close()


def chart_error_types():
    e = json.load(open(RES / "error_analysis.json"))
    types = ["correct", "partial_truth", "fabrication", "overconfident_fabrication", "refusal_or_hedge"]
    type_labels = ["Correct", "Partial truth", "Fabrication", "Overconfident fabrication", "Refusal / hedge"]
    type_colors = ["#70ad47", "#ffc000", "#d97757", "#c0504d", "#9aa0a6"]
    counts = e["counts"]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(METHODS))
    bottoms = np.zeros(len(METHODS))
    for t, lab, col in zip(types, type_labels, type_colors):
        vals = np.array([counts[m].get(t, 0) for m in METHODS], dtype=float)
        ax.bar(x, vals, bottom=bottoms, color=col, edgecolor="#222",
               linewidth=0.6, label=lab)
        for i, v in enumerate(vals):
            if v > 0:
                ax.text(i, bottoms[i] + v / 2, int(v), ha="center", va="center",
                        fontsize=9, color="white" if v > 5 else "#222")
        bottoms += vals
    ax.set_xticks(x)
    ax.set_xticklabels(LABELS, rotation=15, ha="right")
    ax.set_ylabel("Number of responses (out of 30)")
    ax.set_title("Response Type Distribution by Method")
    ax.legend(loc="upper right", fontsize=9, framealpha=0.95)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(RES / "error_types.png", dpi=160)
    plt.close()


def chart_paired_diffs():
    s = json.load(open(RES / "stats_summary.json"))
    pairs = s["paired_vs_baseline"]
    methods = [m for m in METHODS if m != "baseline"]
    labels = [LABELS[METHODS.index(m)] for m in methods]
    means = [pairs[m]["vs_baseline_accuracy_diff"]["mean"] for m in methods]
    los = [pairs[m]["vs_baseline_accuracy_diff"]["ci_lo"] for m in methods]
    his = [pairs[m]["vs_baseline_accuracy_diff"]["ci_hi"] for m in methods]
    ps = [pairs[m]["vs_baseline_accuracy_diff"]["p"] for m in methods]
    err_lo = [m - l for m, l in zip(means, los)]
    err_hi = [h - m for m, h in zip(means, his)]
    colors = ["#c0504d" if m < 0 else "#70ad47" for m in means]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = np.arange(len(methods))
    ax.bar(x, means, yerr=[err_lo, err_hi], capsize=6, color=colors,
           edgecolor="#222", linewidth=0.8)
    ax.axhline(0, color="#222", linewidth=0.8)
    for i, (m, p) in enumerate(zip(means, ps)):
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
        offset = 0.015 if m >= 0 else -0.025
        ax.text(i, m + offset, f"Δ={m:+.3f}\n{sig}", ha="center", fontsize=9, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("Δ Factual Accuracy vs Baseline (paired)")
    ax.set_title("Paired Accuracy Improvement over Baseline (10k bootstrap)\n* p<0.05, ** p<0.01, *** p<0.001")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(RES / "paired_diffs.png", dpi=160)
    plt.close()


if __name__ == "__main__":
    chart_accuracy_with_ci()
    chart_error_types()
    chart_paired_diffs()
    print("Wrote: accuracy_with_ci.png, error_types.png, paired_diffs.png")
