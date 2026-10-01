from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings


TOKEN_ISSUER = "quantia-backend"
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class DocumentPrincipal:
    user_id: str
    email: str | None = None


def create_access_token(user_id: str, email: str | None = None) -> str | None:
    secret = settings.auth_token_secret
    if not secret:
        return None

    now = int(time.time())
    payload = {
        "iss": TOKEN_ISSUER,
        "sub": str(user_id).strip(),
        "email": str(email or "").strip().lower() or None,
        "iat": now,
        "exp": now + settings.auth_token_ttl_seconds,
    }
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _encode_json(header)
    encoded_payload = _encode_json(payload)
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_base64url_encode(signature)}"


def decode_access_token(token: str) -> DocumentPrincipal:
    secret = settings.auth_token_secret
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AUTH_TOKEN_SECRET no esta configurado para proteger documentos.",
        )

    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".", maxsplit=2)
        header = json.loads(_base64url_decode(encoded_header))
        payload: dict[str, Any] = json.loads(_base64url_decode(encoded_payload))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise _invalid_token() from exc

    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise _invalid_token()

    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    try:
        provided = _base64url_decode_bytes(encoded_signature)
    except ValueError as exc:
        raise _invalid_token() from exc
    if not hmac.compare_digest(expected, provided):
        raise _invalid_token()

    now = int(time.time())
    try:
        expires_at = int(payload.get("exp", 0))
    except (TypeError, ValueError) as exc:
        raise _invalid_token() from exc
    user_id = str(payload.get("sub") or "").strip()
    if payload.get("iss") != TOKEN_ISSUER or not user_id or expires_at <= now:
        raise _invalid_token()

    email = str(payload.get("email") or "").strip().lower() or None
    return DocumentPrincipal(user_id=user_id, email=email)


def get_document_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> DocumentPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere un token Bearer para acceder a documentos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_access_token(credentials.credentials)


def _invalid_token() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de acceso invalido o expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _encode_json(value: dict[str, Any]) -> str:
    raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _base64url_encode(raw)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> str:
    return _base64url_decode_bytes(value).decode("utf-8")


def _base64url_decode_bytes(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("base64url invalido") from exc
