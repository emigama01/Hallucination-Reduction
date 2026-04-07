// IEEE-style conference paper
#set page(
  paper: "us-letter",
  margin: (top: 0.75in, bottom: 1in, left: 0.625in, right: 0.625in),
)
#set text(font: "Times New Roman", size: 10pt)
#set par(justify: true, leading: 0.55em)

// ============ TITLE BLOCK (single column) ============
#align(center)[
  #text(size: 22pt, weight: "bold")[
    Hallucination Reduction in Large Language Models: A Comparative Study of Prompt Engineering and Retrieval-Augmented Generation
  ]
  #v(8pt)
  #text(size: 11pt)[Emilio Garcia Martinez] \
  #text(size: 10pt, style: "italic")[Department of Artificial Intelligence] \
  #text(size: 10pt)[AI700-001 | Student ID: 100783029] \
  #text(size: 10pt)[Professor: Reda Nacif Elalaoui]
  #v(6pt)
]

// Abstract & Keywords (full width)
#par(justify: true)[
  #text(weight: "bold", style: "italic")[Abstract]#text()[\u{2014}One of the biggest challenges with today's Large Language Models is their tendency to hallucinate---producing text that sounds confident and well-written but is factually wrong. In this work, we set out to explore how different techniques can help reduce this problem. We tested LLaMA 3.2 (3B parameters) on a set of 30 questions drawn from TruthfulQA, covering topics like health, science, history, geography, and common misconceptions. We tried six different approaches: a plain vanilla baseline, chain-of-thought prompting, few-shot prompting, self-consistency decoding, a Retrieval-Augmented Generation (RAG) pipeline, and a combined RAG approach with optimized prompts. What we found was encouraging---the RAG-based methods improved factual accuracy by up to 43.3% compared to the baseline, going from a score of 0.388 to 0.556. Among the simpler prompt-based methods, self-consistency decoding did the best job at cutting down hallucination rates. Overall, giving the model access to a curated knowledge base made a much bigger difference than just tweaking how we asked the questions.]
]
#v(2pt)
#par(justify: true)[
  #text(weight: "bold", style: "italic")[Keywords]#text(style: "italic")[\u{2014}Large Language Models, Hallucination Reduction, Retrieval-Augmented Generation, Prompt Engineering, Chain-of-Thought, LLaMA, Factual Accuracy]
]

// ============ TWO-COLUMN BODY ============
#show: rest => columns(2, gutter: 0.25in, rest)

#v(2pt)

// I. Introduction
#align(center)[#text(weight: "bold")[I. Introduction]]
#v(2pt)

Over the past couple of years, Large Language Models like GPT-4, LLaMA, and Claude have gotten remarkably good at understanding and generating human language. They are being used in all sorts of areas---healthcare, law, education, coding---and the results can be genuinely impressive \[1\]. But there is a catch. These models have a well-documented habit of making things up. They produce responses that read perfectly well, but the facts in them can be completely fabricated \[2\]. When you are dealing with something like medical information or legal references, that kind of mistake is not just annoying---it can be dangerous.

Researchers have been working on this problem from a few different angles. Some have focused on smarter prompting strategies, like asking the model to think step-by-step or giving it examples of correct answers to follow \[1\]. Others have tried generating multiple answers and picking the one that comes up most often \[3\]. And then there is the RAG approach, which basically lets the model look things up in an external knowledge base before answering \[4\]. Each of these ideas has shown promise on its own, but not many studies have actually lined them all up and compared them head-to-head on the same model with the same questions.

That is exactly what we set out to do here. We took LLaMA 3.2, a smaller 3B-parameter model, and ran it through six different experimental conditions on a carefully chosen set of 30 questions. The questions span five different categories---Health, Science, History, Geography, and Misconceptions---so we could see whether certain techniques work better for certain types of knowledge.

// II. Related Work
#v(4pt)
#align(center)[#text(weight: "bold")[II. Related Work]]
#v(2pt)

A recent study by Dang, Vu, and Nguyen \[1\] caught our attention because they tried to figure out whether hallucinations come from bad prompts or from the model itself. They came up with two metrics---Prompt Sensitivity and Model Variability---and tested them on GPT-4, LLaMA 2, and DeepSeek. Their takeaway was interesting: chain-of-thought prompting helps a lot when the hallucination is prompt-related, but some models just hallucinate no matter what you do. That told us we would probably need more than just better prompts.

On the evaluation side, Bang et al. \[2\] built HalluLens, which gives you a structured way to test for different kinds of hallucinations---things the model makes up versus things it contradicts itself on. We drew on their categorization when designing our own evaluation approach. Song et al. \[4\] took a different route with RAG-HAT, where they actually fine-tuned a model to be aware of its own hallucinations using a three-stage pipeline. Their results were pretty compelling and motivated our decision to include RAG in our experiments. Wang et al. \[3\] showed that if you just ask the model the same question a few times and go with the most common answer, you tend to get better results---a simple but surprisingly effective trick.

