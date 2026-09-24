"""Benchmark cross-encoder rerankers against the question bank.

The retrieval half of figure recall loses a quarter of the expected figures at
ranking time, not at retrieval time: 67.2% reach the shipped top-3 context while
85.5% sit somewhere in the dense top-20 (evals/recall_split.py). A reranker
picks a better 3 out of that 20, so the block handed to Ollama keeps its size
and prefill is unchanged by construction -- the only new cost is the reranker's
own forward pass, which runs before the LLM request, while the GPU is idle.

    python3 evals/rerank_bench.py                  # every model below
    python3 evals/rerank_bench.py --device cpu     # force CPU
    python3 evals/rerank_bench.py --models cross-encoder/ms-marco-MiniLM-L-6-v2

Models download once from HuggingFace and run locally thereafter, which keeps
the runtime path offline. Nothing here needs trust_remote_code.

RESULT (2026-09-19, 57 questions, pool=20, top_k=3, auto device on the M4):

    arm                                      recall    delta            95% CI   ms
    dense top-3 (shipped)                     0.678         -                 -    -
    cross-encoder/ms-marco-TinyBERT-L-2-v2    0.650    -0.028  [-0.125, +0.070]   13
    cross-encoder/ms-marco-MiniLM-L-4-v2      0.660    -0.018  [-0.106, +0.073]   25
    cross-encoder/ms-marco-MiniLM-L-6-v2      0.668    -0.009  [-0.096, +0.079]   28
    cross-encoder/ms-marco-MiniLM-L-12-v2     0.665    -0.013  [-0.086, +0.064]   49
    mixedbread-ai/mxbai-rerank-xsmall-v1      0.698    +0.020  [-0.070, +0.117]  161
    BAAI/bge-reranker-base                    0.671    -0.007  [-0.111, +0.091]  156
    dense top-20 (ceiling)                    0.913    +0.235                 -    -

**No reranker beats the dense baseline.** Every interval crosses zero; the best
arm is +0.020 at 161ms/query, which is not a result. Model size does not help --
bge-reranker-base (1.1GB) scores below MiniLM-L-6 (90MB).

The headroom is nonetheless real and NOT a pooling artifact: the oracle best
3-of-20 is 0.913, identical to reading all 20, and the best SINGLE chunk in the
pool averages 0.873 -- so one chunk usually holds nearly every expected figure,
and dense already picks an optimal 3 on 38 of the 57 questions. The task a
reranker fails at is finding that one chunk on the other 19.

The likeliest reason is what it is being asked to score. ingest.py slices the
corpus every 500 characters with no regard for structure, so 74% of chunks start
mid-sentence and 88% end mid-sentence -- one begins "e and region.". A
cross-encoder trained on well-formed MS-MARCO passages has little to work with.
Boundary-aware chunking was tried against this (sentence-packed to a target
size, 3-5% mid-sentence starts) and did NOT cleanly win: it produces smaller
chunks, and its own oracle ceiling falls to 0.843-0.860, because the expected
figures cluster inside ~500-character windows that cleaner chunks split. Any
retry needs to hold BOTH the character budget and the oracle ceiling constant
before its recall number means anything.

A caution on power: with 57 questions the CI half-width is ~0.09, so this bench
can only detect large effects. It rules out a reranker being an easy win; it
does not rule out a +0.03 one.

Reported per model: context recall at the shipped top_k (the quantity
recall_split.py calls retrieval, so 0.678 is the number to beat), the paired
bootstrap CI against the dense baseline over the same questions, seconds per
query, and how many distinct documents and publishers survive into the top-3 --
a reranker that returns three slices of one document would starve
format_context's authoritative/advocacy mix even with a good recall score.
"""

import argparse
import json
import random
import statistics as st
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evals.attainability import FIGURE, normalise
from evals.recall_split import checkable
from joulie import config
from joulie.rag import Retriever

POOL = 20
RESAMPLES = 4000
SEED = 20260919

MODELS = [
    "cross-encoder/ms-marco-TinyBERT-L-2-v2",
    "cross-encoder/ms-marco-MiniLM-L-4-v2",
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "cross-encoder/ms-marco-MiniLM-L-12-v2",
    "mixedbread-ai/mxbai-rerank-xsmall-v1",
    "BAAI/bge-reranker-base",
]


def recall(texts: list[str], figures: set[str]) -> float:
    hay = normalise("\n".join(texts))
    return sum(normalise(f) in hay for f in figures) / len(figures)


