from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

from joulie import config


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
    def format_context(chunks: list[dict[str, Any]]) -> str:
        """Group chunks by stance so the LLM sees the authoritative/advocacy
        split up-front. Advocacy is labelled explicitly so the model knows to
        attribute rather than state as fact."""
        if not chunks:
            return ""

        buckets: dict[str, list[dict[str, Any]]] = {
            "authoritative": [],
            "advocacy": [],
            "reference": [],
        }
        for c in chunks:
            buckets.get(c["stance"], buckets["authoritative"]).append(c)

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
