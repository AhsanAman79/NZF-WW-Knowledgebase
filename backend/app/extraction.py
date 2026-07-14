"""Text extraction from supported document formats.

Supported: PDF, DOCX, XLSX, PPTX, HTML/HTM, VTT, TXT/MD/CSV.
Returns plain text; extraction is best-effort and never raises on empty content.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".pptx", ".html", ".htm",
    ".vtt", ".txt", ".md", ".csv",
}


def is_supported(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS


def extract_text(filename: str, data: bytes) -> str:
    """Dispatch extraction based on file extension."""
    ext = Path(filename).suffix.lower()
    try:
        if ext == ".pdf":
            return _from_pdf(data)
        if ext == ".docx":
            return _from_docx(data)
        if ext == ".xlsx":
            return _from_xlsx(data)
        if ext == ".pptx":
            return _from_pptx(data)
        if ext in {".html", ".htm"}:
            return _from_html(data)
        if ext == ".vtt":
            return _from_vtt(data)
        if ext in {".txt", ".md", ".csv"}:
            return _decode(data)
    except Exception as exc:  # noqa: BLE001 - extraction is best-effort
        return f"[extraction error for {filename}: {exc}]"
    return ""


def _decode(data: bytes) -> str:
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _from_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts = [(page.extract_text() or "") for page in reader.pages]
    return _clean("\n".join(parts))


def _from_docx(data: bytes) -> str:
    import docx

    doc = docx.Document(io.BytesIO(data))
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text for cell in row.cells))
    return _clean("\n".join(parts))


def _from_xlsx(data: bytes) -> str:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    parts: list[str] = []
    for ws in wb.worksheets:
        parts.append(f"# Sheet: {ws.title}")
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None]
            if cells:
                parts.append(" | ".join(cells))
    wb.close()
    return _clean("\n".join(parts))


def _from_pptx(data: bytes) -> str:
    from pptx import Presentation

    prs = Presentation(io.BytesIO(data))
    parts: list[str] = []
    for i, slide in enumerate(prs.slides, start=1):
        parts.append(f"# Slide {i}")
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    text = "".join(run.text for run in para.runs)
                    if text.strip():
                        parts.append(text)
    return _clean("\n".join(parts))


def _from_html(data: bytes) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(_decode(data), "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return _clean(soup.get_text(separator="\n"))


def _from_vtt(data: bytes) -> str:
    """Parse WebVTT subtitle/transcript files, stripping timestamps and cues."""
    text = _decode(data)
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line == "WEBVTT":
            continue
        # Skip timestamp lines like "00:00:01.000 --> 00:00:04.000"
        if "-->" in line:
            continue
        # Skip numeric cue identifiers
        if line.isdigit():
            continue
        # Remove inline tags like <v Speaker> or <00:00:01.000>
        line = re.sub(r"<[^>]+>", "", line).strip()
        if line:
            lines.append(line)
    # De-duplicate consecutive identical caption lines
    deduped: list[str] = []
    for line in lines:
        if not deduped or deduped[-1] != line:
            deduped.append(line)
    return _clean("\n".join(deduped))


def _clean(text: str) -> str:
    text = text.replace("\x00", " ")
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
