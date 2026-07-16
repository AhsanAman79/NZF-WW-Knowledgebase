"""Domain schema: NZF entities, areas, document types, and API models."""
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
# PLACEHOLDER: replace with the real areas once provided.
AREAS: list[str] = [
    "CEO",
    "Finance",
    "Fundraising",
    "Distribution",
    "Governance",
    "Operations",
    "Marketing & Communications",
    "Community",
    "HR & People",
    "Legal & Compliance",
    "IT / AI / Tech",
    "Programmes & Impact",
    "Other",
]

# --- Document types -> filename prefix ---
# Order matters (shown in the dropdown). "Other" is the default.
DOC_TYPES: list[dict[str, str]] = [
    {"label": "Report", "prefix": "RPT"},
    {"label": "Finance", "prefix": "FIN"},
    {"label": "Policy / Governance", "prefix": "POL"},
    {"label": "Minutes", "prefix": "MIN"},
    {"label": "Presentation", "prefix": "PRE"},
    {"label": "Strategy", "prefix": "STR"},
    {"label": "Transcript", "prefix": "TRN"},
    {"label": "Communication", "prefix": "COM"},
    {"label": "Organisation", "prefix": "ORG"},
    {"label": "Data", "prefix": "DAT"},
    {"label": "Other", "prefix": "OTH"},
]

_DOC_TYPE_LABELS = {d["label"] for d in DOC_TYPES}
_DOC_TYPE_PREFIX = {d["label"]: d["prefix"] for d in DOC_TYPES}


def is_valid_doc_type(label: str) -> bool:
    return label in _DOC_TYPE_LABELS


def prefix_for(label: str | None) -> str:
    return _DOC_TYPE_PREFIX.get(label or "", "OTH")


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    stored_filename: str
    entity: str
    area: str
    doc_type: str
    title: str | None = None
    sharepoint_url: str | None = None
    chunks_indexed: int
    extracted_chars: int
    sharepoint_uploaded: bool
    duplicate: bool = False


class SearchRequest(BaseModel):
    query: str
    entity: str | None = None
    area: str | None = None
    doc_type: str | None = None
    top_k: int | None = None


class SearchResultItem(BaseModel):
    document_id: str
    filename: str
    entity: str
    area: str
    doc_type: str | None = None
    title: str | None = None
    upload_date: str | None = None
    sharepoint_url: str | None = None
    snippet: str
    score: float


class SearchResponse(BaseModel):
    query: str
    answer: str | None = None
    results: list[SearchResultItem]


class ImportRequest(BaseModel):
    url: str
    entity: str | None = None
    area: str | None = None
    doc_type: str | None = None
