"""Ingest documents from knowledge_base/ into ChromaDB for Joulie's RAG pipeline.

Every corpus file has YAML frontmatter (title, source_url, publisher,
content_stance, licence, source_date, document_id). We parse the frontmatter
for metadata, chunk the body only, and store rich per-chunk metadata so the
retriever can surface stance/publisher/URL to the LLM context.

Usage:
    source .venv/bin/activate
    python ingest.py            # incremental (skip unchanged files)
    python ingest.py --rebuild  # wipe collection and re-ingest everything
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from joulie import config

REPO_ROOT = Path(__file__).parent
KB_DIR = Path(config.KNOWLEDGE_BASE_PATH)
MANIFEST_PATH = REPO_ROOT / "ingest_manifest.json"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# Files that live in the corpus but aren't content themselves.
SKIP_NAMES = {"MANIFEST.md", "README.md", ".DS_Store"}

# Publisher folder → short label used in retrieved context blocks.
PUBLISHER_SHORT = {
    "EA Website": "EA",
    "EECA Website": "EECA",
    "CommComm Website": "ComComm",
    "MBIE Website": "MBIE",
    "Rewiring Website": "Rewiring",
}

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


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


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (metadata, body). If no frontmatter, returns ({}, text)."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm_text, body = m.group(1), m.group(2)
    # Minimal YAML parser — the corpus uses only 'key: value' at the top level,
    # with optional quoted string values. No nested structures, no lists.
    meta: dict = {}
    for line in fm_text.splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # Strip # inline comments and surrounding quotes.
        if "#" in value and not (value.startswith('"') or value.startswith("'")):
            value = value.split("#", 1)[0].rstrip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        meta[key] = value
    return meta, body.strip()


def normalise_stance(meta: dict) -> str:
    """Reduce the descriptive content_stance / publisher into a short tag."""
    stance = (meta.get("content_stance") or "").lower()
    publisher = (meta.get("publisher") or "").lower()
    if "rewiring" in publisher:
        return "advocacy"
    if stance.startswith("advocacy") or "advocacy" in stance:
        return "advocacy"
    if stance.startswith("signposting") or "signposting" in stance:
        return "reference"
    return "authoritative"


def publisher_short(rel_path: str, meta: dict) -> str:
    """Prefer the frontmatter publisher's short label; fall back to folder."""
    top = rel_path.split("/", 2)[1] if "/" in rel_path else ""
    if top in PUBLISHER_SHORT:
        return PUBLISHER_SHORT[top]
    # Fallback — try to derive from full publisher name.
    pub = (meta.get("publisher") or "").lower()
    for short in ("EA", "EECA", "MBIE"):
        if short.lower() in pub:
            return short
    if "commerce" in pub:
        return "ComComm"
    if "rewiring" in pub:
        return "Rewiring"
    return "unknown"


def chunk_body(body: str, source: str, meta: dict, short_hash: str) -> list[dict]:
    chunks = []
    step = CHUNK_SIZE - CHUNK_OVERLAP
    start = 0
    idx = 0
    while start < len(body):
        end = min(start + CHUNK_SIZE, len(body))
        text = body[start:end].strip()
        if text:
            chunks.append({
                "id": f"{short_hash}_c{idx}",
                "text": text,
                "metadata": {
                    "source": source,
                    "chunk_index": idx,
                    "publisher_short": publisher_short(source, meta),
                    "publisher": meta.get("publisher", "unknown")[:200],
                    "stance": normalise_stance(meta),
                    "title": (meta.get("title") or "")[:200],
                    "section": (meta.get("section") or "")[:200],
                    "source_url": meta.get("source_url") or "",
                    "source_date": meta.get("source_date") or "",
                    "document_id": meta.get("document_id") or "",
                },
            })
            idx += 1
        if end >= len(body):
            break
        start += step
    return chunks


def ingest_file(path: Path, rel: str, file_hash: str, collection, embed_model) -> int:
    short = file_hash[:8]
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        print(f"  [empty] {rel}")
        return 0

    meta, body = parse_frontmatter(text)
    if not meta:
        print(f"  [warn] {rel} — no frontmatter, ingesting body as-is")
    if not body.strip():
        print(f"  [empty body] {rel}")
        return 0

    all_chunks = chunk_body(body, rel, meta, short)
    if not all_chunks:
        return 0

    # Drop any stale chunks for this file before re-inserting.
    collection.delete(where={"source": rel})

    ids = [c["id"] for c in all_chunks]
    texts = [c["text"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]
    embeddings = embed_model.encode(texts, show_progress_bar=False, convert_to_numpy=True).tolist()

    collection.upsert(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
    return len(all_chunks)


def main():
    parser = argparse.ArgumentParser(description="Ingest knowledge_base/ into ChromaDB.")
    parser.add_argument("--rebuild", action="store_true", help="Wipe collection and re-ingest everything.")
    args = parser.parse_args()

    if not KB_DIR.exists():
        raise SystemExit(f"knowledge_base/ not found at {KB_DIR}")

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

    files = sorted(
        p for p in KB_DIR.rglob("*.md")
        if p.is_file() and p.name not in SKIP_NAMES
    )
    if not files:
        print(f"[ingest] no .md files found under {KB_DIR}")
        return

    total_chunks = 0
    for path in files:
        rel = str(path.relative_to(REPO_ROOT))
        h = hash_file(path)
        if hashes.get(rel) == h and not args.rebuild:
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
