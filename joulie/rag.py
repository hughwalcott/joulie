from pathlib import Path

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

    def retrieve(self, query: str) -> list[dict]:
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

        chunks = []
        for doc, meta, dist in zip(docs, metas, dists):
            if dist > self.distance_threshold:
                continue
            chunks.append({
                "text": doc,
                "source": meta.get("source", "unknown"),
                "page": meta.get("page", 0),
                "distance": dist,
            })
        return chunks

    @staticmethod
    def format_context(chunks: list[dict]) -> str:
        blocks = []
        for c in chunks:
            page_label = f"p.{c['page']}" if c.get("page") else "n/a"
            blocks.append(f"--- [{c['source']}, {page_label}] ---\n{c['text']}")
        return "\n\n".join(blocks)

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
