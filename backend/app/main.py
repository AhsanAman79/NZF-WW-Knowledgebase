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
    DOC_TYPES,
    ENTITIES,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    UploadResponse,
    is_valid_doc_type,
    prefix_for,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    vectorstore.init_db()
    yield


app = FastAPI(title="NZF WW Knowledgebase API", version="0.2.0", lifespan=lifespan)

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


@app.get("/api/doctypes")
def get_doctypes() -> list[str]:
    return [d["label"] for d in DOC_TYPES]


@app.get("/api/sharepoint/check")
def sharepoint_check() -> dict:
    if not settings.sharepoint_configured:
        return {"ok": False, "message": "SharePoint not configured (missing client secret?)."}
    ok, message = sharepoint.check_access()
    return {"ok": ok, "message": message}


@app.post("/api/upload", response_model=UploadResponse)
def upload(
    file: UploadFile = File(...),
    entity: str = Form(""),
    area: str = Form(""),
    doc_type: str = Form("Other"),
    title: str = Form(""),
    description: str = Form(""),
) -> UploadResponse:
    if entity and entity not in ENTITIES:
        raise HTTPException(400, f"Unknown entity '{entity}'.")
    if area and area not in AREAS:
        raise HTTPException(400, f"Unknown area '{area}'.")
    if doc_type and not is_valid_doc_type(doc_type):
        raise HTTPException(400, f"Unknown document type '{doc_type}'.")
    entity = entity.strip() or "Unspecified"
    area = area.strip() or "Unspecified"

    original_filename = file.filename or "upload"
    if not is_supported(original_filename):
        raise HTTPException(400, f"Unsupported file type: {original_filename}")

    data = file.file.read()
    if not data:
        raise HTTPException(400, "Empty file.")

    title_clean = title.strip() or None
    description_clean = description.strip() or None
    prefix = prefix_for(doc_type)
    chash = ingest.content_hash(data)

    # Duplicate detection: identical content already indexed -> skip.
    existing = vectorstore.find_by_hash(chash)
    if existing:
        return UploadResponse(
            document_id=existing["id"],
            filename=original_filename,
            stored_filename=existing["filename"],
            entity=existing["entity"],
            area=existing["area"],
            doc_type=doc_type,
            title=title_clean,
            sharepoint_url=existing.get("sharepoint_url"),
            chunks_indexed=0,
            extracted_chars=0,
            sharepoint_uploaded=False,
            duplicate=True,
        )

    stored_filename = ingest.build_stored_filename(prefix, title_clean, original_filename)

    # 1) Upload the original to SharePoint (if configured).
    sharepoint_url = sharepoint_item_id = None
    sharepoint_uploaded = False
    if settings.sharepoint_configured:
        try:
            sharepoint_url, sharepoint_item_id = sharepoint.upload_file(
                stored_filename, data, entity, area
            )
            sharepoint_uploaded = True
        except sharepoint.SharePointError as exc:
            raise HTTPException(502, f"SharePoint upload failed: {exc}")

    # 2) Extract, embed and index.
    try:
        doc_id, chunks_indexed, extracted_chars, _ = ingest.ingest_document(
            stored_filename=stored_filename,
            original_filename=original_filename,
            data=data,
            title=title_clean,
            entity=entity,
            area=area,
            doc_type=doc_type,
            description=description_clean,
            content_hash_value=chash,
            sharepoint_url=sharepoint_url,
            sharepoint_item_id=sharepoint_item_id,
        )
    except embeddings.OllamaError as exc:
        raise HTTPException(502, f"Embedding failed (is Ollama running?): {exc}")

    return UploadResponse(
        document_id=doc_id,
        filename=original_filename,
        stored_filename=stored_filename,
        entity=entity,
        area=area,
        doc_type=doc_type,
        title=title_clean,
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
    hits = vectorstore.search(query_vec, top_k, req.entity, req.area, req.doc_type)

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
_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
