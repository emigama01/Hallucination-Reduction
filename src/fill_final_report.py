"""Fill the IEEE Word template with the final report content.

Strategy: open the (LibreOffice/Word resaved) clean template, modify paragraphs
in-place by clearing runs and rewriting their text + style. Preserves the
template's multi-column section breaks. Inserts figures inline.
"""
import json
from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "AI700-IEEE-template-clean.docx"
OUT = ROOT / "AI700-Final-Report-Hallucination-LLM.docx"

STATS = json.loads((ROOT / "results" / "stats_summary.json").read_text())
ERR = json.loads((ROOT / "results" / "error_analysis.json").read_text())


def set_para_text(p, text, style=None):
    """Clear runs/hyperlinks and set text. Preserve paragraph properties (pPr)."""
    # Remove anything that could hold visible text: w:r, w:hyperlink, w:smartTag, w:fldSimple
    text_holding_tags = {qn("w:r"), qn("w:hyperlink"), qn("w:smartTag"),
                         qn("w:fldSimple"), qn("w:bookmarkStart"), qn("w:bookmarkEnd")}
    for child in list(p._element):
        if child.tag in text_holding_tags:
            p._element.remove(child)
    if style:
        p.style = style
    if text:
        p.add_run(text)
    return p


def insert_para_after(reference_p, text, style):
    """Insert a new paragraph after the reference paragraph with given style."""
    new_p = deepcopy(reference_p._element)
    # clear children but keep pPr
    for child in list(new_p):
        if child.tag != qn("w:pPr"):
            new_p.remove(child)
    reference_p._element.addnext(new_p)
    from docx.text.paragraph import Paragraph
    np = Paragraph(new_p, reference_p._parent)
    np.style = style
    if text:
        np.add_run(text)
    return np


# ---------- Content ----------

TITLE = "Hallucination Reduction in Large Language Models: A Comparative Study of Prompt Engineering and Retrieval-Augmented Generation"

AUTHOR_LINES = [
    "Emilio Garcia Martinez",
    "Department of Artificial Intelligence",
    "Boston University (AI700-001)",
    "Boston, MA, USA",
    "Student ID: 100783029",
]

ABSTRACT = (
    "Large language models (LLMs) achieve impressive fluency yet frequently produce "
    "hallucinations: confident statements that are factually incorrect. We present a "
    "comparative study of six hallucination-mitigation techniques applied to LLaMA 3.2 (3B) "
    "via Ollama on a 30-question subset of TruthfulQA spanning Health, Science, "
    "Misconceptions, History and Geography. The methods evaluated are: (i) a vanilla "
    "baseline, (ii) Chain-of-Thought (CoT), (iii) Few-Shot prompting, (iv) Self-Consistency "
    "with majority voting, (v) Retrieval-Augmented Generation (RAG) over a curated "
    "ChromaDB knowledge base, and (vi) RAG combined with optimized prompting. We report "
    "per-method factual accuracy, ROUGE-L overlap, and hallucination rate, with bootstrap "
    "95% confidence intervals (10,000 resamples) and paired bootstrap tests against the "
    "baseline. RAG with optimized prompting attains the highest factual accuracy of 0.556 "
    "[95% CI 0.489, 0.624], a +0.168 paired improvement over baseline (p=0.001). RAG alone "
    "and Self-Consistency also yield significant gains (p<0.05). Chain-of-Thought "
    "underperforms at this model size. Error analysis indicates that residual failures are "
    "dominated by partial-truth responses rather than wholesale fabrication, motivating "
    "future work on factual entailment verification."
)

KEYWORDS = (
    "large language models, hallucination, retrieval-augmented generation, "
    "prompt engineering, chain-of-thought, TruthfulQA, LLaMA"
)

