"""OAuth Authorization Server for Cursor via FastMCP GoogleProvider (OAuthProxy).

Mirrors ``services/google-chat-mcp`` (Ruvos AS + DCR + PKCE). This process is a
sibling MCP so Docs write scopes are not added to the Chat Connect consent.
Ops reuse the existing Ruvos Google OAuth client — add the Docs scopes and this
service's redirect URI. Do not create a second Google client and do not put a
client secret in Cursor.
"""

from __future__ import annotations

import logging
import os
import re

from cryptography.fernet import Fernet
from fastmcp.server.auth.providers.google import GoogleProvider
from key_value.aio.stores.memory import MemoryStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

from ruvos_google_docs_mcp.config import (
    CURSOR_REDIRECT_URIS,
    OAUTH_SCOPES,
    Settings,
)
from ruvos_google_docs_mcp.redis_store import build_redis_store

# Never log bearer tokens, refresh tokens, or secrets.
_SENSITIVE_PATTERNS = re.compile(
    r"(access_token|refresh_token|client_secret|authorization|bearer|"
    r"STORAGE_ENCRYPTION_KEY|JWT_SIGNING_KEY|GOCSPX-)[^\s]*",
    re.IGNORECASE,
)


class _RedactSensitiveFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _SENSITIVE_PATTERNS.sub("[REDACTED]", record.msg)
        if record.args:
            record.args = tuple(
                _SENSITIVE_PATTERNS.sub("[REDACTED]", str(arg))
                if isinstance(arg, str)
                else arg
                for arg in record.args
            )
        return True


def install_log_redaction() -> None:
    """Strip token-like substrings from all log records."""
    root = logging.getLogger()
    if not any(isinstance(f, _RedactSensitiveFilter) for f in root.filters):
        root.addFilter(_RedactSensitiveFilter())


def install_ruvos_consent_theme() -> None:
    """Swap FastMCP default consent HTML for the Ruvos-branded template."""
    import fastmcp.server.auth.oauth_proxy.consent as consent_module

    from ruvos_google_docs_mcp.consent_theme import create_ruvos_consent_html

    consent_module.create_consent_html = create_ruvos_consent_html


def build_auth_provider(settings: Settings) -> GoogleProvider:
    """Build a fail-closed OAuth AS: Cursor DCR → our AS → Google OAuth.

    Security locks (same as Google Chat):
    - User-scoped upstream tokens (no shared broker token)
    - Exact-match Cursor redirect allowlist
    - Encrypted per-user token storage at rest
    - Upstream revocation on disconnect (configured in server.py)
    - Consent screen on every authorization (confused-deputy defense)
    """
    install_ruvos_consent_theme()

    use_memory = os.environ.get("USE_MEMORY_STORAGE", "").lower() in {
        "1",
        "true",
        "yes",
    }
    redis_url = os.environ.get("REDIS_URL")

    if redis_url:
        client_storage = FernetEncryptionWrapper(
            key_value=build_redis_store(redis_url),
            fernet=Fernet(settings.storage_encryption_key.encode()),
        )
    elif use_memory:
        client_storage = FernetEncryptionWrapper(
            key_value=MemoryStore(),
            fernet=Fernet(settings.storage_encryption_key.encode()),
        )
    else:
        # None → FastMCP creates encrypted disk store keyed by jwt_signing_key.
        client_storage = None

    return GoogleProvider(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        base_url=settings.base_url,
        required_scopes=list(OAUTH_SCOPES),
        valid_scopes=list(OAUTH_SCOPES),
        allowed_client_redirect_uris=list(CURSOR_REDIRECT_URIS),
        jwt_signing_key=settings.jwt_signing_key,
        client_storage=client_storage,
        require_authorization_consent=True,
    )
