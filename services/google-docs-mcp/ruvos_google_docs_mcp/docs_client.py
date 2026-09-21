"""User-scoped Google Docs API client (create, get, batchUpdate).

Edits are applied in place on a Google Doc. This client does not upload HTML,
Word/.docx, or markdown files.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from ruvos_google_docs_mcp.blocks import (
    BlockError,
    body_end_index,
    build_cell_fill_requests,
    compile_text_run,
    delete_body_request,
    document_url,
    find_table_element,
    insert_table_request,
    segment_blocks,
    summarize_document,
    validate_blocks,
)
from ruvos_google_docs_mcp.config import (
    DOCS_API_URL,
    DOCUMENTS_SCOPE,
    MAX_BATCH_REQUESTS,
)

_DOC_URL_RE = re.compile(
    r"docs\.google\.com/document/d/([a-zA-Z0-9_-]+)",
    re.IGNORECASE,
)
_DOC_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{8,128}$")

# Body edits Annie needs, plus the structural requests a follow-up edit uses.
# Unknown keys are rejected so this cannot become a file-upload proxy.
ALLOWED_BATCH_REQUESTS = frozenset(
    {
        "insertText",
        "deleteContentRange",
        "updateTextStyle",
        "updateParagraphStyle",
        "createParagraphBullets",
        "deleteParagraphBullets",
        "insertTable",
        "insertTableRow",
        "insertTableColumn",
        "deleteTableRow",
        "deleteTableColumn",
        "updateTableCellStyle",
        "updateTableColumnProperties",
        "updateTableRowStyle",
        "mergeTableCells",
        "unmergeTableCells",
        "pinTableHeaderRows",
        "replaceAllText",
        "updateDocumentStyle",
        "insertPageBreak",
        "insertSectionBreak",
        "insertInlineImage",
    }
)

_GET_FIELDS = "documentId,title,revisionId,body,lists"

IN_PLACE_NOTE = (
    "Edited the Google Doc in place via documents.batchUpdate. "
    "Refresh the Doc to see the change. "
    "The deliverable is this Google Doc — not HTML, Word/.docx, or a markdown upload."
)


class DocsApiError(Exception):
    """Raised when the Docs API returns an error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def normalize_document_id(value: str) -> str:
    """Accept a document id or a docs.google.com/document/d/... URL."""
    if not isinstance(value, str):
        raise BlockError("document_id must be a string.")
    raw = value.strip()
    match = _DOC_URL_RE.search(raw)
    if match:
        return match.group(1)
    if _DOC_ID_RE.match(raw):
        return raw
    raise BlockError(
        "document_id must be a Google Doc id or a "
        "https://docs.google.com/document/d/<id>/edit URL."
    )


def validate_batch_requests(requests: Any) -> list[dict[str, Any]]:
    """Fail closed unless every entry is one allowed documents.batchUpdate request."""
    if not isinstance(requests, list) or not requests:
        raise BlockError("requests must be a non-empty list of Docs API request objects.")
    if len(requests) > MAX_BATCH_REQUESTS:
        raise BlockError(f"requests exceeds the limit of {MAX_BATCH_REQUESTS}.")

    cleaned: list[dict[str, Any]] = []
    for index, request in enumerate(requests):
        if not isinstance(request, dict) or len(request) != 1:
            raise BlockError(
                f"requests[{index}] must be an object with exactly one Docs API request key."
            )
        key = next(iter(request))
        if key not in ALLOWED_BATCH_REQUESTS:
            raise BlockError(
                f"requests[{index}] uses unsupported request '{key}'. "
                "Only Google Docs documents.batchUpdate body edits are accepted "
                "(insertText, replaceAllText, updateParagraphStyle, insertTable, ...). "
                "Do not upload HTML, Word/.docx, or markdown."
            )
        cleaned.append(request)
    return cleaned


