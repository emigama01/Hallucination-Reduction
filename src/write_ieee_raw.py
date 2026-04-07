"""
Write IEEE paper by directly editing the XML inside the docx zip.
No python-docx involved - preserves the Strict OOXML format perfectly.
"""

import zipfile
import json
import os
import xml.etree.ElementTree as ET
import copy
import io

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
ORIGINAL = os.path.join(os.path.dirname(__file__), "..", "AI700-001-IEEE-conference-template-letter-Midterm.docx")
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "AI700-001-IEEE-Hallucination-LLM-Paper.docx")

NS_W = 'http://purl.oclc.org/ooxml/wordprocessingml/main'


def load_results():
    with open(os.path.join(RESULTS_DIR, "summary.json")) as f:
        return json.load(f)


def get_para_text(para):
    """Get full text from a paragraph element."""
    texts = para.findall(f'.//{{{NS_W}}}t')
    return ''.join(t.text or '' for t in texts)


def set_para_text(para, new_text):
    """Replace all text in a paragraph with new_text, keeping first run's formatting."""
    runs = para.findall(f'{{{NS_W}}}r')
    if not runs:
        # No runs - create one
        r = ET.SubElement(para, f'{{{NS_W}}}r')
        t = ET.SubElement(r, f'{{{NS_W}}}t')
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        t.text = new_text
        return

    # Keep first run's rPr (formatting), clear its text
    first_run = runs[0]
    first_rPr = first_run.find(f'{{{NS_W}}}rPr')

    # Remove ALL runs
    for r in runs:
        para.remove(r)

    # Create single new run with preserved formatting
    new_run = ET.SubElement(para, f'{{{NS_W}}}r')
    if first_rPr is not None:
        new_run.insert(0, copy.deepcopy(first_rPr))
    t = ET.SubElement(new_run, f'{{{NS_W}}}t')
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    t.text = new_text


def change_para_style(para, new_style_id):
    """Change the paragraph style."""
    pPr = para.find(f'{{{NS_W}}}pPr')
    if pPr is None:
        pPr = ET.SubElement(para, f'{{{NS_W}}}pPr')
        # Insert at beginning
        para.remove(pPr)
        para.insert(0, pPr)

    pStyle = pPr.find(f'{{{NS_W}}}pStyle')
    if pStyle is None:
        pStyle = ET.SubElement(pPr, f'{{{NS_W}}}pStyle')
        # Insert at beginning of pPr
        pPr.remove(pStyle)
        pPr.insert(0, pStyle)

    pStyle.set(f'{{{NS_W}}}val', new_style_id)


