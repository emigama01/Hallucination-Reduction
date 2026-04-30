"""Statistical analysis & error categorization on existing experiment_results.csv.

Computes:
- Bootstrap 95% CIs (10k resamples) on factual accuracy and hallucination rate per method
- McNemar-style paired bootstrap on hallucination rate vs baseline
- Error type categorization (fabrication / overconfident / partial-truth / refusal)
"""
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

random.seed(42)

ROOT = Path(__file__).resolve().parent.parent
RESULTS_CSV = ROOT / "results" / "experiment_results.csv"
OUT_JSON = ROOT / "results" / "stats_summary.json"
ERROR_JSON = ROOT / "results" / "error_analysis.json"

METHODS = ["baseline", "cot", "few_shot", "self_consistency", "rag", "rag_optimized"]
N_BOOT = 10000


def load_rows():
    rows = []
    with open(RESULTS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def bootstrap_mean_ci(values, n_boot=N_BOOT, alpha=0.05):
    if not values:
        return (0.0, 0.0, 0.0)
    n = len(values)
    means = []
    for _ in range(n_boot):
        sample = [values[random.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(n_boot * alpha / 2)]
    hi = means[int(n_boot * (1 - alpha / 2))]
    pt = sum(values) / n
    return (pt, lo, hi)


def paired_bootstrap_diff(a, b, n_boot=N_BOOT, alpha=0.05):
    """a, b are paired lists (same questions). Returns (mean_diff, lo, hi, p_two_sided)."""
    assert len(a) == len(b)
    n = len(a)
    diffs = [a[i] - b[i] for i in range(n)]
    boots = []
    for _ in range(n_boot):
        s = [diffs[random.randrange(n)] for _ in range(n)]
        boots.append(sum(s) / n)
    boots.sort()
    lo = boots[int(n_boot * alpha / 2)]
    hi = boots[int(n_boot * (1 - alpha / 2))]
    pt = sum(diffs) / n
    # two-sided p: fraction of bootstrap means with sign opposite to point estimate
    if pt > 0:
        p = 2 * sum(1 for x in boots if x <= 0) / n_boot
    elif pt < 0:
        p = 2 * sum(1 for x in boots if x >= 0) / n_boot
    else:
        p = 1.0
    p = min(p, 1.0)
    return (pt, lo, hi, p)


def categorize_error(response, correct_answer, is_hallucinated):
    """Light heuristic categorization of wrong/hallucinated responses."""
    if not is_hallucinated:
        return "correct"
    r = (response or "").lower()
    # Refusal / hedge
    refusal_markers = [
        "i don't know", "i do not know", "cannot answer", "i'm not sure",
        "i am not sure", "no clear", "unclear", "depends", "it depends",
        "i can't", "i cannot",
    ]
    if any(m in r for m in refusal_markers):
        return "refusal_or_hedge"
    # Partial-truth: contains some keywords from correct answer
    correct_tokens = set(w.lower().strip(".,;:") for w in (correct_answer or "").split() if len(w) > 3)
    resp_tokens = set(w.lower().strip(".,;:") for w in r.split() if len(w) > 3)
    overlap = correct_tokens & resp_tokens
    if correct_tokens and len(overlap) / max(len(correct_tokens), 1) > 0.25:
        return "partial_truth"
    # Overconfident: long, declarative, no hedging
    word_count = len(r.split())
    hedges = ["might", "perhaps", "may be", "possibly", "likely", "approximately"]
    has_hedge = any(h in r for h in hedges)
    if word_count > 30 and not has_hedge:
        return "overconfident_fabrication"
    return "fabrication"


def main():
    rows = load_rows()
    by_method = defaultdict(list)
    for r in rows:
        by_method[r["phase"]].append(r)

    # Per-method stats with CIs
    summary = {}
    for m in METHODS:
        items = by_method.get(m, [])
        accs = [float(r["factual_accuracy"]) for r in items]
        halls = [int(r["is_hallucinated"] == "True" or r["is_hallucinated"] == "1") for r in items]
        rouges = [float(r["rouge_l"]) for r in items]
        a_pt, a_lo, a_hi = bootstrap_mean_ci(accs)
        h_pt, h_lo, h_hi = bootstrap_mean_ci(halls)
        r_pt, r_lo, r_hi = bootstrap_mean_ci(rouges)
        summary[m] = {
            "n": len(items),
            "accuracy": {"mean": a_pt, "ci_lo": a_lo, "ci_hi": a_hi},
            "hallucination_rate": {"mean": h_pt, "ci_lo": h_lo, "ci_hi": h_hi},
            "rouge_l": {"mean": r_pt, "ci_lo": r_lo, "ci_hi": r_hi},
        }

    # Paired comparisons vs baseline (same question order assumed within each phase)
    base_items = sorted(by_method["baseline"], key=lambda r: r["question"])
    pairs = {}
    for m in METHODS:
        if m == "baseline":
            continue
        m_items = sorted(by_method[m], key=lambda r: r["question"])
        if len(m_items) != len(base_items):
            continue
        a_diff = paired_bootstrap_diff(
            [float(r["factual_accuracy"]) for r in m_items],
            [float(r["factual_accuracy"]) for r in base_items],
        )
        h_diff = paired_bootstrap_diff(
            [int(r["is_hallucinated"] == "True") for r in m_items],
            [int(r["is_hallucinated"] == "True") for r in base_items],
        )
        pairs[m] = {
            "vs_baseline_accuracy_diff": {
                "mean": a_diff[0], "ci_lo": a_diff[1], "ci_hi": a_diff[2], "p": a_diff[3],
            },
            "vs_baseline_hallucination_diff": {
                "mean": h_diff[0], "ci_lo": h_diff[1], "ci_hi": h_diff[2], "p": h_diff[3],
            },
        }
    summary["paired_vs_baseline"] = pairs

    OUT_JSON.write_text(json.dumps(summary, indent=2))
    print(f"Wrote {OUT_JSON}")

    # Error type analysis
    err_counts = defaultdict(lambda: defaultdict(int))
    err_examples = defaultdict(lambda: defaultdict(list))
    for m in METHODS:
        for r in by_method[m]:
            is_hall = r["is_hallucinated"] == "True"
            cat = categorize_error(r["response"], r["correct_answer"], is_hall)
            err_counts[m][cat] += 1
            if cat != "correct" and len(err_examples[m][cat]) < 2:
                err_examples[m][cat].append({
                    "question": r["question"],
                    "response_preview": (r["response"] or "")[:200],
                    "correct_answer": r["correct_answer"],
                })
    error_summary = {
        "counts": {m: dict(err_counts[m]) for m in METHODS},
        "examples": {m: {k: v for k, v in err_examples[m].items()} for m in METHODS},
    }
    ERROR_JSON.write_text(json.dumps(error_summary, indent=2))
    print(f"Wrote {ERROR_JSON}")

    # Print summary
    print("\n=== Accuracy CIs ===")
    for m in METHODS:
        s = summary[m]["accuracy"]
        print(f"  {m:18s}  {s['mean']:.3f}  [{s['ci_lo']:.3f}, {s['ci_hi']:.3f}]")
    print("\n=== Paired diffs vs baseline (accuracy) ===")
    for m, d in pairs.items():
        a = d["vs_baseline_accuracy_diff"]
        print(f"  {m:18s}  Δ={a['mean']:+.3f}  [{a['ci_lo']:+.3f}, {a['ci_hi']:+.3f}]  p={a['p']:.3f}")


if __name__ == "__main__":
    main()