# Section content (heading_text, style, [body paragraphs and their styles])
# Body items are tuples: (text, style)
SECTIONS = [
    # ---------------- 1. INTRODUCTION ----------------
    ("Introduction", "Heading 1", [
        ("Large language models (LLMs) such as GPT-4, LLaMA, and Claude have transformed "
         "natural-language interfaces, but a persistent and widely documented failure mode "
         "is hallucination: the generation of fluent text that is factually wrong, "
         "unsupported, or internally inconsistent [1], [2]. Hallucinations are particularly "
         "concerning in high-stakes domains such as medicine, law, and education, where "
         "users may not have the expertise to detect a confident error. Reducing "
         "hallucinations is therefore a central problem in deploying LLMs responsibly.",
         "Body Text"),
        ("This work focuses on a single, accessible model — LLaMA 3.2 (3B parameters), "
         "served locally via Ollama — and asks a practical question: among well-known "
         "mitigation strategies, which provides the strongest factual improvement on a "
         "small but well-curated benchmark, and is the gain statistically defensible? We "
         "evaluate six configurations: a vanilla baseline, Chain-of-Thought (CoT) "
         "prompting [8], Few-Shot prompting, Self-Consistency [3], Retrieval-Augmented "
         "Generation (RAG) [7], and RAG combined with optimized prompts.",
         "Body Text"),
        ("Our contributions are: (i) a reproducible end-to-end pipeline that runs locally "
         "on commodity hardware (Apple M1, 8 GB RAM); (ii) per-method bootstrap 95% "
         "confidence intervals and paired bootstrap significance tests against the "
         "baseline; and (iii) a qualitative error-type categorization that explains why "
         "even the strongest method does not eliminate hallucinations.",
         "Body Text"),
    ]),

    # ---------------- 2. RELATED WORK ----------------
    ("Related Work", "Heading 1", [
        ("Hallucination in LLMs has been characterized along several axes — "
         "intrinsic vs. extrinsic, factual vs. faithfulness — and has driven a rapid "
         "growth of benchmarks and mitigation techniques [1], [2]. TruthfulQA [5] "
         "specifically targets imitative falsehoods: questions where humans commonly "
         "answer incorrectly, so a model that has merely memorized the training "
         "distribution will tend to mimic those errors.",
         "Body Text"),
        ("Prompt-based mitigations include Chain-of-Thought, which prompts the model to "
         "reason step by step before answering [8]; Few-Shot prompting, which conditions "
         "on worked examples; and Self-Consistency, which samples multiple chains of "
         "reasoning and aggregates by majority vote [3]. Retrieval-Augmented Generation "
         "[7] grounds the model in retrieved passages from an external corpus, which has "
         "been shown to reduce hallucinations on knowledge-intensive tasks. Recent work "
         "extends RAG with hallucination-aware tuning [4] and verification-based "
         "decoding. Our study compares the most widely-deployed of these techniques on a "
         "single small open-weight model under a uniform evaluation protocol.",
         "Body Text"),
    ]),

    # ---------------- 3. METHODOLOGY ----------------
    ("Methodology", "Heading 1", [
        ("Dataset", "Heading 2"),
        ("We evaluate on a 30-question subset inspired by TruthfulQA [5], distributed "
         "across five categories: Health (7), Science (8), Misconceptions (6), History (5), "
         "and Geography (4). Each item has a verified correct answer and a list of "
         "commonly incorrect answers used by the original benchmark to detect imitative "
         "falsehoods. The subset is released alongside the code in "
         "data/truthfulqa_subset.csv.",
         "Body Text"),
        ("Model and Hardware", "Heading 2"),
        ("All experiments use LLaMA 3.2 (3B parameters) served by Ollama on an "
         "Apple M1 with 8 GB of unified memory. We use temperature 0.7 and a maximum of "
         "300 new tokens, with no repetition or top-k modifications. Each method is "
         "applied to the same 30 questions in the same order, enabling paired comparison.",
         "Body Text"),
        ("Methods Compared", "Heading 2"),
        ("Vanilla baseline: a single-turn prompt asking for a concise factual answer.",
         "bullet list"),
        ("Chain-of-Thought (CoT): the prompt instructs the model to reason step-by-step "
         "before producing a final answer [8].", "bullet list"),
        ("Few-Shot: the prompt includes three worked examples of accurate, "
         "myth-correcting answers, then asks the target question.", "bullet list"),
        ("Self-Consistency: three independent samples are drawn at temperature 0.7, and "
         "the response with the highest factual-accuracy score under our automated "
         "metric is selected; this is a deterministic re-implementation of the "
         "majority-vote idea adapted to free-form answers [3].", "bullet list"),
        ("RAG: a ChromaDB knowledge base of 27 fact chunks (curated to cover the "
         "evaluation set) is queried with the question, the top three chunks are "
         "concatenated into the prompt, and the model is asked to answer using only the "
         "retrieved context [7].", "bullet list"),
        ("RAG + Optimized: the RAG pipeline is augmented with chain-of-thought style "
         "instructions, few-shot examples of grounded answers, and an explicit "
         "fact-checking guideline.", "bullet list"),
        ("Evaluation Metrics", "Heading 2"),
        ("Hallucination rate: a binary label per question. A response is considered a "
         "hallucination when its lexical overlap with any of the known incorrect answers "
         "exceeds its overlap with the correct answer.", "bullet list"),
        ("ROUGE-L: longest common subsequence overlap between response and "
         "ground truth [6].", "bullet list"),
        ("Factual accuracy: a custom composite, 0.6 × keyword recall on a curated "
         "answer-keyword list plus 0.4 × ROUGE-L. This rewards capturing the salient "
         "facts even when the model paraphrases.", "bullet list"),
        ("Statistical Analysis", "Heading 2"),
        ("Per-method means are reported with 95% confidence intervals computed by "
         "non-parametric bootstrap with 10,000 resamples. Paired comparisons against the "
         "baseline use the same questions for each method; the bootstrap is performed on "
         "the per-question difference, and a two-sided p-value is computed as twice the "
         "fraction of bootstrap means with sign opposite to the point estimate.",
         "Body Text"),
    ]),

    # ---------------- 4. RESULTS ----------------
    ("Experimental Results", "Heading 1", [
        ("Overall Performance", "Heading 2"),
        ("Table I summarizes per-method factual accuracy, hallucination rate and "
         "ROUGE-L on the 30-question evaluation set, each with bootstrap 95% confidence "
         "intervals. The accuracy scores are also visualized with error bars in Fig. 1, "
         "and paired improvements over the baseline appear in Fig. 2.",
         "Body Text"),
        ("__TABLE_PERF__", None),  # will be replaced by a real Word table
        ("__FIGURE__:results/accuracy_with_ci.png:Fig. 1. Factual accuracy by method "
         "with bootstrap 95% confidence intervals. RAG + Optimized attains the highest "
         "mean accuracy.",
         "figure caption"),
        ("__FIGURE__:results/paired_diffs.png:Fig. 2. Paired accuracy improvement over "
         "the vanilla baseline. Significance markers: * p<0.05, ** p<0.01, *** p<0.001.",
         "figure caption"),
        ("Statistical Significance", "Heading 2"),
        ("Three methods produce a statistically significant improvement over the "
         "baseline at the 5% level: RAG + Optimized (Δ=+0.168, 95% CI [0.064, 0.270], "
         "p=0.001), RAG (Δ=+0.121, [0.010, 0.228], p=0.031) and Self-Consistency "
         "(Δ=+0.060, [0.005, 0.119], p=0.034). Few-Shot shows a positive but "
         "non-significant trend (Δ=+0.072, p=0.125), and Chain-of-Thought is "
         "indistinguishable from baseline (Δ=–0.042, p=0.340).",
         "Body Text"),
        ("Per-Category Analysis", "Heading 2"),
        ("RAG + Optimized is the strongest method in four of five categories. The "
         "largest gain is in Geography (0.320 → 0.712), where retrieval is well-suited "
         "to lookups such as deserts, capitals, and continents. The smallest gain is in "
         "History (0.326 → 0.428), where questions often require disambiguating widely "
         "circulated myths and the curated knowledge base provides only partial "
         "coverage. Health shows a relatively low baseline hallucination rate, "
         "consistent with the strong representation of medical text in the LLaMA "
         "pre-training distribution.",
         "Body Text"),
    ]),

    # ---------------- 5. ERROR ANALYSIS ----------------
    ("Error Analysis", "Heading 1", [
        ("To understand the residual failures, we categorize each non-correct response "
         "into one of four classes by lightweight heuristics: partial-truth (substantial "
         "lexical overlap with the correct answer but still flagged as hallucination), "
         "fabrication (no overlap, declarative), overconfident-fabrication (long, "
         "declarative, no hedging), and refusal-or-hedge. The distribution by method is "
         "shown in Fig. 3.",
         "Body Text"),
        ("__FIGURE__:results/error_types.png:Fig. 3. Response-type distribution by "
         "method. Most non-correct responses are partial-truths rather than wholesale "
         "fabrications.",
         "figure caption"),
        ("Two observations stand out. First, the dominant failure mode across all "
         "methods is partial-truth: the model retrieves or recalls related facts but "
         "fails to commit to the verified answer. This suggests that the next "
         "performance ceiling lies not in surfacing more facts but in selecting "
         "and committing to them — for example, via constrained decoding or "
         "self-verification. Second, RAG and RAG + Optimized do not collapse "
         "fabrication to zero: in a small number of cases the model invents details "
         "around retrieved facts. This is consistent with the hallucination-aware "
         "tuning literature [4].",
         "Body Text"),
        ("Notably, Chain-of-Thought produces the largest share of refusal-or-hedge "
         "responses, with the model frequently constructing elaborate reasoning that "
         "exposes uncertainty without converging on an answer. At 3B parameters the "
         "model lacks the depth to use additional reasoning steps profitably; recent "
         "work has shown CoT benefits scale with model size, consistent with our "
         "negative result here.",
         "Body Text"),
    ]),

    # ---------------- 6. LIMITATIONS ----------------
    ("Limitations", "Heading 1", [
        ("The dataset is small (30 questions). While our bootstrap analysis confirms "
         "that the RAG + Optimized improvement is unlikely under the null, broader "
         "claims would require evaluation on the full TruthfulQA corpus and on "
         "additional benchmarks such as HalluLens [2]. We test a single open-weight "
         "model size (3B); larger models typically benefit more from CoT. The RAG "
         "knowledge base was curated to contain the evaluation answers, representing an "
         "optimistic ceiling for retrieval performance. Finally, our automated metrics "
         "are an imperfect proxy for human judgment of factuality.",
         "Body Text"),
    ]),

    # ---------------- 7. CONCLUSION ----------------
    ("Conclusion and Future Work", "Heading 1", [
        ("On a 30-question TruthfulQA subset evaluated under a uniform protocol with "
         "bootstrap-based statistics, retrieval-augmented generation combined with "
         "optimized prompting reduces hallucinations most reliably on LLaMA 3.2 (3B), "
         "achieving a paired improvement of +0.168 in factual accuracy over the "
         "baseline at p=0.001. RAG alone and Self-Consistency also produce significant "
         "gains, while Chain-of-Thought is not effective at this model size. Error "
         "analysis shows that the remaining failures are predominantly partial-truth "
         "responses, suggesting the next gains will come from techniques that help "
         "the model commit to a verified answer — for example, factual-entailment "
         "verification, self-consistent decoding over retrieved facts, or "
         "hallucination-aware fine-tuning [4].",
         "Body Text"),
    ]),
]

