"""SharePoint integration via Microsoft Graph (app-only / client credentials).

Uploads land in the configured document library under a folder structure:
    <Entity>/<Area>/<filename>
Requires an Entra app registration with Sites.Selected (granted on the target
site) or Sites.ReadWrite.All application permission.
"""
from __future__ import annotations

import urllib.parse

import httpx
import msal

from .config import settings

_GRAPH = "https://graph.microsoft.com/v1.0"
_SCOPE = ["https://graph.microsoft.com/.default"]

_token_cache: dict[str, str] = {}


class SharePointError(RuntimeError):
    pass


def _get_token() -> str:
    app = msal.ConfidentialClientApplication(
        client_id=settings.client_id,
        client_credential=settings.client_secret,
        authority=f"https://login.microsoftonline.com/{settings.tenant_id}",
    )
    result = app.acquire_token_for_client(scopes=_SCOPE)
    if "access_token" not in result:
        raise SharePointError(
            f"Token error: {result.get('error')}: {result.get('error_description')}"
        )
    return result["access_token"]


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_get_token()}"}


def _get_site_id(client: httpx.Client) -> str:
    if "site_id" in _token_cache:
        return _token_cache["site_id"]
    path = settings.sharepoint_site_path.strip("/")
    url = f"{_GRAPH}/sites/{settings.sharepoint_hostname}:/{path}"
    resp = client.get(url, headers=_headers())
    if resp.status_code != 200:
        raise SharePointError(f"Cannot resolve site ({resp.status_code}): {resp.text[:300]}")
    site_id = resp.json()["id"]
    _token_cache["site_id"] = site_id
    return site_id


def _get_drive_id(client: httpx.Client, site_id: str) -> str:
    if "drive_id" in _token_cache:
        return _token_cache["drive_id"]
    url = f"{_GRAPH}/sites/{site_id}/drives"
    resp = client.get(url, headers=_headers())
    if resp.status_code != 200:
        raise SharePointError(f"Cannot list drives ({resp.status_code}): {resp.text[:300]}")
    drives = resp.json().get("value", [])
    target = settings.sharepoint_library.lower()
    for drive in drives:
        if drive.get("name", "").lower() == target:
            _token_cache["drive_id"] = drive["id"]
            return drive["id"]
    # Fall back to the default document library
    if drives:
        _token_cache["drive_id"] = drives[0]["id"]
        return drives[0]["id"]
    raise SharePointError("No document libraries found on the site.")


def upload_file(filename: str, data: bytes, entity: str, area: str) -> tuple[str, str]:
    """Upload a file to <Entity>/<Area>/<filename>. Returns (web_url, item_id)."""
    with httpx.Client(timeout=120.0) as client:
        site_id = _get_site_id(client)
        drive_id = _get_drive_id(client, site_id)

        folder = f"{entity}/{area}"
        item_path = urllib.parse.quote(f"{folder}/{filename}")
        session_url = (
            f"{_GRAPH}/sites/{site_id}/drives/{drive_id}/root:/{item_path}:/createUploadSession"
        )
        resp = client.post(
            session_url,
            headers=_headers(),
            json={"item": {"@microsoft.graph.conflictBehavior": "rename"}},
        )
        if resp.status_code not in (200, 201):
            raise SharePointError(
                f"Cannot create upload session ({resp.status_code}): {resp.text[:300]}"
            )
        upload_url = resp.json()["uploadUrl"]

        total = len(data)
        chunk = 5 * 1024 * 1024  # 5 MiB
        item: dict = {}
        start = 0
        # Empty files: single zero-length PUT
        if total == 0:
            put = client.put(
                upload_url,
                headers={"Content-Range": "bytes */0", "Content-Length": "0"},
                content=b"",
            )
            item = put.json() if put.content else {}
        while start < total:
            end = min(start + chunk, total)
            put = client.put(
                upload_url,
                headers={
                    "Content-Length": str(end - start),
                    "Content-Range": f"bytes {start}-{end - 1}/{total}",
                },
                content=data[start:end],
            )
            if put.status_code not in (200, 201, 202):
                raise SharePointError(f"Upload failed ({put.status_code}): {put.text[:300]}")
            if put.status_code in (200, 201):
                item = put.json()
            start = end

    return item.get("webUrl", ""), item.get("id", "")


def check_access() -> tuple[bool, str]:
    """Verify token + site/drive access. Returns (ok, message)."""
    try:
        with httpx.Client(timeout=30.0) as client:
            site_id = _get_site_id(client)
            drive_id = _get_drive_id(client, site_id)
        return True, f"OK (site={site_id[:12]}..., drive={drive_id[:12]}...)"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
