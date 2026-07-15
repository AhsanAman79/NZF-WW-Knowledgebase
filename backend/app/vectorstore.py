"""Embedded vector store backed by SQLite + numpy cosine similarity."""
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
                original_filename TEXT,
                title TEXT,
                entity TEXT NOT NULL,
                area TEXT NOT NULL,
                doc_type TEXT,
                description TEXT,
                upload_date TEXT,
                file_size INTEGER,
                content_hash TEXT,
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
            CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(content_hash);
            CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
            """
        )


def find_by_hash(content_hash: str) -> dict | None:
    """Return an existing document with the same content hash, if any."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, filename, entity, area, sharepoint_url FROM documents "
            "WHERE content_hash = ? LIMIT 1",
            (content_hash,),
        ).fetchone()
    return dict(row) if row else None


def add_document(
    *,
    filename: str,
    original_filename: str,
    title: str | None,
    entity: str,
    area: str,
    doc_type: str,
    description: str | None,
    file_size: int,
    content_hash: str,
    chunks: list[str],
    embeddings: list[list[float]],
    sharepoint_url: str | None = None,
    sharepoint_item_id: str | None = None,
) -> tuple[str, str]:
    """Persist a document and its embedded chunks. Returns (document_id, upload_date)."""
    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO documents (id, filename, original_filename, title, entity, area, "
            "doc_type, description, upload_date, file_size, content_hash, sharepoint_url, "
            "sharepoint_item_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (doc_id, filename, original_filename, title, entity, area, doc_type, description,
             now, file_size, content_hash, sharepoint_url, sharepoint_item_id, now),
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
    return doc_id, now


def search(
    query_embedding: list[float],
    top_k: int,
    entity: str | None = None,
    area: str | None = None,
    doc_type: str | None = None,
) -> list[dict]:
    """Return the top_k most similar chunks, optionally filtered."""
    sql = (
        "SELECT c.text AS text, c.embedding AS embedding, d.id AS document_id, d.filename, "
        "d.title, d.entity, d.area, d.doc_type, d.upload_date, d.sharepoint_url "
        "FROM chunks c JOIN documents d ON c.document_id = d.id"
    )
    conditions, params = [], []
    if entity:
        conditions.append("d.entity = ?")
        params.append(entity)
    if area:
        conditions.append("d.area = ?")
        params.append(area)
    if doc_type:
        conditions.append("d.doc_type = ?")
        params.append(doc_type)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    if not rows:
        return []

    matrix = np.stack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rows])
    query = np.asarray(query_embedding, dtype=np.float32)
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
                "title": r["title"],
                "entity": r["entity"],
                "area": r["area"],
                "doc_type": r["doc_type"],
                "upload_date": r["upload_date"],
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