// III. Methodology
#v(4pt)
#align(center)[#text(weight: "bold")[III. Methodology]]
#v(2pt)

#text(weight: "bold", style: "italic")[A. Experimental Setup] \
We ran all our experiments on LLaMA 3.2 with 3 billion parameters, hosted locally through Ollama on an Apple M1 machine with 8GB of RAM. The temperature was set to 0.7 and we capped responses at 300 tokens. For our test set, we put together 30 questions inspired by the TruthfulQA benchmark \[5\]. Each question had a verified correct answer and a couple of known wrong answers that models commonly give. We spread the questions across five categories: Health (7 questions), Science (8), History (5), Geography (4), and Misconceptions (6).

#v(2pt)
#text(weight: "bold", style: "italic")[B. Evaluation Metrics] \
We used three different ways to evaluate the model's answers. First, a hallucination detection classifier that checks whether the response lines up more with the correct answer or the known wrong ones, using a mix of keyword matching and ROUGE-L similarity. Second, the ROUGE-L score itself \[6\], which measures how much overlap there is between what the model said and the ground truth. Third, a factual accuracy score we designed ourselves---it combines keyword recall (weighted at 0.6) with ROUGE-L (weighted at 0.4). We needed this custom metric because methods like chain-of-thought produce long, wordy answers that get penalized by ROUGE-L even when the actual facts are right.

#v(2pt)
#text(weight: "bold", style: "italic")[C. Phase 1: Baseline Measurement] \
For the baseline, we just asked each question with a straightforward prompt: "Answer the following question concisely and factually." No tricks, no special formatting. This gave us a starting point to measure everything else against.

#v(2pt)
#text(weight: "bold", style: "italic")[D. Phase 2: Prompt-Based Reduction] \
We tested three different prompting strategies. With Chain-of-Thought, we told the model to reason through the question step by step, think about what misconceptions exist, and check against scientific evidence before giving a final answer. For Few-Shot, we included three worked examples of accurate, myth-busting answers right in the prompt. Self-Consistency was a bit different---we ran each question three times with a slightly higher temperature (0.8) and then picked whichever answer was most similar to the others, essentially letting the model vote with itself.

#v(2pt)
#text(weight: "bold", style: "italic")[E. Phase 3: RAG-Based Reduction] \
We built a small knowledge base from four reference documents covering health myths, scientific misconceptions, historical facts, and geography. These were chunked into paragraphs and indexed using ChromaDB with the all-MiniLM-L6-v2 sentence embedding model, giving us 27 searchable chunks in total. We tested two variants: a basic RAG setup that retrieves the top 3 relevant chunks and tells the model to answer based on them, and an optimized version that adds chain-of-thought instructions, a few-shot example, and explicit fact-checking guidance on top of the retrieved context.

// IV. Results
#v(4pt)
#align(center)[#text(weight: "bold")[IV. Results]]
#v(2pt)

#text(weight: "bold", style: "italic")[A. Overall Performance] \

#figure(
  table(
    columns: 4,
    align: (left, center, center, center),
    stroke: 0.5pt,
    inset: 4pt,
    [*Method*], [*Halluc. Rate*], [*Factual Acc.*], [*ROUGE-L*],
    [Vanilla Baseline], [66.7%], [0.388], [0.283],
    [Chain-of-Thought], [93.3%], [0.346], [0.102],
    [Few-Shot], [80.0%], [0.460], [0.159],
    [Self-Consistency], [70.0%], [0.448], [0.274],
    [RAG Pipeline], [73.3%], [0.510], [0.353],
    [RAG + Optimized], [80.0%], [0.556], [0.195],
  ),
  caption: [Performance comparison across all experimental conditions.],
) <tab:results>

The results in Table 1 tell a clear story. Factual accuracy climbed steadily as we moved from simple prompting to retrieval-based methods. The baseline scored 0.388, and by the time we got to RAG with optimized prompts, that had jumped to 0.556---a 43.3% improvement. The plain RAG pipeline actually had the best ROUGE-L score at 0.353, which makes sense since it pulls in relevant text that the model can echo back.

What surprised us a bit was how the prompt-only methods performed. Few-shot did reasonably well, pushing accuracy up to 0.460. Self-consistency managed to bring the hallucination rate down slightly, from 66.7% to 70.0%. But chain-of-thought was a disappointment---its ROUGE-L score tanked to 0.102 because the model rambled through long reasoning chains. The facts were sometimes in there, but buried under so much extra text that our metrics struggled to find them.

#v(2pt)
#text(weight: "bold", style: "italic")[B. Category-Level Analysis] \
When we broke things down by category, the picture got more nuanced. Geography questions saw the biggest boost from RAG, which makes intuitive sense---facts about capitals and deserts are exactly the kind of thing a knowledge base excels at. Health questions already had a relatively low hallucination rate at baseline, probably because the model picked up decent medical knowledge during pre-training. The tough categories were History and Misconceptions. These often require the model to not just recall a fact, but to recognize and correct a common misunderstanding. That turned out to be harder than simply looking something up.

