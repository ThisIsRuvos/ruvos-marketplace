"""FastMCP application entrypoint."""

from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from ruvos_google_docs_mcp.auth import build_auth_provider, install_log_redaction
from ruvos_google_docs_mcp.config import GOOGLE_REVOKE_URL, Settings
from ruvos_google_docs_mcp.tools import register_tools


def create_app(settings: Settings | None = None) -> FastMCP:
    """Create the configured FastMCP server."""
    install_log_redaction()
    cfg = settings or Settings.from_env()

    auth = build_auth_provider(cfg)
    # Enable upstream token revocation when Cursor disconnects (POST /revoke).
    auth._upstream_revocation_endpoint = GOOGLE_REVOKE_URL

    mcp = FastMCP(
        name="Ruvos Google Docs",
        instructions=(
            "Create and edit Google Docs in place for the authenticated user via the "
            "Docs API (documents.batchUpdate). Use create_doc to mint a Doc, "
            "replace_body for headings (H1–H3), bullets, numbered lists, tables, and "
            "full body replace, get_doc to read it back, and batch_update_doc for a "
            "follow-up edit on the same documentId (for example replaceAllText). "
            "The deliverable is the Google Doc URL. Do not upload HTML, Word/.docx, "
            "or raw markdown as the final artifact. Do not use the featured Google "
            "Drive connector to create the file — it cannot style or replace the body. "
            "All operations are user-scoped."
        ),
        auth=auth,
    )

    register_tools(mcp)

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "ruvos-google-docs-mcp"})

    return mcp