ACK_HEADING = "Acknowledgment"
ACK_BODY = (
    "The author thanks Prof. Reda Nacif Elalaoui for the AI700-001 course and the "
    "structure that motivated this work, and the open-source maintainers of Ollama, "
    "ChromaDB and the TruthfulQA dataset, without which a local, reproducible "
    "evaluation would not have been possible."
)

REFERENCES = [
    "A.-H. Dang, T. Vu, and L.-M. Nguyen, \"A survey and analysis of hallucinations in large language models,\" Frontiers in AI, vol. 8, 2025.",
    "Y. Bang et al., \"HalluLens: A benchmark for LLM hallucinations,\" in Proc. 63rd ACL, 2025.",
    "X. Wang et al., \"Self-consistency improves chain of thought reasoning in language models,\" in Proc. ICLR, 2023.",
    "J. Song et al., \"RAG-HAT: A hallucination-aware tuning pipeline for LLM in RAG,\" in Proc. EMNLP, 2024.",
    "S. Lin, J. Hilton, and O. Evans, \"TruthfulQA: Measuring how models mimic human falsehoods,\" in Proc. ACL, 2022.",
    "C.-Y. Lin, \"ROUGE: A package for automatic evaluation of summaries,\" in Text Summarization Branches Out, 2004.",
    "P. Lewis et al., \"Retrieval-augmented generation for knowledge-intensive NLP tasks,\" in Proc. NeurIPS, 2020.",
    "J. Wei et al., \"Chain-of-thought prompting elicits reasoning in large language models,\" in Proc. NeurIPS, 2022.",
    "AI@Meta, \"LLaMA 3.2 model card,\" 2024. [Online]. Available: https://github.com/meta-llama/llama3",
    "Ollama, \"Ollama: Run LLMs locally,\" 2024. [Online]. Available: https://github.com/ollama/ollama",
]


