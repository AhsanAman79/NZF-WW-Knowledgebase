"""FastAPI application: upload + semantic search API for NZF WW Knowledgebase."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import embeddings, ingest, sharepoint, vectorstore
from .config import settings
from .extraction import is_supported
from .schemas import (
    AREAS,
    ENTITIES,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    UploadResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    vectorstore.init_db()
    yield


app = FastAPI(title="NZF WW Knowledgebase API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "ollama_reachable": embeddings.health(),
        "sharepoint_configured": settings.sharepoint_configured,
        "chat_enabled": settings.chat_enabled,
        **vectorstore.stats(),
    }


@app.get("/api/entities")
def get_entities() -> list[str]:
    return ENTITIES


@app.get("/api/areas")
def get_areas() -> list[str]:
    return AREAS


@app.get("/api/sharepoint/check")
def sharepoint_check() -> dict:
    if not settings.sharepoint_configured:
        return {"ok": False, "message": "SharePoint not configured (missing client secret?)."}
    ok, message = sharepoint.check_access()
    return {"ok": ok, "message": message}


@app.post("/api/upload", response_model=UploadResponse)
def upload(
    file: UploadFile = File(...),
    entity: str = Form(...),
    area: str = Form(...),
) -> UploadResponse:
    if entity not in ENTITIES:
        raise HTTPException(400, f"Unknown entity '{entity}'. Allowed: {ENTITIES}")
    if area not in AREAS:
        raise HTTPException(400, f"Unknown area '{area}'. Allowed: {AREAS}")
    filename = file.filename or "upload"
    if not is_supported(filename):
        raise HTTPException(400, f"Unsupported file type: {filename}")

    data = file.file.read()
    if not data:
        raise HTTPException(400, "Empty file.")

    # 1) Upload the original to SharePoint (if configured).
    sharepoint_url: str | None = None
    sharepoint_item_id: str | None = None
    sharepoint_uploaded = False
    if settings.sharepoint_configured:
        try:
            sharepoint_url, sharepoint_item_id = sharepoint.upload_file(
                filename, data, entity, area
            )
            sharepoint_uploaded = True
        except sharepoint.SharePointError as exc:
            raise HTTPException(502, f"SharePoint upload failed: {exc}")

    # 2) Extract, embed and index for semantic search.
    try:
        doc_id, chunks_indexed, extracted_chars = ingest.ingest_document(
            filename, data, entity, area, sharepoint_url, sharepoint_item_id
        )
    except embeddings.OllamaError as exc:
        raise HTTPException(502, f"Embedding failed (is Ollama running?): {exc}")

    return UploadResponse(
        document_id=doc_id,
        filename=filename,
        entity=entity,
        area=area,
        sharepoint_url=sharepoint_url,
        chunks_indexed=chunks_indexed,
        extracted_chars=extracted_chars,
        sharepoint_uploaded=sharepoint_uploaded,
    )


@app.post("/api/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    query = req.query.strip()
    if not query:
        raise HTTPException(400, "Empty query.")
    if req.entity and req.entity not in ENTITIES:
        raise HTTPException(400, f"Unknown entity '{req.entity}'.")
    if req.area and req.area not in AREAS:
        raise HTTPException(400, f"Unknown area '{req.area}'.")

    try:
        query_vec = embeddings.embed_text(query)
    except embeddings.OllamaError as exc:
        raise HTTPException(502, f"Embedding failed (is Ollama running?): {exc}")

    top_k = req.top_k or settings.search_top_k
    hits = vectorstore.search(query_vec, top_k, req.entity, req.area)

    answer = None
    if hits and settings.chat_enabled:
        try:
            answer = embeddings.synthesize_answer(query, [h["snippet"] for h in hits])
        except embeddings.OllamaError:
            answer = None

    return SearchResponse(
        query=query,
        answer=answer,
        results=[SearchResultItem(**h) for h in hits],
    )



# --- Serve the built frontend (single-service production mode) ---
# In development the frontend runs on the Vite dev server (port 3000) and proxies
# to this API. In production, `npm run build` produces frontend/dist which is
# served here so everything runs from one process/port.
_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
