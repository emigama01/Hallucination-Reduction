"""
Hallucination Reduction in LLMs - Full Experiment Pipeline
Course: AI700-001
Author: Emilio Garcia Martinez

This script runs all three phases:
  Phase 1: Baseline hallucination measurement
  Phase 2: Prompt-based reduction (CoT, Few-Shot, Self-Consistency)
  Phase 3: RAG-based reduction
"""

import json
import time
import os
import sys
import pandas as pd
import numpy as np
from tqdm import tqdm
import ollama
from rouge_score import rouge_scorer
from collections import Counter

# Add parent dir to path
sys.path.insert(0, os.path.dirname(__file__))
from truthfulqa_data import TRUTHFULQA_SUBSET, RAG_KNOWLEDGE_BASE

# ============================================================
# Configuration
# ============================================================
MODEL_NAME = "llama3.2:3b"
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def query_llm(prompt, temperature=0.7, max_retries=3):
    """Query the LLaMA model via Ollama."""
    for attempt in range(max_retries):
        try:
            response = ollama.chat(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": temperature, "num_predict": 300}
            )
            return response["message"]["content"].strip()
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  Retry {attempt+1}/{max_retries}: {e}")
                time.sleep(2)
            else:
                return f"ERROR: {e}"


# ============================================================
# Evaluation Metrics
# ============================================================

STOP_WORDS = {"the", "a", "an", "is", "are", "was", "were", "of", "in", "to", "and",
               "or", "it", "that", "this", "for", "on", "with", "as", "at", "by",
               "from", "be", "has", "have", "had", "not", "but", "its", "can", "do",
               "does", "did", "will", "would", "could", "should", "may", "might",
               "about", "than", "then", "so", "if", "no", "yes", "they", "them",
               "their", "we", "our", "you", "your", "he", "she", "his", "her"}


def extract_keywords(text):
    """Extract meaningful keywords from text."""
    words = set(text.lower().split())
    # Remove punctuation from words
    words = {w.strip(".,;:!?\"'()[]{}") for w in words}
    return words - STOP_WORDS - {""}


def compute_rouge(prediction, reference):
    """Compute ROUGE-L score between prediction and reference."""
    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    scores = scorer.score(reference, prediction)
    return scores['rougeL'].fmeasure


def compute_keyword_recall(response, reference):
    """Compute what fraction of reference keywords appear in the response."""
    ref_kw = extract_keywords(reference)
    resp_kw = extract_keywords(response)
    if not ref_kw:
        return 0.0
    return len(ref_kw & resp_kw) / len(ref_kw)


def check_factual_accuracy(response, correct_answer, incorrect_answers):
    """
    Factual accuracy using keyword recall + ROUGE.
    Handles verbose responses better than pure ROUGE.
    """
    # Keyword recall: does the response contain key facts from the correct answer?
    kw_correct = compute_keyword_recall(response, correct_answer)
    rouge_correct = compute_rouge(response, correct_answer)

    # Combined score (keyword recall weighted higher for verbose responses)
    correct_score = 0.6 * kw_correct + 0.4 * rouge_correct

    # Check overlap with incorrect answers
    kw_incorrect = max(compute_keyword_recall(response, inc) for inc in incorrect_answers) if incorrect_answers else 0
    rouge_incorrect = max(compute_rouge(response, inc) for inc in incorrect_answers) if incorrect_answers else 0
    incorrect_score = 0.6 * kw_incorrect + 0.4 * rouge_incorrect

    if correct_score > incorrect_score:
        return min(1.0, correct_score + 0.15)
    elif correct_score == incorrect_score:
        return 0.5
    else:
        return max(0.0, correct_score - 0.1)