def bootstrap(deltas: list[float], rng: random.Random) -> tuple[float, float]:
    n = len(deltas)
    means = sorted(st.mean(rng.choices(deltas, k=n)) for _ in range(RESAMPLES))
    return means[int(0.025 * RESAMPLES)], means[int(0.975 * RESAMPLES)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="evals/results-tuning-d-shipped.json")
    ap.add_argument("--models", nargs="*", default=MODELS)
    ap.add_argument("--device", default=None, help="cpu / mps; default lets torch choose")
    ap.add_argument("--out", default="evals/rerank-bench.json")
    args = ap.parse_args()

    rows = [r for r in json.loads(Path(args.results).read_text())
            if not r["id"].endswith("-rephrased")]
    k = config.RAG_TOP_K
    retriever = Retriever(top_k=POOL, distance_threshold=99.0)

    # One dense pass; every arm reranks the same pools, so differences are the
    # reranker and nothing else.
    pools = []
    for row in rows:
        figures = checkable(row["expected"])
        if not figures:
            continue
        chunks = retriever.retrieve(row["question"])
        if len(chunks) < k:
            continue
        pools.append({"id": row["id"], "question": row["question"],
                      "figures": figures, "chunks": chunks})
    print(f"[bench] {len(pools)} questions with checkable figures, pool={POOL}, top_k={k}")

    def profile(pick) -> dict:
        """pick(pool) -> the k chunks that arm puts in front of the model."""
        recalls, docs, pubs = [], [], []
        for p in pools:
            top = pick(p)
            recalls.append(recall([c["text"] for c in top], p["figures"]))
            docs.append(len({c["source"] for c in top}))
            pubs.append(len({c["publisher_short"] for c in top}))
        return {"recall": recalls, "docs": st.mean(docs), "pubs": st.mean(pubs)}

    base = profile(lambda p: p["chunks"][:k])
    ceiling = profile(lambda p: p["chunks"])
    rng = random.Random(SEED)
    report = [{"model": f"dense top-{k} (shipped)", "recall": st.mean(base["recall"]),
               "delta": 0.0, "ci": None, "seconds": None,
               "docs": base["docs"], "pubs": base["pubs"]}]

    from sentence_transformers import CrossEncoder

    for name in args.models:
        print(f"\n[bench] {name}")
        try:
            t0 = time.monotonic()
            model = CrossEncoder(name, device=args.device) if args.device else CrossEncoder(name)
            load = time.monotonic() - t0
        except Exception as exc:
            print(f"  skipped: {exc!r}")
            continue

        timings = []

        def pick(p, model=model, timings=timings):
            pairs = [(p["question"], c["text"]) for c in p["chunks"]]
            t0 = time.monotonic()
            scores = model.predict(pairs, show_progress_bar=False)
            timings.append(time.monotonic() - t0)
            order = sorted(range(len(pairs)), key=lambda i: -scores[i])[:k]
            return [p["chunks"][i] for i in order]

        model.predict([(pools[0]["question"], pools[0]["chunks"][0]["text"])],
                      show_progress_bar=False)  # warm the graph before timing
        timings.clear()
        prof = profile(pick)
        deltas = [a - b for a, b in zip(prof["recall"], base["recall"])]
        lo, hi = bootstrap(deltas, rng)
        report.append({"model": name, "recall": st.mean(prof["recall"]),
                       "delta": st.mean(deltas), "ci": [lo, hi],
                       "seconds": st.mean(timings), "load_seconds": load,
                       "docs": prof["docs"], "pubs": prof["pubs"]})
        print(f"  recall {st.mean(prof['recall']):.3f}  ({st.mean(deltas):+.3f}, "
              f"CI [{lo:+.3f}, {hi:+.3f}])  {st.mean(timings)*1000:.0f}ms/query")

    report.append({"model": f"dense top-{POOL} (ceiling)", "recall": st.mean(ceiling["recall"]),
                   "delta": st.mean(ceiling["recall"]) - st.mean(base["recall"]),
                   "ci": None, "seconds": None,
                   "docs": ceiling["docs"], "pubs": ceiling["pubs"]})

    print(f"\n{'arm':<42}{'recall':>8}{'delta':>8}{'95% CI':>20}{'ms/query':>10}"
          f"{'docs':>7}{'pubs':>7}")
    for r in report:
        ci = f"[{r['ci'][0]:+.3f}, {r['ci'][1]:+.3f}]" if r["ci"] else ""
        ms = f"{r['seconds']*1000:.0f}" if r["seconds"] else ""
        print(f"{r['model'][:41]:<42}{r['recall']:>8.3f}{r['delta']:>+8.3f}{ci:>20}"
              f"{ms:>10}{r['docs']:>7.2f}{r['pubs']:>7.2f}")

    Path(args.out).write_text(json.dumps(
        {"device": args.device or "auto", "pool": POOL, "top_k": k,
         "questions": len(pools), "arms": report}, indent=1))
    print(f"\n[bench] wrote {args.out}")


if __name__ == "__main__":
    main()
