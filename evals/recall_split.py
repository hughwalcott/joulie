"""Split figure recall into its two independent halves.

    figure_recall  =  P(figure reaches the context)  x  P(model states it | it did)
                      ^ retrieval                       ^ generation

compare_runs.py reports the product, which is what makes a low score hard to act
on: 0.545 is consistent with good retrieval and a terse model, or with a verbose
model and bad retrieval. Those need opposite fixes, and only one of them is free
in latency terms — reordering chunks costs nothing, while making answers carry
more figures lengthens the decode window, which is what puts TTS chunks into the
contended RTF band (logs/latency-analysis.md, third pass finding 1).

    python3 evals/recall_split.py evals/results-tuning-d-shipped.json

Measured on run D (2026-09-18, shipped config, 57 questions / 131 figures):

    in the k=3 context          67.2%      <- retrieval
    ...and stated by the model  75.0%      <- generation
    reachable within k=20       85.5%      <- what reranking could recover
    present anywhere in the KB  ~100%      <- attainability.py: the corpus is not the limit

(Those are pooled over all 131 figures. The lever table below is the mean of
per-question ratios, the aggregation compare_runs.py uses, so its 0.678 is the
same quantity as the 67.2% above counted a different way -- do not mix them.)

The generation half is mostly the answer-length budget, not a fault: it is 0.93
when the reference answer carries ONE figure and 0.59 when it carries three,
against a system prompt that asks for two to four sentences. Read a low
generation number as "the reference is denser than a spoken answer can be"
before reading it as an error.

REJECTED LEVERS. Each was measured against the shipped 0.678 context recall at
an unchanged context size, and each lost. They are recorded so the next person
does not re-derive them:

    BM25 top-3 (whole corpus, title+section+body)        0.527  (-0.151)
    reciprocal rank fusion, dense + BM25                 0.642  (-0.036)
    hybrid score, BM25 within the dense top-20           0.663  (-0.015)
    sentence selection by term overlap, pool=6           0.640  (-0.038)
    sentence selection by embedding, pool=20             0.598  (-0.079)
    2-sentence windows by embedding, pool=20             0.634  (-0.044)
    3-sentence windows by embedding, pool=20             0.652  (-0.026)
    title+section embedded with the body (re-ingest)     0.648  (-0.030)

Two things fall out of that list. Cheap lexical and sentence-level signals cannot
improve on MiniLM's own ordering of its own top-20 — the gap to 0.913 needs a
stronger relevance model, not a cleverer rescoring of the same one. And every
arm that cut below whole-chunk granularity lost in proportion to how finely it
cut (1 sentence < 2 < 3 < whole chunk), which is the same fragmentation that
rejected CHUNK_SIZE 250 in ingest.py.
"""

import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evals.attainability import FIGURE, normalise
from joulie import config
from joulie.rag import Retriever

WIDE = 20


def checkable(expected: str) -> set[str]:
    """The expected answer's distinctive figures, matching compare_runs.py:
    bare years only count when nothing stronger is present."""
    figures = set(FIGURE.findall(expected))
    strong = {f for f in figures if not (f.strip().isdigit() and len(f.strip()) == 4)}
    return strong or figures


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "evals/results-tuning-d-shipped.json")
    rows = [r for r in json.loads(path.read_text()) if not r["id"].endswith("-rephrased")]
    # No threshold: this measures ranking, and RAG_DISTANCE_THRESHOLD was
    # measured never to fire on this bank (0 of 107 questions lose a chunk).
    retriever = Retriever(top_k=WIDE, distance_threshold=99.0)
    k = config.RAG_TOP_K

    per_question = []
    for row in rows:
        figures = checkable(row["expected"])
        if not figures:
            continue
        texts = [c["text"] for c in retriever.retrieve(row["question"])]
        context = normalise("\n".join(texts[:k]))
        wide = normalise("\n".join(texts))
        answer = normalise(row["answer"])
        in_context = {f for f in figures if normalise(f) in context}
        per_question.append({
            "id": row["id"],
            "expected": len(figures),
            "in_context": len(in_context),
            "in_wide": sum(normalise(f) in wide for f in figures),
            "stated": sum(normalise(f) in answer for f in in_context),
            "words": len(row["answer"].split()),
        })

    total = sum(q["expected"] for q in per_question)
    in_ctx = sum(q["in_context"] for q in per_question)
    stated = sum(q["stated"] for q in per_question)
    wide = sum(q["in_wide"] for q in per_question)
    print(f"{path.stem}: {len(per_question)} questions, {total} checkable figures, top_k={k}\n")
    print(f"  reach the context      {in_ctx:4d} / {total}  {in_ctx/total:6.1%}   retrieval")
    print(f"  ...and get stated      {stated:4d} / {in_ctx}  {stated/in_ctx:6.1%}   generation")
    print(f"  product                {stated/total:6.1%}   (compare_runs figure_recall)")
    print(f"  within top-{WIDE}          {wide:4d} / {total}  {wide/total:6.1%}   reranking ceiling")

    print("\ngeneration recall by how many figures the reference answer carries:")
    print(f"  {'figures':<10}{'n':>4}{'retrieval':>12}{'generation':>13}{'answer words':>14}")
    for lo, hi, label in [(1, 1, "1"), (2, 2, "2"), (3, 3, "3"), (4, 99, "4+")]:
        group = [q for q in per_question if lo <= q["expected"] <= hi]
        if not group:
            continue
        got = [q for q in group if q["in_context"]]
        print(f"  {label:<10}{len(group):>4}"
              f"{st.mean(q['in_context']/q['expected'] for q in group):>12.3f}"
              f"{st.mean(q['stated']/q['in_context'] for q in got):>13.3f}"
              f"{st.mean(q['words'] for q in group):>14.0f}")

    missed = sorted((q for q in per_question if q["in_context"] < q["expected"]),
                    key=lambda q: q["in_context"] - q["expected"])
    print(f"\nretrieval misses ({len(missed)} questions) — worst first, "
          f"'wide' shows what reranking could recover:")
    for q in missed[:10]:
        print(f"  {q['id']:<9}{q['in_context']}/{q['expected']} in context, "
              f"{q['in_wide']}/{q['expected']} within top-{WIDE}")


if __name__ == "__main__":
    main()