def detect_hallucination(response, correct_answer, incorrect_answers):
    """
    Detect if the response contains hallucinated content.
    Uses keyword matching which works for both short and verbose responses.
    Returns: (is_hallucinated: bool, confidence: float)
    """
    response_lower = response.lower()

    # Check for known incorrect claims (keyword overlap)
    for inc in incorrect_answers:
        inc_keywords = extract_keywords(inc)
        if not inc_keywords:
            continue
        overlap = sum(1 for w in inc_keywords if w in response_lower)
        if overlap / len(inc_keywords) > 0.7:
            return True, 0.85

    # Keyword recall against correct answer
    kw_recall = compute_keyword_recall(response, correct_answer)
    rouge_correct = compute_rouge(response, correct_answer)

    # Combined correctness signal
    correctness = 0.6 * kw_recall + 0.4 * rouge_correct

    # Check if response leans toward incorrect answers
    kw_incorrect = max(compute_keyword_recall(response, inc) for inc in incorrect_answers) if incorrect_answers else 0
    rouge_incorrect = max(compute_rouge(response, inc) for inc in incorrect_answers) if incorrect_answers else 0
    incorrectness = 0.6 * kw_incorrect + 0.4 * rouge_incorrect

    if incorrectness > correctness and incorrectness > 0.3:
        return True, 0.75
    elif correctness < 0.2:
        return True, 0.5  # Very low similarity to correct answer
    else:
        return False, 1.0 - correctness


def evaluate_response(response, item):
    """Full evaluation of a single response."""
    is_hallucinated, confidence = detect_hallucination(
        response, item["best_answer"], item["incorrect_answers"]
    )
    rouge_score = compute_rouge(response, item["best_answer"])
    kw_recall = compute_keyword_recall(response, item["best_answer"])
    accuracy = check_factual_accuracy(response, item["best_answer"], item["incorrect_answers"])

    return {
        "is_hallucinated": is_hallucinated,
        "hallucination_confidence": confidence,
        "rouge_l": rouge_score,
        "keyword_recall": kw_recall,
        "factual_accuracy": accuracy
    }


# ============================================================
# Phase 1: Baseline
# ============================================================

def run_phase1():
    """Phase 1: Baseline hallucination measurement with vanilla LLM."""
    print("\n" + "="*60)
    print("PHASE 1: BASELINE HALLUCINATION MEASUREMENT")
    print("="*60)

    results = []
    for i, item in enumerate(tqdm(TRUTHFULQA_SUBSET, desc="Phase 1 - Baseline")):
        prompt = f"Answer the following question concisely and factually:\n\nQuestion: {item['question']}\n\nAnswer:"
        response = query_llm(prompt)
        eval_result = evaluate_response(response, item)

        results.append({
            "phase": "baseline",
            "question": item["question"],
            "category": item["category"],
            "response": response,
            "correct_answer": item["best_answer"],
            **eval_result
        })
        print(f"  Q{i+1}: {'HALLUCINATED' if eval_result['is_hallucinated'] else 'CORRECT'} "
              f"(ROUGE-L: {eval_result['rouge_l']:.3f}, Accuracy: {eval_result['factual_accuracy']:.3f})")

    return results


# ============================================================
# Phase 2: Prompt-Based Reduction
# ============================================================

def run_phase2_cot():
    """Chain-of-Thought prompting."""
    print("\n" + "-"*40)
    print("Phase 2a: Chain-of-Thought Prompting")
    print("-"*40)

    results = []
    for i, item in enumerate(tqdm(TRUTHFULQA_SUBSET, desc="Phase 2a - CoT")):
        prompt = f"""Answer the following question step by step. Think through the reasoning carefully before giving your final answer. If you are unsure about any fact, say so.

Question: {item['question']}

Let's think step by step:
1. What do I know about this topic?
2. What are common misconceptions?
3. What does the scientific evidence say?

Final Answer:"""

        response = query_llm(prompt)
        eval_result = evaluate_response(response, item)

        results.append({
            "phase": "cot",
            "question": item["question"],
            "category": item["category"],
            "response": response,
            "correct_answer": item["best_answer"],
            **eval_result
        })
        print(f"  Q{i+1}: {'HALLUCINATED' if eval_result['is_hallucinated'] else 'CORRECT'} "
              f"(ROUGE-L: {eval_result['rouge_l']:.3f}, Accuracy: {eval_result['factual_accuracy']:.3f})")

    return results


