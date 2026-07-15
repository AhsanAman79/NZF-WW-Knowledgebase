"""Ingestion pipeline: name -> extract -> chunk -> embed -> store."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from . import embeddings, vectorstore
from .config import settings
from .extraction import extract_text

_UMLAUTS = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue"}


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def slugify(text: str) -> str:
    """Lowercase, umlauts transliterated, hyphen-separated, ascii-only."""
    for k, v in _UMLAUTS.items():
        text = text.replace(k, v)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "dokument"


def build_stored_filename(prefix: str, title: str | None, original_filename: str) -> str:
    """{PREFIX}_{slug}-{YYYY-MM-DD}.{ext}"""
    ext = Path(original_filename).suffix.lower()
    base = title if title else Path(original_filename).stem
    slug = slugify(base)[:60]
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{prefix}_{slug}-{date}{ext}"


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start, length = 0, len(text)
    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            window = text[start:end]
            for sep in ("\n\n", "\n", ". "):
                pos = window.rfind(sep)
                if pos > chunk_size * 0.5:
                    end = start + pos + len(sep)
                    break
        chunks.append(text[start:end].strip())
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def ingest_document(
    *,
    stored_filename: str,
    original_filename: str,
    data: bytes,
    title: str | None,
    entity: str,
    area: str,
    doc_type: str,
    description: str | None,
    content_hash_value: str,
    sharepoint_url: str | None = None,
    sharepoint_item_id: str | None = None,
) -> tuple[str, int, int, str]:
    """Extract, chunk, embed and store. Returns (document_id, chunks_indexed, extracted_chars, upload_date)."""
    text = extract_text(original_filename, data)
    extracted_chars = len(text)
    # Fallback: if no text could be extracted (e.g. legacy .doc, images-only PDF,
    # iWork files), index the document by its metadata so it stays findable.
    embed_source = text
    if not text.strip():
        parts = [p for p in (title, doc_type, Path(original_filename).stem, description) if p]
        embed_source = " — ".join(parts)
    chunks = chunk_text(embed_source, settings.chunk_size, settings.chunk_overlap)
    vectors = embeddings.embed_texts(chunks) if chunks else []
    doc_id, upload_date = vectorstore.add_document(
        filename=stored_filename,
        original_filename=original_filename,
        title=title,
        entity=entity,
        area=area,
        doc_type=doc_type,
        description=description,
        file_size=len(data),
        content_hash=content_hash_value,
        chunks=chunks,
        embeddings=vectors,
        sharepoint_url=sharepoint_url,
        sharepoint_item_id=sharepoint_item_id,
    )
    return doc_id, len(chunks), extracted_chars, upload_date
