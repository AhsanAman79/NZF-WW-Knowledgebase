"""Ollama client for embeddings and (optional) answer synthesis."""
from __future__ import annotations

import httpx

from .config import settings


class OllamaError(RuntimeError):
    pass


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return an embedding vector for each input text via Ollama."""
    vectors: list[list[float]] = []
    url = f"{settings.ollama_base_url}/api/embeddings"
    with httpx.Client(timeout=120.0) as client:
        for text in texts:
            resp = client.post(url, json={"model": settings.embedding_model, "prompt": text})
            if resp.status_code != 200:
                raise OllamaError(
                    f"Embedding request failed ({resp.status_code}): {resp.text[:300]}"
                )
            data = resp.json()
            embedding = data.get("embedding")
            if not embedding:
                raise OllamaError(f"No embedding returned for model '{settings.embedding_model}'")
            vectors.append(embedding)
    return vectors


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


def synthesize_answer(query: str, contexts: list[str]) -> str | None:
    """Optional: use a chat model to synthesize an answer from retrieved context.

    Returns None if no chat model is configured.
    """
    if not settings.chat_enabled:
        return None
    context_block = "\n\n---\n\n".join(contexts)
    prompt = (
        "You are the NZF Worldwide knowledge assistant. Answer the question using ONLY "
        "the context below. If the answer is not in the context, say you don't have that "
        "information. Be concise and cite the entity/area when relevant.\n\n"
        f"Context:\n{context_block}\n\nQuestion: {query}\n\nAnswer:"
    )
    url = f"{settings.ollama_base_url}/api/generate"
    with httpx.Client(timeout=180.0) as client:
        resp = client.post(
            url, json={"model": settings.chat_model, "prompt": prompt, "stream": False}
        )
        if resp.status_code != 200:
            raise OllamaError(f"Chat request failed ({resp.status_code}): {resp.text[:300]}")
        return resp.json().get("response", "").strip() or None


def health() -> bool:
    """Check whether the Ollama server is reachable."""
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{settings.ollama_base_url}/api/tags")
            return resp.status_code == 200
    except httpx.HTTPError:
        return False