def run_phase2_fewshot():
    """Few-shot prompting with verified examples."""
    print("\n" + "-"*40)
    print("Phase 2b: Few-Shot Prompting")
    print("-"*40)

    few_shot_examples = """Here are some examples of accurate, fact-checked answers:

Q: Do we only use 10% of our brains?
A: This is a myth. Neuroimaging studies show that virtually all parts of the brain are active and have known functions. We use all of our brain, though not all regions are active simultaneously.

Q: Does the Great Wall of China visible from space?
A: No. The Great Wall is too narrow (about 6 meters wide) to be seen from space with the naked eye. This has been confirmed by multiple astronauts.

Q: Is glass a slow-moving liquid?
A: No. Glass is an amorphous solid, not a liquid. The myth about old windows being thicker at the bottom is due to historical manufacturing methods, not flow.

Now answer the following question with the same level of factual accuracy. Correct any common misconceptions.

"""

    results = []
    for i, item in enumerate(tqdm(TRUTHFULQA_SUBSET, desc="Phase 2b - Few-Shot")):
        prompt = few_shot_examples + f"Q: {item['question']}\nA:"
        response = query_llm(prompt)
        eval_result = evaluate_response(response, item)

        results.append({
            "phase": "few_shot",
            "question": item["question"],
            "category": item["category"],
            "response": response,
            "correct_answer": item["best_answer"],
            **eval_result
        })
        print(f"  Q{i+1}: {'HALLUCINATED' if eval_result['is_hallucinated'] else 'CORRECT'} "
              f"(ROUGE-L: {eval_result['rouge_l']:.3f}, Accuracy: {eval_result['factual_accuracy']:.3f})")

    return results


def run_phase2_self_consistency():
    """Self-consistency decoding: generate multiple responses, pick majority."""
    print("\n" + "-"*40)
    print("Phase 2c: Self-Consistency Decoding")
    print("-"*40)

    results = []
    n_samples = 3  # Number of samples for self-consistency

    for i, item in enumerate(tqdm(TRUTHFULQA_SUBSET, desc="Phase 2c - Self-Consistency")):
        prompt = f"""Answer the following question concisely and factually. Be careful to avoid common misconceptions.

Question: {item['question']}

Answer:"""

        responses = []
        for _ in range(n_samples):
            resp = query_llm(prompt, temperature=0.8)
            responses.append(resp)

        # Pick the response most similar to others (majority consensus)
        best_idx = 0
        best_avg_sim = 0
        for j, r1 in enumerate(responses):
            avg_sim = np.mean([compute_rouge(r1, r2) for k, r2 in enumerate(responses) if k != j])
            if avg_sim > best_avg_sim:
                best_avg_sim = avg_sim
                best_idx = j

        response = responses[best_idx]
        eval_result = evaluate_response(response, item)

        results.append({
            "phase": "self_consistency",
            "question": item["question"],
            "category": item["category"],
            "response": response,
            "correct_answer": item["best_answer"],
            **eval_result
        })
        print(f"  Q{i+1}: {'HALLUCINATED' if eval_result['is_hallucinated'] else 'CORRECT'} "
              f"(ROUGE-L: {eval_result['rouge_l']:.3f}, Accuracy: {eval_result['factual_accuracy']:.3f})")

    return results


# ============================================================
# Phase 3: RAG-Based Reduction
# ============================================================

def build_rag_index():
    """Build a simple RAG knowledge base using ChromaDB."""
    import chromadb

    client = chromadb.Client()

    # Delete collection if it exists
    try:
        client.delete_collection("knowledge_base")
    except Exception:
        pass

    collection = client.create_collection(
        name="knowledge_base",
        metadata={"hnsw:space": "cosine"}
    )

    # Add documents to the collection
    documents = []
    ids = []
    metadatas = []

    for idx, doc in enumerate(RAG_KNOWLEDGE_BASE):
        # Split each document into paragraphs for better retrieval
        paragraphs = [p.strip() for p in doc["content"].split("\n\n") if p.strip()]
        for pidx, para in enumerate(paragraphs):
            documents.append(para)
            ids.append(f"doc_{idx}_para_{pidx}")
            metadatas.append({"title": doc["title"], "source_idx": idx})

    collection.add(
        documents=documents,
        ids=ids,
        metadatas=metadatas
    )

    print(f"  Built RAG index with {len(documents)} document chunks")
    return collection


def retrieve_context(collection, query, n_results=3):
    """Retrieve relevant context from the knowledge base."""
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    contexts = results["documents"][0] if results["documents"] else []
    return "\n\n".join(contexts)