def main():
    summary = load_results()
    baseline_acc = summary['baseline']['avg_factual_accuracy']
    best_acc = summary['rag_optimized']['avg_factual_accuracy']
    improvement = ((best_acc - baseline_acc) / baseline_acc) * 100

    # Read original docx
    zin = zipfile.ZipFile(ORIGINAL, 'r')
    doc_xml_bytes = zin.read('word/document.xml')

    # Register all namespaces to avoid ns0: prefixes
    namespaces = {}
    for event, (prefix, uri) in ET.iterparse(io.BytesIO(doc_xml_bytes), events=['start-ns']):
        if prefix and uri:
            namespaces[prefix] = uri
            ET.register_namespace(prefix, uri)
    # Also register default
    ET.register_namespace('w', NS_W)

    root = ET.fromstring(doc_xml_bytes)
    body = root.find(f'{{{NS_W}}}body')

    # Get all paragraphs
    paras = body.findall(f'{{{NS_W}}}p')
    print(f"Found {len(paras)} paragraphs")

    # Debug: print paragraph index and content
    for i, p in enumerate(paras):
        text = get_para_text(p)[:60]
        pPr = p.find(f'{{{NS_W}}}pPr')
        style = ""
        if pPr is not None:
            pStyle = pPr.find(f'{{{NS_W}}}pStyle')
            if pStyle is not None:
                style = pStyle.get(f'{{{NS_W}}}val', '')
        if text.strip():
            print(f"  P{i} [{style}]: {text}")

    # ================================================================
    # Now replace content paragraph by paragraph
    # ================================================================

    # P0: Title
    set_para_text(paras[0],
        "Hallucination Reduction in Large Language Models: A Comparative Study of Prompt Engineering and Retrieval-Augmented Generation")

    # P1: subtitle note - clear
    set_para_text(paras[1], "")

    # P2-P4: Author area (complex with section breaks)
    # P2 is usually empty with section break
    # P3 has first author
    set_para_text(paras[3],
        "Emilio Garcia Martinez\nDept. of Artificial Intelligence\nAI700-001 | ID: 100783029\nProfessor: Reda Nacif Elalaoui")

    # Clear all other author paragraphs
    for i in range(4, 19):
        if i < len(paras):
            text = get_para_text(paras[i])
            if text.strip():
                set_para_text(paras[i], "")

    # P19: Abstract
    set_para_text(paras[19],
        "Abstract\u2014Large Language Models (LLMs) have demonstrated remarkable capabilities in natural language understanding and generation, yet they remain prone to hallucination\u2014generating fluent but factually incorrect content. This paper presents a systematic evaluation of hallucination reduction techniques applied to LLaMA 3.2 (3B parameters) across a curated dataset of 30 TruthfulQA-inspired questions spanning five knowledge categories. We implement and compare six experimental conditions: vanilla baseline, chain-of-thought (CoT) prompting, few-shot prompting, self-consistency decoding, Retrieval-Augmented Generation (RAG), and RAG with optimized prompting. Our results demonstrate that RAG-based approaches achieve the highest factual accuracy improvement of 43.3% over baseline (0.388 to 0.556), with the RAG pipeline showing the strongest ROUGE-L scores (0.353). Self-consistency decoding provided the best hallucination rate reduction among prompt-only methods.")

    # P20: Keywords
    set_para_text(paras[20],
        "Keywords\u2014Large Language Models, Hallucination Reduction, RAG, Prompt Engineering, Chain-of-Thought, LLaMA, Factual Accuracy")

    # P21: Heading 1 -> Introduction
    set_para_text(paras[21], "Introduction")

    # P22: Body Text
    set_para_text(paras[22],
        "Large Language Models (LLMs) such as GPT-4, LLaMA, and Claude have achieved remarkable advances in natural language processing, enabling applications in healthcare, legal analysis, education, and software development [1]. However, a critical limitation persists: the phenomenon of hallucination, defined as the generation of text that is syntactically fluent but factually incorrect or unsupported by source material [2]. In high-stakes domains, hallucinated outputs can have severe consequences.")

    # P23: Heading 1 -> Related Work
    set_para_text(paras[23], "Related Work")

    # P24: Heading 2 -> change to body text style
    change_para_style(paras[24], 'BodyText')
    set_para_text(paras[24],
        "Dang, Vu, and Nguyen [1] proposed the Prompt Sensitivity and Model Variability metrics for determining whether hallucinations originate from prompting strategies or model behavior. Their experiments demonstrated that chain-of-thought prompting can significantly reduce prompt-sensitive hallucinations, though some models retain high rates regardless of strategy. Bang et al. [2] introduced HalluLens, a comprehensive hallucination benchmarking suite. Song et al. [4] presented RAG-HAT, combining retrieval augmentation with DPO fine-tuning. Wang et al. [3] demonstrated that self-consistency decoding improves factual accuracy.")

    # P25: Body Text
    set_para_text(paras[25],
        "These works motivated our three-phase approach: establishing baselines, testing prompt engineering techniques, and implementing RAG-based reduction with optimized prompting strategies. Our work differs by systematically comparing all approaches on the same smaller model (3B parameters) under identical conditions.")

    # P27: Heading 2 -> Heading 1 Methodology
    change_para_style(paras[27], 'Heading1')
    set_para_text(paras[27], "Methodology")

    # P28: sponsors -> Heading 2
    change_para_style(paras[28], 'Heading2')
    set_para_text(paras[28], "Experimental Setup")

    # P29: Body Text
    set_para_text(paras[29],
        "All experiments were conducted using LLaMA 3.2 (3B parameters) served locally via Ollama on an Apple M1 system with 8GB RAM. The model was run with temperature 0.7 and maximum prediction length of 300 tokens. We used a curated dataset of 30 questions inspired by TruthfulQA [5], distributed across five categories: Health (7), Science (8), History (5), Geography (4), and Misconceptions (6).")

    # P30: Heading 1 -> Heading 2
    change_para_style(paras[30], 'Heading2')
    set_para_text(paras[30], "Evaluation Metrics")

    # P31: Body Text
    set_para_text(paras[31],
        "We evaluated responses using three complementary metrics: (1) Hallucination Detection Rate, a binary classifier combining keyword overlap with ROUGE-L similarity; (2) ROUGE-L Score, measuring longest common subsequence overlap [6]; and (3) Factual Accuracy Score, a composite metric combining keyword recall (0.6 weight) and ROUGE-L similarity (0.4 weight), designed to handle verbose responses.")

    # P32: Body Text -> Heading 2
    change_para_style(paras[32], 'Heading2')
    set_para_text(paras[32], "Experimental Conditions")

    # P33: Heading 2 -> Body Text
    change_para_style(paras[33], 'BodyText')
    set_para_text(paras[33],
        "Six conditions were tested: (1) Vanilla baseline with simple factual prompting; (2) Chain-of-Thought prompting with step-by-step reasoning; (3) Few-Shot prompting with three verified examples; (4) Self-Consistency Decoding generating three responses and selecting the majority consensus; (5) RAG Pipeline retrieving top 3 chunks from ChromaDB; (6) RAG + Optimized Prompting combining retrieval with CoT, few-shot examples, and fact-checking instructions.")

    # P34: Body Text -> Heading 1 Results
    change_para_style(paras[34], 'Heading1')
    set_para_text(paras[34], "Results")

    # P35: Heading 2 -> Heading 2
    set_para_text(paras[35], "Overall Performance")

    # P36-39: bullet list -> Body Text for results
    change_para_style(paras[36], 'BodyText')
    set_para_text(paras[36],
        f"The most significant finding is the progressive improvement in factual accuracy from baseline ({baseline_acc:.3f}) to RAG + Optimized Prompting ({best_acc:.3f}), representing a {improvement:.1f}% improvement. The RAG pipeline achieved the highest ROUGE-L score ({summary['rag']['avg_rouge_l']:.3f}), indicating strongest lexical overlap with ground-truth answers.")

    change_para_style(paras[37], 'BodyText')
    set_para_text(paras[37],
        f"Baseline: Hallucination Rate {summary['baseline']['hallucination_rate']:.1%}, Accuracy {summary['baseline']['avg_factual_accuracy']:.3f}, ROUGE-L {summary['baseline']['avg_rouge_l']:.3f}. Chain-of-Thought: {summary['cot']['hallucination_rate']:.1%}, {summary['cot']['avg_factual_accuracy']:.3f}, {summary['cot']['avg_rouge_l']:.3f}. Few-Shot: {summary['few_shot']['hallucination_rate']:.1%}, {summary['few_shot']['avg_factual_accuracy']:.3f}, {summary['few_shot']['avg_rouge_l']:.3f}.")

    change_para_style(paras[38], 'BodyText')
    set_para_text(paras[38],
        f"Self-Consistency: {summary['self_consistency']['hallucination_rate']:.1%}, {summary['self_consistency']['avg_factual_accuracy']:.3f}, {summary['self_consistency']['avg_rouge_l']:.3f}. RAG Pipeline: {summary['rag']['hallucination_rate']:.1%}, {summary['rag']['avg_factual_accuracy']:.3f}, {summary['rag']['avg_rouge_l']:.3f}. RAG + Optimized: {summary['rag_optimized']['hallucination_rate']:.1%}, {summary['rag_optimized']['avg_factual_accuracy']:.3f}, {summary['rag_optimized']['avg_rouge_l']:.3f}.")

    change_para_style(paras[39], 'BodyText')
    set_para_text(paras[39],
        f"Among prompt-only methods, few-shot prompting achieved the highest factual accuracy ({summary['few_shot']['avg_factual_accuracy']:.3f}). Self-consistency showed the best hallucination rate reduction ({summary['self_consistency']['hallucination_rate']:.1%} vs {summary['baseline']['hallucination_rate']:.1%} baseline). CoT produced very low ROUGE-L ({summary['cot']['avg_rouge_l']:.3f}) due to verbose outputs, highlighting ROUGE-L limitations for structured responses.")

    # P40: Heading 2 -> Heading 2 Category Analysis
    set_para_text(paras[40], "Category-Level Analysis")

    # P41: Body Text
    set_para_text(paras[41],
        "Category-level analysis revealed significant variation. Geography showed the largest accuracy improvement with RAG, likely because factual geographic data is well-suited to retrieval-based grounding. Health maintained relatively low baseline hallucination rates, suggesting stronger pre-training knowledge. History and Misconceptions were the hardest categories to address.")

    # P42: Body Text
    set_para_text(paras[42],
        "An important finding concerns the divergence between ROUGE-L and factual accuracy. CoT and RAG+Optimized produced verbose responses with low ROUGE-L but correct facts. Our composite metric better captures verbose-but-accurate responses. Relying solely on lexical overlap may underestimate structured prompting effectiveness.")

    # P43: equation -> clear
    set_para_text(paras[43], "")

    # P44: Body Text -> Heading 1 Discussion
    change_para_style(paras[44], 'Heading1')
    set_para_text(paras[44], "Discussion")

    # P45: Heading 2 -> Body Text
    change_para_style(paras[45], 'BodyText')
    set_para_text(paras[45],
        "Our results confirm that grounding model outputs in external knowledge is more effective than relying on parametric knowledge alone. The 43.3% factual accuracy improvement demonstrates that even 3B parameter models achieve meaningful hallucination reduction when augmented with retrieval. CoT underperformance on smaller models contrasts with findings on GPT-4 [1], suggesting capacity-dependent effectiveness.")

    # P46-57: bullet list -> reuse for discussion + conclusion
    change_para_style(paras[46], 'BodyText')
    set_para_text(paras[46],
        "Self-consistency decoding showed moderate improvement with minimal complexity, making it a practical first-line defense. RAG is most effective for factual recall (Geography, Health) but less for nuanced reasoning about misconceptions. Optimal hallucination reduction strategies should be domain-adaptive.")

    change_para_style(paras[47], 'Heading2')
    set_para_text(paras[47], "Limitations")

    change_para_style(paras[48], 'BodyText')
    set_para_text(paras[48],
        "Limitations include: a small dataset (30 questions), single model size (3B), purpose-built knowledge base (optimistic RAG scenario), and automated-only evaluation. Results may not generalize to larger LLMs where CoT may be more effective.")

    change_para_style(paras[49], 'Heading1')
    set_para_text(paras[49], "Conclusion and Future Work")

    change_para_style(paras[50], 'BodyText')
    set_para_text(paras[50],
        f"This paper presented a systematic evaluation of hallucination reduction techniques for LLaMA 3.2 (3B). RAG combined with optimized prompting achieves {improvement:.1f}% factual accuracy improvement over vanilla baseline. Few-shot and self-consistency showed the most consistent prompt-only improvements.")

    change_para_style(paras[51], 'BodyText')
    set_para_text(paras[51],
        "Future work will extend evaluation to larger models (7B-70B), implement hallucination-aware fine-tuning following the RAG-HAT approach [4], evaluate on full TruthfulQA, and explore hybrid self-consistency + RAG approaches with NLI-based faithfulness evaluation.")

    # Clear remaining body text paragraphs
    for i in range(52, 80):
        if i < len(paras):
            set_para_text(paras[i], "")

    # P80: References heading - keep
    set_para_text(paras[80], "References")

    # Clear P81-85
    for i in range(81, 86):
        if i < len(paras):
            set_para_text(paras[i], "")

    # P86+: references
    refs = [
        'A.-H. Dang, T. Vu, and L.-M. Nguyen, "A survey and analysis of hallucinations in large language models," Frontiers in AI, vol. 8, 2025.',
        'Y. Bang et al., "HalluLens: A benchmark for LLM hallucinations," in Proc. 63rd ACL, 2025.',
        'X. Wang et al., "Self-consistency improves chain of thought reasoning in language models," in Proc. ICLR, 2023.',
        'J. Song et al., "RAG-HAT: A Hallucination-Aware Tuning Pipeline," in Proc. EMNLP, 2024.',
        'S. Lin, J. Hilton, and O. Evans, "TruthfulQA: Measuring how models mimic human falsehoods," in Proc. ACL, 2022.',
        'C.-Y. Lin, "ROUGE: A package for automatic evaluation of summaries," in Text Summarization Branches Out, 2004.',
        'P. Lewis et al., "Retrieval-augmented generation for knowledge-intensive NLP tasks," in Proc. NeurIPS, 2020.',
        'J. Wei et al., "Chain-of-thought prompting elicits reasoning in large language models," in Proc. NeurIPS, 2022.',
    ]
    for i, ref in enumerate(refs):
        idx = 86 + i
        if idx < len(paras):
            set_para_text(paras[idx], ref)

    # Clear leftover
    for i in range(86 + len(refs), len(paras)):
        if i < len(paras):
            set_para_text(paras[i], "")

    # Serialize back to XML bytes
    new_xml = ET.tostring(root, encoding='unicode', xml_declaration=True)
    # Fix encoding declaration
    new_xml = new_xml.replace("<?xml version='1.0' encoding='us-ascii'?>",
                               '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
    new_xml_bytes = new_xml.encode('utf-8')

    # Write new docx - copy everything from original, replace only document.xml
    with zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.namelist():
            if item == 'word/document.xml':
                zout.writestr(item, new_xml_bytes)
            else:
                zout.writestr(item, zin.read(item))

    zin.close()
    print(f"IEEE paper saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
