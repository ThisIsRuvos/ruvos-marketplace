"""Sequence tests: replace body compiles to batchUpdate, then a follow-up edit."""

from __future__ import annotations

import httpx
import pytest

from ruvos_google_docs_mcp.blocks import utf16_len
from ruvos_google_docs_mcp.docs_client import (
    apply_structured_body,
    create_document,
)


def _empty_with_end(end_index: int) -> dict:
    return {
        "documentId": "abcd1234ef",
        "title": "NFRHC Assessment",
        "revisionId": "1",
        "body": {
            "content": [
                {"endIndex": 1, "sectionBreak": {}},
                {
                    "startIndex": 1,
                    "endIndex": end_index,
                    "paragraph": {
                        "elements": [
                            {
                                "startIndex": 1,
                                "endIndex": end_index,
                                "textRun": {"content": "old\n"},
                            }
                        ]
                    },
                },
            ]
        },
    }


def _table_document(start: int) -> dict:
    columns = 2

    def para(row: int, col: int) -> int:
        return start + 3 + row * (1 + columns * 2) + col * 2

    def cell(index: int) -> dict:
        return {
            "content": [
                {
                    "startIndex": index,
                    "endIndex": index + 1,
                    "paragraph": {
                        "elements": [
                            {
                                "startIndex": index,
                                "endIndex": index + 1,
                                "textRun": {"content": "\n"},
                            }
                        ]
                    },
                }
            ]
        }

    end = start + 2 + 2 * (1 + 2 * columns)
    return {
        "documentId": "abcd1234ef",
        "title": "NFRHC Assessment",
        "revisionId": "2",
        "body": {
            "content": [
                {"endIndex": 1, "sectionBreak": {}},
                {
                    "startIndex": start,
                    "endIndex": end,
                    "table": {
                        "rows": 2,
                        "columns": 2,
                        "tableRows": [
                            {"tableCells": [cell(para(0, 0)), cell(para(0, 1))]},
                            {"tableCells": [cell(para(1, 0)), cell(para(1, 1))]},
                        ],
                    },
                },
            ]
        },
    }


@pytest.mark.asyncio
async def test_replace_heading_and_table_then_indexes_stick(monkeypatch: pytest.MonkeyPatch) -> None:
    batches: list[list[dict]] = []
    stage = {"value": "initial"}
    heading = "NFRHC Assessment\n"
    table_start = 1 + utf16_len(heading)

    async def fake_get(token: str, document_id: str, timeout: float = 30.0) -> dict:
        assert token == "user-token"
        assert document_id == "abcd1234ef"
        if stage["value"] == "initial":
            return _empty_with_end(30)
        return _table_document(table_start)

    async def fake_batch(
        token: str,
        document_id: str,
        requests: list[dict],
        timeout: float = 30.0,
    ) -> dict:
        assert token == "user-token"
        batches.append(requests)
        if any("insertTable" in request for request in requests):
            stage["value"] = "table"
        return {"replies": [{} for _ in requests]}

    monkeypatch.setattr(
        "ruvos_google_docs_mcp.docs_client.get_document",
        fake_get,
    )
    monkeypatch.setattr(
        "ruvos_google_docs_mcp.docs_client.batch_update_document",
        fake_batch,
    )

    summary = await apply_structured_body(
        "user-token",
        "abcd1234ef",
        [
            {"type": "heading", "level": 1, "text": "NFRHC Assessment"},
            {
                "type": "table",
                "rows": [["Requirement", "Status"], ["Access review", "Gap"]],
            },
        ],
        mode="replace",
    )

    assert summary["documentId"] == "abcd1234ef"
    assert summary["url"].endswith("/d/abcd1234ef/edit")
    assert "batchUpdate" in summary["message"]
    assert len(batches) == 3

    text_batch = batches[0]
    assert text_batch[0]["deleteContentRange"]["range"]["endIndex"] == 29
    assert text_batch[1]["insertText"]["text"] == heading
    assert text_batch[1]["insertText"]["location"]["index"] == 1
    assert (
        text_batch[2]["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"]
        == "HEADING_1"
    )

    table_batch = batches[1]
    assert table_batch == [
        {
            "insertTable": {
                "rows": 2,
                "columns": 2,
                "location": {"index": table_start},
            }
        }
    ]

    fill = batches[2]
    inserted = [request["insertText"]["text"] for request in fill if "insertText" in request]
    assert inserted == ["Gap", "Access review", "Status", "Requirement"]
    assert any(
        request.get("updateTextStyle", {}).get("textStyle", {}).get("bold") is True
        for request in fill
    )


@pytest.mark.asyncio
async def test_append_does_not_delete_existing_body(monkeypatch: pytest.MonkeyPatch) -> None:
    batches: list[list[dict]] = []

    async def fake_get(token: str, document_id: str, timeout: float = 30.0) -> dict:
        return _empty_with_end(10)

    async def fake_batch(
        token: str,
        document_id: str,
        requests: list[dict],
        timeout: float = 30.0,
    ) -> dict:
        batches.append(requests)
        return {"replies": []}

    monkeypatch.setattr("ruvos_google_docs_mcp.docs_client.get_document", fake_get)
    monkeypatch.setattr(
        "ruvos_google_docs_mcp.docs_client.batch_update_document",
        fake_batch,
    )

    await apply_structured_body(
        "user-token",
        "abcd1234ef",
        [{"type": "paragraph", "text": "Follow-up edit"}],
        mode="append",
    )

    assert len(batches) == 1
    assert "deleteContentRange" not in batches[0][0]
    assert batches[0][0]["insertText"]["location"]["index"] == 9
    assert batches[0][0]["insertText"]["text"] == "Follow-up edit\n"


@pytest.mark.asyncio
async def test_create_document_posts_docs_api_not_a_file_upload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    class FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def request(
            self,
            method: str,
            url: str,
            headers: dict | None = None,
            json: dict | None = None,
            params: dict | None = None,
        ) -> httpx.Response:
            captured["method"] = method
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return httpx.Response(
                200,
                json={"documentId": "abcdefghij", "title": "NFRHC Assessment"},
            )

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    created = await create_document("secret-token", "NFRHC Assessment")
    assert captured["method"] == "POST"
    assert captured["url"] == "https://docs.googleapis.com/v1/documents"
    assert captured["headers"]["Authorization"] == "Bearer secret-token"
    assert captured["json"] == {"title": "NFRHC Assessment"}
    assert "mimeType" not in captured["json"]
    assert created["url"] == "https://docs.google.com/document/d/abcdefghij/edit"