async def create_document(
    access_token: str,
    title: str,
    *,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Create a blank Google Doc via documents.create. Returns id, title, and URL."""
    payload = await _request(
        "POST",
        f"{DOCS_API_URL}/documents",
        access_token,
        json_body={"title": title},
        timeout=timeout,
    )
    document_id = payload.get("documentId")
    if not isinstance(document_id, str) or not document_id:
        raise DocsApiError("Docs API create response did not include documentId.")
    return {
        "documentId": document_id,
        "title": payload.get("title") or title,
        "url": document_url(document_id),
    }


async def get_document(
    access_token: str,
    document_id: str,
    *,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Fetch a document (body + lists) for readback and table cell indexes."""
    return await _request(
        "GET",
        f"{DOCS_API_URL}/documents/{document_id}",
        access_token,
        params={"fields": _GET_FIELDS},
        timeout=timeout,
    )


async def batch_update_document(
    access_token: str,
    document_id: str,
    requests: list[dict[str, Any]],
    *,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Apply documents.batchUpdate requests in place. Returns the API response."""
    if not requests:
        raise BlockError("Refusing to call batchUpdate with an empty request list.")
    return await _request(
        "POST",
        f"{DOCS_API_URL}/documents/{document_id}:batchUpdate",
        access_token,
        json_body={"requests": requests},
        timeout=timeout,
    )


async def apply_structured_body(
    access_token: str,
    document_id: str,
    blocks: Any,
    *,
    mode: str = "replace",
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Replace or append structured blocks via one or more batchUpdate calls.

    Tables are inserted in their own batchUpdate, then filled from a fresh
    documents.get, because the Docs API will not honor cell insert indexes in
    the same batch as insertTable.
    """
    if isinstance(mode, str):
        mode = mode.strip().lower()
    if mode not in ("replace", "append"):
        raise BlockError("mode must be 'replace' or 'append'.")

    normalized = validate_blocks(blocks)
    document = await get_document(access_token, document_id, timeout=timeout)
    end_index = body_end_index(document)
    cursor = 1 if mode == "replace" else max(end_index - 1, 1)
    pending_delete = delete_body_request(end_index) if mode == "replace" else None

    for kind, payload in segment_blocks(normalized):
        if kind == "text":
            text_requests, inserted = compile_text_run(payload, insert_at=cursor)
            batch: list[dict[str, Any]] = []
            if pending_delete is not None:
                batch.append(pending_delete)
                pending_delete = None
            batch.extend(text_requests)
            if batch:
                await batch_update_document(
                    access_token, document_id, batch, timeout=timeout
                )
            cursor += inserted
            continue

        rows = payload["rows"]
        batch = []
        if pending_delete is not None:
            batch.append(pending_delete)
            pending_delete = None
        table_start = cursor
        batch.append(
            insert_table_request(
                index=table_start,
                rows=len(rows),
                columns=len(rows[0]),
            )
        )
        await batch_update_document(access_token, document_id, batch, timeout=timeout)
        document = await get_document(access_token, document_id, timeout=timeout)
        table_element = find_table_element(document, table_start)
        fill = build_cell_fill_requests(
            table_element,
            rows,
            header=payload["header"],
        )
        if fill:
            await batch_update_document(
                access_token, document_id, fill, timeout=timeout
            )
            document = await get_document(access_token, document_id, timeout=timeout)
            table_element = find_table_element(document, table_start)
        cursor = int(table_element["endIndex"])

    if pending_delete is not None:
        await batch_update_document(
            access_token, document_id, [pending_delete], timeout=timeout
        )

    updated = await get_document(access_token, document_id, timeout=timeout)
    summary = summarize_document(updated)
    summary["mode"] = mode
    summary["message"] = IN_PLACE_NOTE
    return summary


async def read_document_summary(
    access_token: str,
    document_id: str,
    *,
    timeout: float = 30.0,
) -> dict[str, Any]:
    document = await get_document(access_token, document_id, timeout=timeout)
    summary = summarize_document(document)
    summary["message"] = (
        "Read the Google Doc in place. To change it, call replace_body or "
        "batch_update_doc on this documentId. Do not export to Word, HTML, or markdown."
    )
    return summary


async def _request(
    method: str,
    url: str,
    access_token: str,
    *,
    json_body: dict[str, Any] | None = None,
    params: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(
            method,
            url,
            headers=headers,
            json=json_body,
            params=params,
        )
    return _parse_response(response)


def _parse_response(response: httpx.Response) -> dict[str, Any]:
    if response.status_code == 401:
        raise DocsApiError(
            "Google Docs authentication failed or token expired. "
            "Reconnect Ruvos Google Docs in Cursor.",
            status_code=401,
        )
    if response.status_code == 403:
        detail = _extract_error_message(response)
        raise DocsApiError(
            "Google Docs refused the call (HTTP 403). "
            f"Disconnect and reconnect Ruvos Google Docs so consent includes "
            f"{DOCUMENTS_SCOPE}. Detail: {detail}",
            status_code=403,
        )
    if response.status_code == 404:
        raise DocsApiError(
            "Google Doc not found or not visible to this user.",
            status_code=404,
        )
    if response.status_code >= 400:
        detail = _extract_error_message(response)
        raise DocsApiError(
            f"Docs API error (HTTP {response.status_code}): {detail}",
            status_code=response.status_code,
        )
    if not response.content:
        return {}
    payload = response.json()
    if not isinstance(payload, dict):
        raise DocsApiError("Docs API returned a non-object JSON body.")
    return payload


def _extract_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        text = response.text.strip()
        return text[:300] if text else "empty error body"
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()[:500]
    if isinstance(error, str) and error.strip():
        return error.strip()[:500]
    return "unknown Docs API error"