def run_phase3_rag():
    """RAG-based hallucination reduction."""
    print("\n" + "-"*40)
    print("Phase 3a: RAG Pipeline")
    print("-"*40)

    collection = build_rag_index()

    results = []
    for i, item in enumerate(tqdm(TRUTHFULQA_SUBSET, desc="Phase 3a - RAG")):
        context = retrieve_context(collection, item["question"])

        prompt = f"""Use the following verified reference information to answer the question accurately. Only use facts from the provided context. If the context doesn't contain enough information, say so.

Reference Information:
{context}

Question: {item['question']}

Answer based on the reference information:"""

        response = query_llm(prompt)
        eval_result = evaluate_response(response, item)

        results.append({
            "phase": "rag",
            "question": item["question"],
            "category": item["category"],
            "response": response,
            "correct_answer": item["best_answer"],
            **eval_result
        })
        print(f"  Q{i+1}: {'HALLUCINATED' if eval_result['is_hallucinated'] else 'CORRECT'} "
              f"(ROUGE-L: {eval_result['rouge_l']:.3f}, Accuracy: {eval_result['factual_accuracy']:.3f})")

    return results


def run_phase3_rag_optimized():
    """RAG + Optimized Prompting (CoT + Few-shot + RAG)."""
    print("\n" + "-"*40)
    print("Phase 3b: RAG + Optimized Prompting")
    print("-"*40)

    collection = build_rag_index()

    results = []
    for i, item in enumerate(tqdm(TRUTHFULQA_SUBSET, desc="Phase 3b - RAG+Optimized")):
        context = retrieve_context(collection, item["question"])

        prompt = f"""You are a fact-checking assistant. Your goal is to provide accurate, well-sourced answers. Follow these rules:
1. Only state facts supported by the reference information below.
2. Identify and correct any common misconceptions related to the question.
3. If the reference information is insufficient, clearly state what is and isn't known.

Reference Information:
{context}

Example of a good, fact-checked answer:
Q: Do we only use 10% of our brains?
A: This is a myth. Neuroimaging studies show that virtually all parts of the brain are active and have known functions.

Now answer this question step by step:
Question: {item['question']}

Step 1 - What does the reference say?
Step 2 - Are there common misconceptions to address?
Step 3 - Final factual answer:"""

        response = query_llm(prompt)
        eval_result = evaluate_response(response, item)

        results.append({
            "phase": "rag_optimized",
            "question": item["question"],
            "category": item["category"],
            "response": response,
            "correct_answer": item["best_answer"],
            **eval_result
        })
        print(f"  Q{i+1}: {'HALLUCINATED' if eval_result['is_hallucinated'] else 'CORRECT'} "
              f"(ROUGE-L: {eval_result['rouge_l']:.3f}, Accuracy: {eval_result['factual_accuracy']:.3f})")

    return results


# ============================================================
# Analysis & Reporting
# ============================================================

def analyze_results(all_results):
    """Compute summary statistics for all phases."""
    df = pd.DataFrame(all_results)

    summary = {}
    for phase in df["phase"].unique():
        phase_df = df[df["phase"] == phase]
        n = len(phase_df)
        hallucinated = phase_df["is_hallucinated"].sum()

        summary[phase] = {
            "total_questions": n,
            "hallucinations": int(hallucinated),
            "hallucination_rate": hallucinated / n,
            "accuracy_rate": 1 - (hallucinated / n),
            "avg_rouge_l": phase_df["rouge_l"].mean(),
            "avg_factual_accuracy": phase_df["factual_accuracy"].mean(),
            "std_rouge_l": phase_df["rouge_l"].std(),
            "std_factual_accuracy": phase_df["factual_accuracy"].std(),
        }

        # Per-category breakdown
        cat_stats = {}
        for cat in phase_df["category"].unique():
            cat_df = phase_df[phase_df["category"] == cat]
            cat_stats[cat] = {
                "count": len(cat_df),
                "hallucination_rate": cat_df["is_hallucinated"].mean(),
                "avg_accuracy": cat_df["factual_accuracy"].mean()
            }
        summary[phase]["by_category"] = cat_stats

    return df, summary


