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

# 500 is load-bearing for retrieval QUALITY, not just recall volume, and was
# measured rather than guessed. Halving it to 250 to cut prefill cost (the
# retrieved block is the only part of the prompt Ollama cannot serve from its KV
# cache) cost figure recall 0.557 -> 0.416 across the 107-question bank, with 9
# questions dropping from full recall to none. The mechanism is not truncation
# but displacement: smaller chunks changed WHICH sources won the top-4, shifting
# answers off authoritative figures and onto advocacy material — EECA's $7,000
# heat pump install became Rewiring's "$4,000 to $10,000", MBIE's 56% process
# heat figure vanished, and answers attributing to Rewiring nearly doubled
# (9 -> 16). Don't trade this for the ~1.85s of prefill.
# See logs/latency-analysis.md, "Third pass", and
# evals/results-tuning-{a-baseline,b-chunk250}.json.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# Files that live in the corpus but aren't content themselves. INDEX.md is
# folder navigation and REVIEW.md is a maintainer's audit of the corpus — both
# would retrieve as if they were NZ energy facts.
SKIP_NAMES = {"MANIFEST.md", "README.md", "INDEX.md", "REVIEW.md", ".DS_Store"}

# Publisher folder → short label used in retrieved context blocks.
PUBLISHER_SHORT = {
    "EA Website": "EA",
    "EECA Website": "EECA",
    "CommComm Website": "ComComm",
    "MBIE Website": "MBIE",
    "Rewiring Website": "Rewiring",
}

# The Consumer Tech / Policy Data / Product Specs corpora label provenance with
# an `authority:` field rather than the older `content_stance:`. Map it to the
# short label used in context headers and to a stance, because the folder name
# there describes a topic ("Policy Data"), not a publisher.
AUTHORITY = {
    "EECA":                      ("EECA", "authoritative"),
    "Electricity Authority":     ("EA", "authoritative"),
    "MBIE":                      ("MBIE", "authoritative"),
    "Commerce Commission":       ("ComComm", "authoritative"),
    "Beehive":                   ("Beehive", "authoritative"),
    "Climate Change Commission": ("Climate Commission", "authoritative"),
    "Ministry for the Environment": ("MfE", "authoritative"),
    "Ministry of Transport":     ("Min. of Transport", "authoritative"),
    "NZTA":                      ("NZTA", "authoritative"),
    "Tenancy Services":          ("Tenancy Services", "authoritative"),
    # An industry body, not a regulator — attributed for the same reason
    # Rewiring Aotearoa is.
    "BusinessNZ Energy Council": ("BusinessNZ Energy Council", "advocacy"),
    # Explanatory technology write-ups drawn from overseas and supplier pages.
    "supplier documentation":    ("supplier documentation", "reference"),
}

# Publisher name -> short label. Anchored patterns, never bare substrings: a
# plain `"ea" in publisher` test matched every "... New Zealand" manufacturer
# and labelled BYD, Kia, Nissan and friends as EA, the Electricity Authority.
_PUBLISHER_PATTERNS = (
    ("EECA", r"\beeca\b|energy efficiency"),
    ("EA", r"\belectricity authority\b"),
    ("MBIE", r"\bmbie\b|ministry of business"),
    ("ComComm", r"\bcommerce commission\b"),
    ("Rewiring", r"\brewiring\b"),
)

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


# Editorial asides written to whoever maintains the corpus, not to a visitor —
# every product-spec file ends with one, and they retrieve as if they were NZ
# energy facts ("Reconcile against RightCar's official record...").
_MAINTAINER_NOTE_RE = re.compile(
    r"^(#{1,6})\s*Note for corpus maintainers\b.*?(?=^\1\s|\Z)",
    re.MULTILINE | re.DOTALL | re.IGNORECASE,
)


def strip_maintainer_notes(body: str) -> str:
    """Drop 'Note for corpus maintainers' sections, up to the next heading of the
    same level or end of file."""
    return _MAINTAINER_NOTE_RE.sub("", body).strip()


def normalise_stance(meta: dict) -> str:
    """Reduce the frontmatter's provenance fields into a short tag.

    "authoritative" must mean a New Zealand regulator. Manufacturer material
    gets its own "vendor" tag rather than being waved through as authoritative:
    a Tesla or BYD spec sheet is a sales claim, and the corpus rule is that
    non-regulators are attributed, never presented as neutral fact.
    """
    # The product-specs schema is the only one carrying a brand.
    if (meta.get("brand") or "").strip():
        return "vendor"
    authority = (meta.get("authority") or "").strip()
    if authority in AUTHORITY:
        return AUTHORITY[authority][1]

    stance = (meta.get("content_stance") or "").lower()
    publisher = (meta.get("publisher") or "").lower()
    if "rewiring" in publisher:
        return "advocacy"
    if stance.startswith("advocacy") or "advocacy" in stance:
        return "advocacy"
    if stance.startswith("signposting") or "signposting" in stance:
        return "reference"
    if stance:
        return "authoritative"
    # No stance field at all: the legacy EECA corpus is like this. Trust it only
    # when the publisher itself resolves to a known regulator — anything else
    # stays "reference" rather than being promoted to regulator status.
    for short, pattern in _PUBLISHER_PATTERNS:
        if re.search(pattern, publisher):
            return "advocacy" if short == "Rewiring" else "authoritative"
    return "reference"


def publisher_short(rel_path: str, meta: dict) -> str:
    """Short label shown in context headers and the kiosk's sources panel.

    Frontmatter first, folder second: the newer corpora are foldered by topic
    ("Policy Data"), so the folder says nothing about who published a file.
    """
    brand = (meta.get("brand") or "").strip()
    if brand:
        return brand[:40]
    authority = (meta.get("authority") or "").strip()
    if authority in AUTHORITY:
        return AUTHORITY[authority][0]
    top = rel_path.split("/", 2)[1] if "/" in rel_path else ""
    if top in PUBLISHER_SHORT:
        return PUBLISHER_SHORT[top]
    pub = (meta.get("publisher") or "").lower()
    for short, pattern in _PUBLISHER_PATTERNS:
        if re.search(pattern, pub):
            return short
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
    body = strip_maintainer_notes(body)
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
