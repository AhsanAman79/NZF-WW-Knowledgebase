"""Domain schema: NZF entities, areas, and API request/response models."""
from __future__ import annotations

from pydantic import BaseModel

# --- NZF entities (fixed list) ---
ENTITIES: list[str] = [
    "UK",
    "Canada",
    "Australia",
    "Netherlands",
    "Germany",
    "WorldWide",
]

# --- Areas / departments ---
# PLACEHOLDER: replace this list with the real areas once provided.
# The upload form and search filters read from this list, so updating it
# here is all that is needed.
AREAS: list[str] = [
    "Finance",
    "Fundraising",
    "Governance",
    "Operations",
    "Marketing & Communications",
    "HR & People",
    "Legal & Compliance",
    "IT",
    "Programmes & Impact",
    "Other",
]


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    entity: str
    area: str
    sharepoint_url: str | None = None
    chunks_indexed: int
    extracted_chars: int
    sharepoint_uploaded: bool


class SearchRequest(BaseModel):
    query: str
    entity: str | None = None
    area: str | None = None
    top_k: int | None = None


class SearchResultItem(BaseModel):
    document_id: str
    filename: str
    entity: str
    area: str
    sharepoint_url: str | None = None
    snippet: str
    score: float


class SearchResponse(BaseModel):
    query: str
    answer: str | None = None
    results: list[SearchResultItem]
