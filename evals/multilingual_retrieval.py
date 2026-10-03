"""Which embedder lets a non-English question find what the English question
finds? The reference for each question is the shipped English retriever's top-k
documents for the English wording; each candidate is scored on how many of those
documents it returns for the translated wording (document recall@k). The English
retriever is not ground truth, but it is what every English eval baseline was
measured against, so matching it is the bar.

    python evals/translate_questions.py       # once, drafts the question set
    python evals/multilingual_retrieval.py [--models a,b] [--k 3]
"""

import argparse
import json
import sys
import time
from pathlib import Path

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from joulie import config  # noqa: E402

HERE = Path(__file__).parent
CANDIDATES = [
    "sentence-transformers/all-MiniLM-L6-v2",   # shipped English model — the floor
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "intfloat/multilingual-e5-small",
    "intfloat/multilingual-e5-base",
]
# Off-topic questions: the distance threshold has to reject these in every
# language, or a visitor's small talk drags irrelevant chunks into the prompt.
OFF_TOPIC = {
    "en": "What's the best place to get fish and chips in Petone?",
    "zh": "佩托尼哪里的炸鱼薯条最好吃？",
    "hi": "पेटोन में फिश एंड चिप्स खाने की सबसे अच्छी जगह कौन सी है?",
    "es": "¿Cuál es el mejor sitio para comer fish and chips en Petone?",
    "fr": "Quel est le meilleur endroit pour manger un fish and chips à Petone ?",
    "de": "Wo gibt es in Petone die besten Fish and Chips?",
}


def prefixes(model_name: str) -> tuple[str, str]:
    # E5 is trained with these markers and degrades without them.
    return ("query: ", "passage: ") if "e5" in model_name else ("", "")


def load_chunks():
    collection = chromadb.PersistentClient(path=config.CHROMA_PATH).get_collection(
        config.CHROMA_COLLECTION)
    got = collection.get(include=["documents", "metadatas", "embeddings"])
    doc_ids = [m.get("document_id") or m.get("source") for m in got["metadatas"]]
    return got["documents"], doc_ids, np.asarray(got["embeddings"], dtype=np.float32)


def normalise(x: np.ndarray) -> np.ndarray:
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def top_k(query_vecs: np.ndarray, chunk_vecs: np.ndarray, k: int):
    sims = query_vecs @ chunk_vecs.T
    idx = np.argsort(-sims, axis=1)[:, :k]
    return idx, 1 - np.take_along_axis(sims, idx, axis=1)   # cosine distance, as Chroma reports


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(CANDIDATES))
    ap.add_argument("--k", type=int, default=config.RAG_TOP_K)
    args = ap.parse_args()

    questions = json.loads((HERE / "questions_multilingual.json").read_text())
    langs = [c for c in questions[0] if c not in ("id", "topic")]
    docs, doc_ids, shipped_vecs = load_chunks()
    shipped_vecs = normalise(shipped_vecs)
    print(f"[eval] {len(docs)} chunks, {len(questions)} questions, languages {langs}")

    # CPU, not MPS: with Ollama holding the GPU, MPS ran out of memory and
    # returned corrupt embeddings without raising. Also the runtime's device —
    # joulie.rag embeds a single short query per turn.
    english = SentenceTransformer(config.EMBED_MODEL, device="cpu")
    ref_idx, _ = top_k(normalise(english.encode([q["en"] for q in questions])), shipped_vecs, args.k)
    reference = [{doc_ids[i] for i in row} for row in ref_idx]

    report = {}
    for name in args.models.split(","):
        q_prefix, p_prefix = prefixes(name)
        model = SentenceTransformer(name, device="cpu")
        if name == config.EMBED_MODEL:
            chunk_vecs = shipped_vecs
        else:
            started = time.monotonic()
            chunk_vecs = normalise(model.encode([p_prefix + d for d in docs], batch_size=64))
            print(f"[eval] {name}: embedded KB in {time.monotonic() - started:.0f}s")
        started = time.monotonic()
        model.encode([q_prefix + questions[0]["en"]])
        query_ms = (time.monotonic() - started) * 1000

        per_lang, on_topic = {}, []
        for lang in langs:
            idx, dist = top_k(normalise(model.encode([q_prefix + q[lang] for q in questions])),
                              chunk_vecs, args.k)
            recalls = [len({doc_ids[i] for i in row} & ref) / len(ref)
                       for row, ref in zip(idx, reference)]
            per_lang[lang] = sum(recalls) / len(recalls)
            on_topic += list(dist[:, 0])
        off_idx, off_dist = top_k(
            normalise(model.encode([q_prefix + t for t in OFF_TOPIC.values()])), chunk_vecs, 1)
        report[name] = {
            "recall_by_language": per_lang,
            "recall_non_english": float(np.mean([v for k, v in per_lang.items() if k != "en"])),
            "top1_distance_on_topic_p90": float(np.percentile(on_topic, 90)),
            "top1_distance_off_topic_min": float(off_dist.min()),
            "query_ms": query_ms,
        }

    print(f"\ndocument recall@{args.k} against the shipped English retriever's English results\n")
    print(f"{'lang':5}" + "".join(f"{n.split('/')[-1][:22]:>24}" for n in report))
    for lang in langs:
        print(f"{lang:5}" + "".join(f"{r['recall_by_language'][lang]:>24.2f}" for r in report.values()))
    print()
    for label, key, fmt in [("non-English mean recall", "recall_non_english", ".2f"),
                            ("on-topic top-1 distance, p90", "top1_distance_on_topic_p90", ".3f"),
                            ("off-topic top-1 distance, min", "top1_distance_off_topic_min", ".3f"),
                            ("query embed ms (CPU)", "query_ms", ".0f")]:
        print(label)
        print(" " * 5 + "".join(f"{format(r[key], fmt):>24}" for r in report.values()))
    (HERE / "multilingual-retrieval.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
