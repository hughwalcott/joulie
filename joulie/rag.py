from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

from joulie import config


@dataclass(frozen=True)
class Source:
    """One publisher whose material was put in front of the model for a turn.

    Deliberately NOT called a citation: these are the chunks retrieval placed in
    the prompt, which is not the same as what the answer actually leaned on. The
    stance travels with the publisher so an advocacy source can never be
    displayed as if it were a regulator.
    """
    publisher: str
    stance: str


class Retriever:
    def __init__(
        self,
        chroma_path: str = config.CHROMA_PATH,
        collection_name: str = config.CHROMA_COLLECTION,
        embed_model: str = config.EMBED_MODEL,
        top_k: int = config.RAG_TOP_K,
        distance_threshold: float = config.RAG_DISTANCE_THRESHOLD,
        multilingual: bool = True,
    ):
        print(f"[rag] loading embedding model '{embed_model}'...")
        self.embed_model = SentenceTransformer(embed_model)
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.client.get_or_create_collection(
            collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self.top_k = top_k
        self.distance_threshold = distance_threshold
        print(f"[rag] {self.collection.count()} chunks indexed")

        self.ml_model = None
        self.ml_collection = None
        if multilingual and (set(config.LANGUAGES) | set(config.TEXT_ONLY_LANGUAGES)) - {"en"}:
            self._load_multilingual()

    def _load_multilingual(self) -> None:
        try:
            collection = self.client.get_collection(config.MULTILINGUAL_CHROMA_COLLECTION)
        except Exception:
            collection = None
        if collection is None or collection.count() == 0:
            print(f"[rag] no '{config.MULTILINGUAL_CHROMA_COLLECTION}' collection — "
                  f"non-English questions will retrieve on their English translation. "
                  f"Run ingest.py to build it.")
            return
        if collection.count() != self.collection.count():
            print(f"[rag] WARNING: multilingual collection has {collection.count()} chunks "
                  f"against {self.collection.count()} — run ingest.py to resync")
        print(f"[rag] loading multilingual embedding model '{config.MULTILINGUAL_EMBED_MODEL}'...")
        # CPU on purpose: a single short query embeds in ~7ms there, and Metal is
        # already contended by Ollama and XTTS. When that memory ran out, MPS
        # returned corrupt embeddings without raising (evals/multilingual_retrieval.py).
        self.ml_model = SentenceTransformer(config.MULTILINGUAL_EMBED_MODEL, device="cpu")
        self.ml_collection = collection

    def handles(self, lang: str) -> bool:
        """Whether a question in `lang` can be searched as asked, without first
        being translated to English."""
        return (lang == "en" or (self.ml_collection is not None
                                 and lang in config.RAG_MULTILINGUAL_LANGUAGES))

    def retrieve(self, query: str, lang: str = "en") -> list[dict[str, Any]]:
        if lang != "en" and self.handles(lang):
            model, collection = self.ml_model, self.ml_collection
            threshold = config.RAG_MULTILINGUAL_DISTANCE_THRESHOLD
        else:
            model, collection, threshold = self.embed_model, self.collection, self.distance_threshold
        if not query.strip() or collection.count() == 0:
            return []
        embedding = model.encode([query], convert_to_numpy=True).tolist()
        result = collection.query(
            query_embeddings=embedding,
            n_results=self.top_k,
        )
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]

        chunks: list[dict[str, Any]] = []
        for doc, meta, dist in zip(docs, metas, dists):
            if dist > threshold:
                continue
            chunks.append({
                "text": doc,
                "source": meta.get("source", "unknown"),
                "publisher": meta.get("publisher", "unknown"),
                "publisher_short": meta.get("publisher_short", "unknown"),
                "stance": meta.get("stance", "authoritative"),
                "title": meta.get("title", ""),
                "section": meta.get("section", ""),
                "source_url": meta.get("source_url", ""),
                "source_date": meta.get("source_date", ""),
                "document_id": meta.get("document_id", ""),
                "distance": dist,
            })
        return chunks

    @staticmethod
    def summarise_sources(chunks: list[dict[str, Any]]) -> tuple[Source, ...]:
        """Collapse retrieved chunks to one entry per publisher, most-retrieved
        first. Several chunks routinely come from one document, and a kiosk panel
        has room for publishers, not chunks. A method rather than a module
        function so joulie.llm can reach it through the retriever it already
        holds — importing joulie.rag would drag chromadb and sentence-transformers
        into every RAG-disabled run."""
        counts: dict[Source, int] = {}
        for c in chunks:
            publisher = c.get("publisher_short") or c.get("publisher") or "unknown"
            source = Source(publisher=publisher, stance=c.get("stance", "authoritative"))
            counts[source] = counts.get(source, 0) + 1
        return tuple(sorted(counts, key=lambda s: -counts[s]))

    @staticmethod
    def format_context(chunks: list[dict[str, Any]]) -> str:
        """Group chunks by stance so the LLM sees the authoritative/advocacy
        split up-front. Advocacy is labelled explicitly so the model knows to
        attribute rather than state as fact."""
        if not chunks:
            return ""

        buckets: dict[str, list[dict[str, Any]]] = {
            "authoritative": [],
            "advocacy": [],
            "vendor": [],
            "reference": [],
        }
        for c in chunks:
            # Unknown stances land in "reference", never "authoritative" — a
            # typo in a frontmatter tag must not promote a sales page to
            # regulator status.
            buckets.get(c["stance"], buckets["reference"]).append(c)

        parts: list[str] = []

        def render_chunk(c: dict[str, Any]) -> str:
            title = c.get("title") or c.get("source", "")
            pub = c.get("publisher_short") or c.get("publisher", "")
            date = c.get("source_date", "")
            header = f"### [{pub}] {title}"
            if date:
                header += f"  ({date})"
            return f"{header}\n{c['text']}"

        if buckets["authoritative"]:
            parts.append("## Authoritative sources (New Zealand government regulators)")
            parts.extend(render_chunk(c) for c in buckets["authoritative"])
        if buckets["advocacy"]:
            parts.append(
                "## Advocacy — Rewiring Aotearoa (attribute claims to Rewiring, not as neutral fact)"
            )
            parts.extend(render_chunk(c) for c in buckets["advocacy"])
        if buckets["vendor"]:
            parts.append(
                "## Manufacturer specifications (vendor material — these are the "
                "manufacturer's own claims. Quote figures as the manufacturer's, "
                "never as an independent finding, and never as a recommendation "
                "or endorsement of the brand)"
            )
            parts.extend(render_chunk(c) for c in buckets["vendor"])
        if buckets["reference"]:
            parts.append("## Reference / signposting")
            parts.extend(render_chunk(c) for c in buckets["reference"])

        return "\n\n".join(parts)

    @classmethod
    def available(cls, chroma_path: str = config.CHROMA_PATH) -> bool:
        path = Path(chroma_path)
        if not path.exists():
            return False
        try:
            client = chromadb.PersistentClient(path=chroma_path)
            collection = client.get_or_create_collection(config.CHROMA_COLLECTION)
            return collection.count() > 0
        except Exception:
            return False
