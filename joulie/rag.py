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

    def retrieve(self, query: str) -> list[dict[str, Any]]:
        if not query.strip() or self.collection.count() == 0:
            return []
        embedding = self.embed_model.encode([query], convert_to_numpy=True).tolist()
        result = self.collection.query(
            query_embeddings=embedding,
            n_results=self.top_k,
        )
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]

        chunks: list[dict[str, Any]] = []
        for doc, meta, dist in zip(docs, metas, dists):
            if dist > self.distance_threshold:
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