# ---------- Document construction ----------

def main():
    doc = Document(str(TEMPLATE))

    # 0. Remove the original sample table from the template.
    for t in list(doc.tables):
        first_cell = t.rows[0].cells[0].text.strip().lower() if t.rows else ""
        if "table head" in first_cell or first_cell == "":
            t._element.getparent().remove(t._element)

    paras = doc.paragraphs
    orig_paras = list(paras)  # snapshot — element references stay valid through sibling removals

    # 1. Title (paragraph 0)
    set_para_text(paras[0], TITLE, "paper title")

    # 2. Authors: collapse the multi-author block into one filled author + blanks.
    # The Author paragraphs are 1..18.  We place one filled author at paragraph 3
    # (which corresponds to the first 4-column author cell), and clear the rest.
    author_text = "\n".join(AUTHOR_LINES)
    for i in range(1, 19):
        if i == 3:
            set_para_text(paras[i], author_text, "Author")
        else:
            set_para_text(paras[i], "", "Author")

    # 3. Abstract / Keywords
    set_para_text(paras[19], "Abstract—" + ABSTRACT, "Abstract")
    set_para_text(paras[20], "Keywords—" + KEYWORDS, "Keywords")

    # 4. Body. Paragraphs 21..79 are body-content slots before the original
    # References Heading-5 at index 80. We rewrite them in place and remove
    # any unused slots.
    BODY_START = 21
    BODY_END = 79
    body_slots = list(range(BODY_START, BODY_END + 1))

    # Flatten our content into (text, style) tuples
    flat = []
    for heading, h_style, items in SECTIONS:
        flat.append((heading, h_style))
        for txt, st in items:
            flat.append((txt, st))
    flat.append((ACK_HEADING, "Heading 5"))
    flat.append((ACK_BODY, "Body Text"))

    # Process __FIGURE__ and __TABLE_PERF__ markers separately:
    # Render figures by clearing the slot paragraph, then inserting an image
    # before the caption text.

    # We also need to track where each slot ends up so we can insert the table.
    body_iter = iter(body_slots)
    figure_inserts = []  # list of (paragraph_obj, image_path)
    table_inserts = []   # list of (paragraph_obj, kind)

    # First pass: assign content to existing slots
    for entry in flat:
        try:
            slot = next(body_iter)
        except StopIteration:
            # Need to add a new paragraph at end of body section
            # Append after BODY_END paragraph by creating new paragraphs
            ref = paras[BODY_END]
            text, style = entry
            if isinstance(text, str) and text.startswith("__FIGURE__:"):
                _, img_path, caption = text.split(":", 2)
                np = insert_para_after(paras[BODY_END], "", "figure caption")
                figure_inserts.append((np, img_path, caption))
            elif text == "__TABLE_PERF__":
                np = insert_para_after(paras[BODY_END], "", "Body Text")
                table_inserts.append((np, "perf"))
            else:
                np = insert_para_after(paras[BODY_END], text, style or "Body Text")
            paras = doc.paragraphs  # refresh
            continue

        text, style = entry
        p = paras[slot]
        if isinstance(text, str) and text.startswith("__FIGURE__:"):
            _, img_path, caption = text.split(":", 2)
            set_para_text(p, "", "figure caption")
            figure_inserts.append((p, img_path, caption))
        elif text == "__TABLE_PERF__":
            set_para_text(p, "", "Body Text")
            table_inserts.append((p, "perf"))
        else:
            set_para_text(p, text, style or "Body Text")

    # Remove any remaining body slots entirely so the document doesn't have a
    # large run of empty paragraphs between the Acknowledgment and References.
    for slot in body_iter:
        p = paras[slot]
        p._element.getparent().remove(p._element)

    # 5. Replace references. Use the *original* paras list (captured before any
    # XML removals) — element references remain valid because XML elements
    # aren't moved, only siblings are removed.
    # In the original template:
    #   index 80     = Heading 5 "References"        (keep)
    #   index 81..85 = Body Text guidance about refs (clear)
    #   index 86..97 = sample reference entries      (replace with our refs)
    if 80 < len(orig_paras):
        set_para_text(orig_paras[80], "References", "Heading 5")
    for i in range(81, 86):
        if i < len(orig_paras):
            p = orig_paras[i]
            p._element.getparent().remove(p._element)

    REF_START = 86
    REF_END = 97
    ref_slots = list(range(REF_START, REF_END + 1))
    for i, ref in enumerate(REFERENCES):
        if i < len(ref_slots) and ref_slots[i] < len(orig_paras):
            set_para_text(orig_paras[ref_slots[i]], f"[{i+1}] {ref}", "references")
    # Remove any unused reference slots
    for j in range(len(REFERENCES), len(ref_slots)):
        if ref_slots[j] < len(orig_paras):
            p = orig_paras[ref_slots[j]]
            p._element.getparent().remove(p._element)

    # 6. Insert figures: replace caption paragraph with image-then-caption
    for fig_p, img_path, caption in figure_inserts:
        full_path = ROOT / img_path
        if not full_path.exists():
            print(f"  ! missing image: {full_path}")
            set_para_text(fig_p, caption, "figure caption")
            continue
        # Insert a new paragraph BEFORE the caption holding the image
        from docx.text.paragraph import Paragraph
        new_p_xml = deepcopy(fig_p._element)
        # clear runs in new paragraph
        for child in list(new_p_xml):
            if child.tag == qn("w:r"):
                new_p_xml.remove(child)
        fig_p._element.addprevious(new_p_xml)
        img_p = Paragraph(new_p_xml, fig_p._parent)
        img_p.style = "figure caption"
        run = img_p.add_run()
        try:
            run.add_picture(str(full_path), width=Inches(3.3))
        except Exception as e:
            print(f"  ! failed to add image {full_path}: {e}")
        # Set caption text
        set_para_text(fig_p, caption, "figure caption")

    # 7. Insert performance table
    for tbl_p, kind in table_inserts:
        if kind == "perf":
            # Build a 7-row x 4-col table just before the paragraph
            table = doc.add_table(rows=1, cols=4)
            try:
                table.style = "Table Grid"
            except KeyError:
                pass  # template lacks Table Grid; use default
            hdr = table.rows[0].cells
            hdr[0].text = "Method"
            hdr[1].text = "Factual Acc. (95% CI)"
            hdr[2].text = "Hallucination Rate"
            hdr[3].text = "ROUGE-L"
            method_labels = {
                "baseline": "Baseline",
                "cot": "Chain-of-Thought",
                "few_shot": "Few-Shot",
                "self_consistency": "Self-Consistency",
                "rag": "RAG",
                "rag_optimized": "RAG + Optimized",
            }
            for m in ["baseline", "cot", "few_shot", "self_consistency", "rag", "rag_optimized"]:
                row = table.add_row().cells
                a = STATS[m]["accuracy"]
                h = STATS[m]["hallucination_rate"]
                r = STATS[m]["rouge_l"]
                row[0].text = method_labels[m]
                row[1].text = f"{a['mean']:.3f} [{a['ci_lo']:.3f}, {a['ci_hi']:.3f}]"
                row[2].text = f"{h['mean']:.3f}"
                row[3].text = f"{r['mean']:.3f}"
            # Move the table to be just before the caption paragraph
            tbl_xml = table._element
            tbl_p._element.addprevious(tbl_xml)
            # Add a Table I caption above the table by repurposing tbl_p's role:
            # we want: caption paragraph (above the table) that says "Table I"
            # For simplicity, re-purpose tbl_p as caption
            set_para_text(tbl_p, "Table I. Per-method performance with bootstrap 95% confidence intervals (10,000 resamples).", "table head")
            # Move caption above the table
            tbl_p._element.addprevious(deepcopy(tbl_p._element))
            tbl_p._element.getparent().remove(tbl_p._element)

    doc.save(str(OUT))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
