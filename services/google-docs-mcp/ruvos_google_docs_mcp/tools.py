"""User-scoped Google Docs MCP tools (fail-closed, in-place Docs API only)."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token

from ruvos_google_docs_mcp.blocks import BlockError, document_url
from ruvos_google_docs_mcp.config import MAX_TITLE_CHARS
from ruvos_google_docs_mcp.docs_client import (
    IN_PLACE_NOTE,
    DocsApiError,
    apply_structured_body,
    batch_update_document,
    create_document,
    normalize_document_id,
    read_document_summary,
    validate_batch_requests,
)

_HANDOFF_BAN = (
    "The deliverable is a Google Doc edited in place via the Docs API "
    "(documents.batchUpdate). Do not upload or hand off HTML, Word/.docx, "
    "or raw markdown as the final artifact."
)

CREATE_DOC_DESCRIPTION = (
    "Create a blank Google Doc owned by the authenticated user and return its "
    "documentId and docs.google.com URL. Optionally write the initial body in the "
    "same call by passing structured blocks (heading H1–H3, paragraph, bullets, "
    "numbered, table). "
    + _HANDOFF_BAN
)

GET_DOC_DESCRIPTION = (
    "Read a Google Doc by documentId or docs.google.com URL. Returns the title, "
    "URL, plain text, and an outline of headings, paragraphs, lists, and tables. "
    "Use this before a follow-up edit on the same documentId. "
    + _HANDOFF_BAN
)

REPLACE_BODY_DESCRIPTION = (
    "Replace or append a Google Doc body in place. blocks is a list of "
    "{type: heading, level: 1|2|3, text}, {type: paragraph, text}, "
    "{type: bullets|numbered, items: [text]}, or "
    "{type: table, header: true, rows: [[cell, ...], ...]}. "
    "mode=replace clears the existing body first; mode=append inserts at the end. "
    "Headings, lists, and tables are written with documents.batchUpdate. "
    "A second call on the same documentId is how a follow-up edit sticks. "
    + _HANDOFF_BAN
)

BATCH_UPDATE_DOC_DESCRIPTION = (
    "Apply raw Google Docs documents.batchUpdate requests to an existing documentId "
    "in place (insertText, updateParagraphStyle, createParagraphBullets, insertTable, "
    "replaceAllText, and other body-edit requests). Use this for a surgical follow-up "
    "edit after create_doc or replace_body — for example replaceAllText — and then "
    "refresh the Doc. Returns the Docs API replies plus the document URL. "
    + _HANDOFF_BAN
)


def _require_user_token() -> tuple[str, str]:
    """Return (google_access_token, user_subject). Fail closed if unauthenticated."""
    token = get_access_token()
    if token is None or not token.token:
        raise PermissionError(
            "Authentication required. Connect Ruvos Google Docs in Cursor."
        )

    subject = token.subject or token.claims.get("sub")
    if not subject:
        raise PermissionError("Authenticated token missing user identity.")

    return token.token, str(subject)


def _clean_title(title: str) -> str:
    if not isinstance(title, str):
        raise BlockError("title must be a string.")
    cleaned = title.strip()
    if not cleaned:
        raise BlockError("title must not be empty.")
    if len(cleaned) > MAX_TITLE_CHARS:
        raise BlockError(f"title exceeds {MAX_TITLE_CHARS} characters.")
    if "\x00" in cleaned or "\r" in cleaned or "\n" in cleaned:
        raise BlockError("title must be a single line.")
    return cleaned


def register_tools(mcp: FastMCP) -> None:
    """Register create / read / in-place edit tools."""

    @mcp.tool(name="create_doc", description=CREATE_DOC_DESCRIPTION)
    async def create_doc(
        title: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        access_token, _user = _require_user_token()
        cleaned_title = _clean_title(title)
        created = await create_document(access_token, cleaned_title)
        if not blocks:
            created["message"] = (
                "Created a Google Doc. Call replace_body or batch_update_doc on this "
                "documentId to edit it in place. " + IN_PLACE_NOTE
            )
            return created

        try:
            written = await apply_structured_body(
                access_token,
                created["documentId"],
                blocks,
                mode="replace",
            )
        except DocsApiError as exc:
            raise DocsApiError(
                f"Created Google Doc {created['documentId']} ({created['url']}) "
                f"but the body write failed: {exc}",
                status_code=exc.status_code,
            ) from exc
        except BlockError as exc:
            raise BlockError(
                f"Created Google Doc {created['documentId']} ({created['url']}) "
                f"but the body write failed: {exc}"
            ) from exc
        written["title"] = written.get("title") or created["title"]
        written["message"] = "Created a Google Doc and wrote the body in place. " + IN_PLACE_NOTE
        return written

    @mcp.tool(name="get_doc", description=GET_DOC_DESCRIPTION)
    async def get_doc(document_id: str) -> dict[str, Any]:
        access_token, _user = _require_user_token()
        return await read_document_summary(
            access_token,
            normalize_document_id(document_id),
        )

    @mcp.tool(name="replace_body", description=REPLACE_BODY_DESCRIPTION)
    async def replace_body(
        document_id: str,
        blocks: list[dict[str, Any]],
        mode: str = "replace",
    ) -> dict[str, Any]:
        access_token, _user = _require_user_token()
        return await apply_structured_body(
            access_token,
            normalize_document_id(document_id),
            blocks,
            mode=mode,
        )

    @mcp.tool(name="batch_update_doc", description=BATCH_UPDATE_DOC_DESCRIPTION)
    async def batch_update_doc(
        document_id: str,
        requests: list[dict[str, Any]],
    ) -> dict[str, Any]:
        access_token, _user = _require_user_token()
        doc_id = normalize_document_id(document_id)
        cleaned = validate_batch_requests(requests)
        result = await batch_update_document(access_token, doc_id, cleaned)
        return {
            "documentId": doc_id,
            "url": document_url(doc_id),
            "replies": result.get("replies"),
            "writeControl": result.get("writeControl"),
            "message": IN_PLACE_NOTE,
        }