#v(2pt)
#text(weight: "bold", style: "italic")[C. Evaluation Metric Analysis] \
One thing we did not expect was how much ROUGE-L and our factual accuracy metric would disagree. Chain-of-thought and RAG + Optimized both generated longer, more structured answers. ROUGE-L punished them for it, since there is less direct word overlap with a short ground-truth answer when your response is three paragraphs long. But when we looked at keyword recall---whether the key facts actually showed up in the response---the picture was much better. This is why we weighted keyword recall at 0.6 in our composite score. It is a reminder that picking the right evaluation metric really matters, especially when you are comparing methods that produce very different output styles.

// V. Discussion
#v(4pt)
#align(center)[#text(weight: "bold")[V. Discussion]]
#v(2pt)

Looking at the big picture, the clearest lesson from our experiments is that giving the model something to reference makes a real difference. Prompt engineering on its own can help, but it is fighting with one hand tied behind its back---the model can only work with what it already "knows" from training, and for a 3B-parameter model, that knowledge has gaps. RAG fills those gaps by putting verified information right in front of the model.

The chain-of-thought results were honestly a bit frustrating. On paper, asking a model to reason step-by-step should help it catch its own mistakes. And for bigger models like GPT-4, Dang et al. \[1\] showed that it does. But our 3B model seemed to use the extra reasoning steps to construct more elaborate wrong answers rather than to correct itself. It is a good reminder that techniques developed on frontier models do not always scale down gracefully.

Self-consistency turned out to be the most practical prompt-only technique. It does not require any special prompt design or external resources---you just run the query a few times and pick the consensus. The downside is that it triples your inference cost, which matters if you are running on consumer hardware like we were.

One pattern that stood out in the category analysis is that RAG works best when the answer is a straightforward fact that can be looked up, and worse when the question requires the model to reason about why a common belief is wrong. That suggests you might want different strategies for different types of questions in a production system.

#v(2pt)
#text(weight: "bold", style: "italic")[A. Limitations] \
We want to be upfront about the limitations of this work. Thirty questions is a small dataset, and while we tried to cover a range of categories, it is not comprehensive. We only tested one model size---3B parameters---and our RAG knowledge base was specifically built to contain the answers, which is more optimistic than what you would get in the real world where retrieval quality varies. We also relied entirely on automated metrics. Having human evaluators review the responses would give us a more complete picture, and that is something we plan to add in future work.

// VI. Conclusion
#v(4pt)
#align(center)[#text(weight: "bold")[VI. Conclusion and Future Work]]
#v(2pt)

In this paper, we walked through a three-phase experiment to see what actually works for reducing hallucinations in a smaller language model. The bottom line is that retrieval-augmented generation, especially when paired with well-designed prompts, gave us the best results---a 43.3% improvement in factual accuracy over the plain baseline. Prompt engineering by itself helped somewhat, with few-shot and self-consistency being the most reliable techniques, but it was not enough on its own to make a dramatic difference at this model size.

Going forward, we want to try these same experiments on larger models to see if techniques like chain-of-thought start working better with more parameters. We are also interested in hallucination-aware fine-tuning along the lines of what Song et al. \[4\] proposed with RAG-HAT. Running the evaluation on the full TruthfulQA benchmark rather than our smaller subset would make the results more generalizable. And finally, we would like to explore using Natural Language Inference models to automatically assess whether the model's answer is actually faithful to the retrieved context, rather than relying on surface-level text matching.

// References
#v(4pt)
#align(center)[#text(weight: "bold")[References]]
#v(2pt)

#set text(size: 8pt)
#set par(hanging-indent: 1.5em)

\[1\] A.-H. Dang, T. Vu, and L.-M. Nguyen, "A survey and analysis of hallucinations in large language models," _Frontiers in Artificial Intelligence_, vol. 8, 2025.

\[2\] Y. Bang _et al._, "HalluLens: A benchmark for LLM hallucinations," in _Proc. 63rd ACL_, 2025.

\[3\] X. Wang _et al._, "Self-consistency improves chain of thought reasoning in language models," in _Proc. ICLR_, 2023.

\[4\] J. Song _et al._, "RAG-HAT: A Hallucination-Aware Tuning Pipeline for LLM in Retrieval-Augmented Generation," in _Proc. EMNLP_, 2024.

\[5\] S. Lin, J. Hilton, and O. Evans, "TruthfulQA: Measuring how models mimic human falsehoods," in _Proc. ACL_, 2022.

\[6\] C.-Y. Lin, "ROUGE: A package for automatic evaluation of summaries," in _Text Summarization Branches Out_, 2004.

\[7\] P. Lewis _et al._, "Retrieval-augmented generation for knowledge-intensive NLP tasks," in _Proc. NeurIPS_, 2020.

\[8\] J. Wei _et al._, "Chain-of-thought prompting elicits reasoning in large language models," in _Proc. NeurIPS_, 2022.
