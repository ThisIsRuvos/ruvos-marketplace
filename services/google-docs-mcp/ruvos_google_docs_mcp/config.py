"""Environment-driven configuration (no secrets in repo)."""

from __future__ import annotations

import os
from dataclasses import dataclass

# Least privilege for in-place Docs edits (architect confirm, no Option 1 veto).
# `documents` authorizes documents.create / documents.get / documents.batchUpdate.
# Drive file-create / parent (`drive.file`) is not requested: this server does
# not set a parent folder and does not upload a blob. Add `drive.file` only if
# a Workspace parent folder becomes required. Do not add full `drive`, Gmail,
# or Calendar. openid + userinfo.email match the Chat middle layer so the
# token has a subject.
OPENID_SCOPES: tuple[str, ...] = (
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
)
DOCUMENTS_SCOPE = "https://www.googleapis.com/auth/documents"

OAUTH_SCOPES: tuple[str, ...] = OPENID_SCOPES + (DOCUMENTS_SCOPE,)

# Cursor MCP OAuth redirect URIs — exact-match allowlist, same as Google Chat.
CURSOR_REDIRECT_URIS: tuple[str, ...] = (
    "http://localhost:8787/callback",
    "https://www.cursor.com/agents/mcp/oauth/callback",
)

DOCS_API_URL = "https://docs.googleapis.com/v1"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"

# Docs API indexes are UTF-16 code units. Cap payload size before we build requests.
MAX_BLOCKS = 200
MAX_TEXT_CHARS = 100_000
MAX_TABLE_ROWS = 50
MAX_TABLE_COLS = 20
MAX_BATCH_REQUESTS = 100
MAX_TITLE_CHARS = 250


@dataclass(frozen=True, slots=True)
class Settings:
    google_client_id: str
    google_client_secret: str
    base_url: str
    jwt_signing_key: str
    storage_encryption_key: str
    port: int
    host: str
    log_level: str

    @classmethod
    def from_env(cls) -> Settings:
        missing = [
            name
            for name, value in {
                "GOOGLE_CLIENT_ID": os.environ.get("GOOGLE_CLIENT_ID"),
                "GOOGLE_CLIENT_SECRET": os.environ.get("GOOGLE_CLIENT_SECRET"),
                "BASE_URL": os.environ.get("BASE_URL"),
                "JWT_SIGNING_KEY": os.environ.get("JWT_SIGNING_KEY"),
                "STORAGE_ENCRYPTION_KEY": os.environ.get("STORAGE_ENCRYPTION_KEY"),
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return cls(
            google_client_id=os.environ["GOOGLE_CLIENT_ID"],
            google_client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
            base_url=os.environ["BASE_URL"].rstrip("/"),
            jwt_signing_key=os.environ["JWT_SIGNING_KEY"],
            storage_encryption_key=os.environ["STORAGE_ENCRYPTION_KEY"],
            port=int(os.environ.get("PORT", "8080")),
            host=os.environ.get("HOST", "0.0.0.0"),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        )