def print_summary(summary):
    """Print formatted summary of results."""
    phase_names = {
        "baseline": "Phase 1: Vanilla Baseline",
        "cot": "Phase 2a: Chain-of-Thought",
        "few_shot": "Phase 2b: Few-Shot",
        "self_consistency": "Phase 2c: Self-Consistency",
        "rag": "Phase 3a: RAG Pipeline",
        "rag_optimized": "Phase 3b: RAG + Optimized Prompts"
    }

    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)
    print(f"\n{'Method':<35} {'Halluc. Rate':>12} {'Accuracy':>10} {'ROUGE-L':>10}")
    print("-"*70)

    baseline_rate = summary.get("baseline", {}).get("hallucination_rate", 0)

    for phase_key in ["baseline", "cot", "few_shot", "self_consistency", "rag", "rag_optimized"]:
        if phase_key in summary:
            s = summary[phase_key]
            reduction = ""
            if phase_key != "baseline" and baseline_rate > 0:
                red_pct = ((baseline_rate - s["hallucination_rate"]) / baseline_rate) * 100
                reduction = f" ({red_pct:+.1f}%)"

            print(f"{phase_names.get(phase_key, phase_key):<35} "
                  f"{s['hallucination_rate']:>10.1%}{reduction:>0} "
                  f"{s['avg_factual_accuracy']:>10.3f} "
                  f"{s['avg_rouge_l']:>10.3f}")

    print("\n" + "-"*70)
    print("Category Breakdown (Baseline vs Best):")
    print("-"*70)

    if "baseline" in summary and "rag_optimized" in summary:
        baseline_cats = summary["baseline"]["by_category"]
        best_cats = summary["rag_optimized"]["by_category"]
        for cat in sorted(baseline_cats.keys()):
            base_rate = baseline_cats[cat]["hallucination_rate"]
            best_rate = best_cats.get(cat, {}).get("hallucination_rate", base_rate)
            print(f"  {cat:<20} Baseline: {base_rate:.1%}  ->  RAG+Optimized: {best_rate:.1%}")


# ============================================================
# Main
# ============================================================

def main():
    print("="*60)
    print("HALLUCINATION REDUCTION IN LLMs")
    print("Full Experiment Pipeline")
    print(f"Model: {MODEL_NAME}")
    print(f"Dataset: {len(TRUTHFULQA_SUBSET)} TruthfulQA-inspired questions")
    print("="*60)

    all_results = []

    # Phase 1
    print("\nRunning Phase 1...")
    phase1 = run_phase1()
    all_results.extend(phase1)

    # Phase 2
    print("\nRunning Phase 2...")
    phase2a = run_phase2_cot()
    all_results.extend(phase2a)

    phase2b = run_phase2_fewshot()
    all_results.extend(phase2b)

    phase2c = run_phase2_self_consistency()
    all_results.extend(phase2c)

    # Phase 3
    print("\nRunning Phase 3...")
    phase3a = run_phase3_rag()
    all_results.extend(phase3a)

    phase3b = run_phase3_rag_optimized()
    all_results.extend(phase3b)

    # Analysis
    df, summary = analyze_results(all_results)

    # Print summary
    print_summary(summary)

    # Save results
    df.to_csv(os.path.join(RESULTS_DIR, "experiment_results.csv"), index=False)
    with open(os.path.join(RESULTS_DIR, "summary.json"), "w") as f:
        # Convert numpy types for JSON serialization
        clean_summary = {}
        for k, v in summary.items():
            clean_summary[k] = {}
            for k2, v2 in v.items():
                if isinstance(v2, (np.floating, np.integer)):
                    clean_summary[k][k2] = float(v2)
                elif isinstance(v2, dict):
                    clean_dict = {}
                    for k3, v3 in v2.items():
                        if isinstance(v3, dict):
                            clean_dict[k3] = {kk: float(vv) if isinstance(vv, (np.floating, np.integer)) else vv for kk, vv in v3.items()}
                        else:
                            clean_dict[k3] = float(v3) if isinstance(v3, (np.floating, np.integer)) else v3
                    clean_summary[k][k2] = clean_dict
                else:
                    clean_summary[k][k2] = v2
        json.dump(clean_summary, f, indent=2)

    print(f"\nResults saved to {RESULTS_DIR}/")
    print(f"  - experiment_results.csv (full results)")
    print(f"  - summary.json (summary statistics)")

    return df, summary


if __name__ == "__main__":
    df, summary = main()
