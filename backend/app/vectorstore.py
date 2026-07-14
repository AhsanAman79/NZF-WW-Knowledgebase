"""Embedded vector store backed by SQLite + numpy cosine similarity.

Suitable for the expected (management-level) document volume. Embeddings are
stored as float32 blobs; search loads candidate vectors and ranks by cosine
similarity in memory. Can be swapped for pgvector/Qdrant later without changing
the public interface.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .config import settings

_DB_PATH = settings.data_dir / "knowledgebase.sqlite"


def _connect() -> sqlite3.Connection:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                entity TEXT NOT NULL,
                area TEXT NOT NULL,
                sharepoint_url TEXT,
                sharepoint_item_id TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                embedding BLOB NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_documents_entity ON documents(entity);
            CREATE INDEX IF NOT EXISTS idx_documents_area ON documents(area);
            CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
            """
        )


def add_document(
    filename: str,
    entity: str,
    area: str,
    chunks: list[str],
    embeddings: list[list[float]],
    sharepoint_url: str | None = None,
    sharepoint_item_id: str | None = None,
) -> str:
    """Persist a document and its embedded chunks. Returns the document id."""
    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO documents (id, filename, entity, area, sharepoint_url, "
            "sharepoint_item_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (doc_id, filename, entity, area, sharepoint_url, sharepoint_item_id, now),
        )
        rows = []
        for i, (text, emb) in enumerate(zip(chunks, embeddings)):
            blob = np.asarray(emb, dtype=np.float32).tobytes()
            rows.append((str(uuid.uuid4()), doc_id, i, text, blob))
        conn.executemany(
            "INSERT INTO chunks (id, document_id, chunk_index, text, embedding) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
    return doc_id


def search(
    query_embedding: list[float],
    top_k: int,
    entity: str | None = None,
    area: str | None = None,
) -> list[dict]:
    """Return the top_k most similar chunks, optionally filtered by entity/area."""
    sql = (
        "SELECT c.id AS chunk_id, c.text AS text, c.embedding AS embedding, "
        "d.id AS document_id, d.filename, d.entity, d.area, d.sharepoint_url "
        "FROM chunks c JOIN documents d ON c.document_id = d.id"
    )
    conditions, params = [], []
    if entity:
        conditions.append("d.entity = ?")
        params.append(entity)
    if area:
        conditions.append("d.area = ?")
        params.append(area)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    if not rows:
        return []

    matrix = np.stack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rows])
    query = np.asarray(query_embedding, dtype=np.float32)

    # Cosine similarity
    matrix_norm = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-8)
    query_norm = query / (np.linalg.norm(query) + 1e-8)
    scores = matrix_norm @ query_norm

    order = np.argsort(-scores)[:top_k]
    results = []
    for idx in order:
        r = rows[int(idx)]
        results.append(
            {
                "document_id": r["document_id"],
                "filename": r["filename"],
                "entity": r["entity"],
                "area": r["area"],
                "sharepoint_url": r["sharepoint_url"],
                "snippet": r["text"],
                "score": float(scores[int(idx)]),
            }
        )
    return results


def stats() -> dict:
    with _connect() as conn:
        docs = conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"]
        chunks = conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()["n"]
    return {"documents": docs, "chunks": chunks}
