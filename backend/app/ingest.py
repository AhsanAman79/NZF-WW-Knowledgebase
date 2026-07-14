"""Ingestion pipeline: extract -> chunk -> embed -> store."""
from __future__ import annotations

from . import embeddings, vectorstore
from .config import settings
from .extraction import extract_text


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping character windows on paragraph boundaries."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        # Try to break on a paragraph/sentence boundary near the end.
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
    filename: str,
    data: bytes,
    entity: str,
    area: str,
    sharepoint_url: str | None = None,
    sharepoint_item_id: str | None = None,
) -> tuple[str, int, int]:
    """Extract, chunk, embed and store a document.

    Returns (document_id, chunks_indexed, extracted_chars).
    """
    text = extract_text(filename, data)
    extracted_chars = len(text)
    chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        doc_id = vectorstore.add_document(
            filename, entity, area, [], [], sharepoint_url, sharepoint_item_id
        )
        return doc_id, 0, extracted_chars

    vectors = embeddings.embed_texts(chunks)
    doc_id = vectorstore.add_document(
        filename, entity, area, chunks, vectors, sharepoint_url, sharepoint_item_id
    )
    return doc_id, len(chunks), extracted_chars
