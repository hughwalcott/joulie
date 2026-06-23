"""Ingest documents from resources/ into ChromaDB for Joulie's RAG pipeline.

Usage:
    source .venv/bin/activate
    python ingest.py            # incremental (skip unchanged files)
    python ingest.py --rebuild  # wipe collection and re-ingest everything
"""
import argparse
import hashlib
import json
from pathlib import Path

import chromadb
import pdfplumber
from sentence_transformers import SentenceTransformer

from joulie import config

REPO_ROOT = Path(__file__).parent
RESOURCES_DIR = REPO_ROOT / "resources"
MANIFEST_PATH = REPO_ROOT / "ingest_manifest.json"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 160


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def load_hashes(manifest_path: Path) -> dict[str, str]:
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text())


def save_hashes(manifest_path: Path, hashes: dict[str, str]) -> None:
    manifest_path.write_text(json.dumps(hashes, indent=2, sort_keys=True))


def extract_pdf(path: Path, source: str) -> list[dict]:
    pages = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            # Filter out very short lines (headers/footers/page numbers).
            lines = [ln for ln in text.splitlines() if len(ln.strip()) >= 4]
            cleaned = "\n".join(lines).strip()
            if cleaned:
                pages.append({"text": cleaned, "page": i, "source": source})
    return pages


def extract_md(path: Path, source: str) -> list[dict]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    return [{"text": text, "page": 0, "source": source}]


def chunk_text(text: str, source: str, page: int, file_hash_short: str) -> list[dict]:
    chunks = []
    step = CHUNK_SIZE - CHUNK_OVERLAP
    start = 0
    idx = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        body = text[start:end].strip()
        if body:
            chunks.append({
                "id": f"{file_hash_short}_p{page}_c{idx}",
                "text": body,
                "metadata": {
                    "source": source,
                    "page": page,
                    "chunk_index": idx,
                },
            })
            idx += 1
        if end >= len(text):
            break
        start += step
    return chunks


def ingest_file(path: Path, rel: str, file_hash: str, collection, embed_model) -> int:
    short = file_hash[:8]
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        pages = extract_pdf(path, rel)
    elif suffix == ".md":
        pages = extract_md(path, rel)
    else:
        print(f"  [skip] unsupported format: {rel}")
        return 0

    all_chunks: list[dict] = []
    for page in pages:
        all_chunks.extend(chunk_text(page["text"], rel, page["page"], short))

    if not all_chunks:
        print(f"  [empty] no text extracted from {rel}")
        return 0

    # Drop any existing chunks for this file (matched by source metadata) so a
    # changed file doesn't leave stale chunks behind.
    collection.delete(where={"source": rel})

    ids = [c["id"] for c in all_chunks]
    texts = [c["text"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]
    embeddings = embed_model.encode(texts, show_progress_bar=False, convert_to_numpy=True).tolist()

    collection.upsert(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
    return len(all_chunks)


def main():
    parser = argparse.ArgumentParser(description="Ingest resources/ into ChromaDB.")
    parser.add_argument("--rebuild", action="store_true", help="Wipe collection and re-ingest everything.")
    args = parser.parse_args()

    if not RESOURCES_DIR.exists():
        raise SystemExit(f"resources/ not found at {RESOURCES_DIR}")

    print(f"[ingest] loading embedding model '{config.EMBED_MODEL}'...")
    embed_model = SentenceTransformer(config.EMBED_MODEL)

    print(f"[ingest] opening ChromaDB at {config.CHROMA_PATH}")
    client = chromadb.PersistentClient(path=config.CHROMA_PATH)

    if args.rebuild:
        try:
            client.delete_collection(config.CHROMA_COLLECTION)
            print(f"[ingest] wiped collection '{config.CHROMA_COLLECTION}'")
        except Exception:
            pass
        if MANIFEST_PATH.exists():
            MANIFEST_PATH.unlink()

    collection = client.get_or_create_collection(
        config.CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    hashes = load_hashes(MANIFEST_PATH)
    new_hashes = dict(hashes)

    files = sorted(p for p in RESOURCES_DIR.rglob("*") if p.is_file() and p.suffix.lower() in {".pdf", ".md"})
    if not files:
        print("[ingest] no .pdf or .md files found under resources/")
        return

    total_chunks = 0
    for path in files:
        rel = str(path.relative_to(REPO_ROOT))
        h = hash_file(path)
        if hashes.get(rel) == h and not args.rebuild:
            print(f"  [skip] unchanged: {rel}")
            continue

        print(f"  [ingest] {rel}")
        added = ingest_file(path, rel, h, collection, embed_model)
        new_hashes[rel] = h
        total_chunks += added
        print(f"    -> {added} chunks")

    save_hashes(MANIFEST_PATH, new_hashes)
    print(f"\n[ingest] done. {total_chunks} chunks added/updated. Collection size: {collection.count()}")


if __name__ == "__main__":
    main()
