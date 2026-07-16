"""Import SharePoint content from a link using the signed-in user's delegated
Microsoft Graph token. Files are downloaded, extracted, embedded and indexed;
the search result links back to the original SharePoint location (no re-upload).
"""
from __future__ import annotations

import base64

import httpx

from . import ingest, vectorstore
from .extraction import is_supported

_GRAPH = "https://graph.microsoft.com/v1.0"
_MAX_FILES = 500


class ImportError_(RuntimeError):
    pass


def _encode_share_url(url: str) -> str:
    b64 = base64.b64encode(url.encode("utf-8")).decode("ascii")
    return "u!" + b64.rstrip("=").replace("/", "_").replace("+", "-")


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _collect_files(client: httpx.Client, token: str, item: dict, acc: list[dict]) -> None:
    if len(acc) >= _MAX_FILES:
        return
    if "folder" in item:
        drive_id = item.get("parentReference", {}).get("driveId")
        item_id = item.get("id")
        if not drive_id or not item_id:
            return
        url = f"{_GRAPH}/drives/{drive_id}/items/{item_id}/children?$top=200"
        while url and len(acc) < _MAX_FILES:
            resp = client.get(url, headers=_headers(token))
            if resp.status_code != 200:
                raise ImportError_(f"Cannot list folder ({resp.status_code}): {resp.text[:200]}")
            data = resp.json()
            for child in data.get("value", []):
                _collect_files(client, token, child, acc)
            url = data.get("@odata.nextLink")
    elif "file" in item:
        acc.append(item)


def import_from_link(url: str, token: str, entity: str, area: str, doc_type: str) -> dict:
    """Resolve a SharePoint link and index all files found under it."""
    summary = {"total": 0, "imported": 0, "duplicates": 0, "skipped": 0, "errors": 0}
    with httpx.Client(timeout=180.0) as client:
        share_id = _encode_share_url(url.strip())
        r = client.get(f"{_GRAPH}/shares/{share_id}/driveItem", headers=_headers(token))
        if r.status_code == 403:
            raise ImportError_("Access denied to this link (your account may not have permission).")
        if r.status_code != 200:
            raise ImportError_(f"Could not resolve the link ({r.status_code}). Is it a valid SharePoint/OneDrive link?")
        root = r.json()

        files: list[dict] = []
        _collect_files(client, token, root, files)
        summary["total"] = len(files)

        for f in files:
            name = f.get("name") or "file"
            try:
                if not is_supported(name):
                    summary["skipped"] += 1
                    continue
                dl = f.get("@microsoft.graph.downloadUrl")
                if not dl:
                    summary["skipped"] += 1
                    continue
                data = client.get(dl).content  # pre-authenticated URL
                chash = ingest.content_hash(data)
                if vectorstore.find_by_hash(chash):
                    summary["duplicates"] += 1
                    continue
                ingest.ingest_document(
                    stored_filename=name,
                    original_filename=name,
                    data=data,
                    title=None,
                    entity=entity,
                    area=area,
                    doc_type=doc_type,
                    description=None,
                    content_hash_value=chash,
                    sharepoint_url=f.get("webUrl"),
                    sharepoint_item_id=f.get("id"),
                )
                summary["imported"] += 1
            except Exception:  # noqa: BLE001
                summary["errors"] += 1
    return summary
