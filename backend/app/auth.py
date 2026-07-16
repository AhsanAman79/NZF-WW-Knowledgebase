"""Microsoft Entra (multi-tenant) OIDC login, restricted to allowed tenants.

Flow: /oauth2/login -> Microsoft -> /oauth2/callback. The id_token signature is
verified against Microsoft's JWKS, the audience must be our client id, and the
tenant id (tid) must be in the allowed list. On success a signed session cookie
is set. Enforcement is done by middleware in main.py.
"""
from __future__ import annotations

import secrets
import urllib.parse

import httpx
import jwt
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .config import settings

router = APIRouter()

_BASE = "https://login.microsoftonline.com/organizations/oauth2/v2.0"
_AUTHORIZE = f"{_BASE}/authorize"
_TOKEN = f"{_BASE}/token"
_JWKS = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
_SCOPE = "openid profile email"

# JWKS client caches signing keys across requests.
_jwk_client = jwt.PyJWKClient(_JWKS) if settings.auth_enabled else None


def _error_page(message: str, status: int) -> HTMLResponse:
    html = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Access denied</title>"
        "<style>body{font-family:system-ui,sans-serif;background:#f5f3f2;color:#1c1c1c;"
        "display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}"
        ".box{background:#fff;border:1px solid #e6e2e0;border-radius:14px;padding:32px;max-width:440px;text-align:center}"
        "h1{color:#d6282c;font-size:20px}a{color:#d6282c;font-weight:600}</style></head>"
        f"<body><div class='box'><h1>Access denied</h1><p>{message}</p>"
        "<p><a href='/oauth2/login'>Try again</a></p></div></body></html>"
    )
    return HTMLResponse(html, status_code=status)


@router.get("/oauth2/login")
def login(request: Request):
    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)
    request.session["oauth_state"] = state
    request.session["oauth_nonce"] = nonce
    params = {
        "client_id": settings.login_client_id,
        "response_type": "code",
        "redirect_uri": settings.redirect_uri,
        "response_mode": "query",
        "scope": _SCOPE,
        "state": state,
        "nonce": nonce,
    }
    return RedirectResponse(f"{_AUTHORIZE}?{urllib.parse.urlencode(params)}")


@router.get("/oauth2/callback")
def callback(request: Request):
    params = request.query_params
    if params.get("error"):
        return _error_page(
            params.get("error_description", params.get("error", "Login failed")), 400
        )
    code = params.get("code", "")
    state = params.get("state", "")
    if not code or state != request.session.get("oauth_state"):
        return _error_page("Invalid or expired login state. Please try again.", 400)

    data = {
        "client_id": settings.login_client_id,
        "client_secret": settings.login_client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.redirect_uri,
        "scope": _SCOPE,
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(_TOKEN, data=data)
        if resp.status_code != 200:
            return _error_page("Sign-in failed (token exchange).", 502)
        id_token = resp.json().get("id_token")
        if not id_token:
            return _error_page("Sign-in failed (no token).", 502)
        signing_key = _jwk_client.get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.login_client_id,
            options={"verify_iss": False},
        )
    except Exception:  # noqa: BLE001
        return _error_page("Could not verify your sign-in. Please try again.", 401)

    if claims.get("nonce") != request.session.get("oauth_nonce"):
        return _error_page("Invalid login (nonce mismatch).", 401)
    if claims.get("tid", "") not in settings.allowed_tenants:
        return _error_page(
            "Your organization is not authorized to access this knowledgebase.", 403
        )

    request.session.pop("oauth_state", None)
    request.session.pop("oauth_nonce", None)
    request.session["user"] = {
        "name": claims.get("name"),
        "email": claims.get("preferred_username") or claims.get("email"),
        "tid": claims.get("tid"),
    }
    return RedirectResponse("/")


@router.get("/oauth2/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/oauth2/login")


@router.get("/api/me")
def me(request: Request):
    return request.session.get("user") or {}
