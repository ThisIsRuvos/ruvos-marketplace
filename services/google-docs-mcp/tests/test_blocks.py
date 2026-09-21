"""Compiler tests for in-place Docs batchUpdate requests."""

from __future__ import annotations

import pytest

from ruvos_google_docs_mcp.blocks import (
    BlockError,
    build_cell_fill_requests,
    compile_text_run,
    delete_body_request,
    summarize_document,
    utf16_len,
    validate_blocks,
)
from ruvos_google_docs_mcp.config import DOCUMENTS_SCOPE, OAUTH_SCOPES
from ruvos_google_docs_mcp.docs_client import (
    DocsApiError,
    normalize_document_id,
    validate_batch_requests,
)
from ruvos_google_docs_mcp.docs_client import _parse_response
from ruvos_google_docs_mcp.tools import (
    BATCH_UPDATE_DOC_DESCRIPTION,
    CREATE_DOC_DESCRIPTION,
    GET_DOC_DESCRIPTION,
    REPLACE_BODY_DESCRIPTION,
)


NFRHC_BLOCKS = [
    {"type": "heading", "level": 1, "text": "NFRHC Assessment"},
    {"type": "heading", "level": 2, "text": "Scope"},
    {"type": "paragraph", "text": "Initial assessment. Status: DRAFT."},
    {"type": "heading", "level": "3", "text": "Findings"},
    {"type": "bullet_list", "items": ["Control exists", "Evidence pending"]},
    {"type": "numbered_list", "items": ["Confirm owner", "Schedule retest"]},
    {
        "type": "table",
        "header": True,
        "rows": [["Requirement", "Status"], ["Access review", "Gap"]],
    },
]


def test_oauth_scopes_are_documents_only() -> None:
    assert OAUTH_SCOPES == (
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        DOCUMENTS_SCOPE,
    )
    joined = " ".join(OAUTH_SCOPES)
    assert "drive" not in joined
    assert "gmail" not in joined
    assert "calendar" not in joined


def test_tool_descriptions_ban_word_html_and_markdown_handoff() -> None:
    for description in (
        CREATE_DOC_DESCRIPTION,
        GET_DOC_DESCRIPTION,
        REPLACE_BODY_DESCRIPTION,
        BATCH_UPDATE_DOC_DESCRIPTION,
    ):
        lowered = description.lower()
        assert "in place" in lowered
        assert "html" in lowered
        assert "docx" in lowered
        assert "markdown" in lowered


def test_rejects_html_word_and_markdown_block_types() -> None:
    for block_type in ("html", "docx", "word", "markdown"):
        with pytest.raises(BlockError, match="not a deliverable"):
            validate_blocks([{"type": block_type, "text": "<h1>No</h1>"}])


def test_nfrhc_blocks_normalize_aliases_and_heading_levels() -> None:
    blocks = validate_blocks(NFRHC_BLOCKS)
    assert [block["type"] for block in blocks] == [
        "heading",
        "heading",
        "paragraph",
        "heading",
        "bullets",
        "numbered",
        "table",
    ]
    assert blocks[3]["level"] == 3
    assert blocks[-1]["header"] is True


def test_compile_text_run_styles_headings_and_lists() -> None:
    blocks = validate_blocks(
        [
            {"type": "heading", "level": 1, "text": "Title"},
            {"type": "paragraph", "text": "Body"},
            {"type": "bullets", "items": ["One", "Two"]},
            {"type": "numbered", "items": ["First"]},
        ]
    )
    requests, inserted = compile_text_run(blocks, insert_at=1)
    assert requests[0]["insertText"]["location"]["index"] == 1
    text = requests[0]["insertText"]["text"]
    assert text == "Title\nBody\nOne\nTwo\nFirst\n"
    assert inserted == utf16_len(text)

    styles = [req["updateParagraphStyle"] for req in requests if "updateParagraphStyle" in req]
    assert styles[0]["paragraphStyle"]["namedStyleType"] == "HEADING_1"
    assert styles[0]["range"] == {"startIndex": 1, "endIndex": 1 + utf16_len("Title\n")}
    assert styles[1]["paragraphStyle"]["namedStyleType"] == "NORMAL_TEXT"
    bullets = [req["createParagraphBullets"] for req in requests if "createParagraphBullets" in req]
    assert bullets[0]["bulletPreset"] == "BULLET_DISC_CIRCLE_SQUARE"
    assert bullets[1]["bulletPreset"] == "NUMBERED_DECIMAL_ALPHA_ROMAN"
    # List range starts after Title\n + Body\n
    assert bullets[0]["range"]["startIndex"] == 1 + utf16_len("Title\nBody\n")


def test_emoji_indexes_use_utf16_code_units() -> None:
    blocks = validate_blocks([{"type": "heading", "level": 1, "text": "A😀"}])
    requests, inserted = compile_text_run(blocks, insert_at=1)
    assert inserted == utf16_len("A😀\n")
    assert inserted == 4
    style = requests[1]["updateParagraphStyle"]["range"]
    assert style["endIndex"] - style["startIndex"] == 4


def test_delete_body_keeps_trailing_newline() -> None:
    assert delete_body_request(2) is None
    delete = delete_body_request(20)
    assert delete is not None
    assert delete["deleteContentRange"]["range"] == {"startIndex": 1, "endIndex": 19}


def test_cell_fill_is_reverse_index_and_bolds_header() -> None:
    start = 7
    columns = 2

    def para(row: int, col: int) -> int:
        return start + 3 + row * (1 + columns * 2) + col * 2

    table = {
        "startIndex": start,
        "endIndex": start + 12,
        "table": {
            "tableRows": [
                {
                    "tableCells": [
                        _cell(para(0, 0)),
                        _cell(para(0, 1)),
                    ]
                },
                {
                    "tableCells": [
                        _cell(para(1, 0)),
                        _cell(para(1, 1)),
                    ]
                },
            ]
        },
    }
    requests = build_cell_fill_requests(
        table,
        [["Req", "Status"], ["Access", "Gap"]],
        header=True,
    )
    inserts = [req["insertText"] for req in requests if "insertText" in req]
    assert [item["location"]["index"] for item in inserts] == [
        para(1, 1),
        para(1, 0),
        para(0, 1),
        para(0, 0),
    ]
    assert inserts[-1]["text"] == "Req"
    bolds = [req["updateTextStyle"] for req in requests if "updateTextStyle" in req]
    assert len(bolds) == 2
    assert bolds[0]["textStyle"]["bold"] is True
    assert bolds[0]["range"]["startIndex"] == para(0, 1)


def test_ragged_table_and_h4_rejected() -> None:
    with pytest.raises(BlockError, match="expected 2"):
        validate_blocks([{"type": "table", "rows": [["a", "b"], ["only"]]}])
    with pytest.raises(BlockError, match="H1"):
        validate_blocks([{"type": "heading", "level": 4, "text": "Too deep"}])


def test_summarize_outline_round_trip_shape() -> None:
    document = {
        "documentId": "abcdefghij",
        "title": "NFRHC Assessment",
        "revisionId": "rev",
        "lists": {
            "list-1": {
                "listProperties": {
                    "nestingLevels": [{"glyphType": "GLYPH_TYPE_UNSPECIFIED"}]
                }
            },
            "list-2": {
                "listProperties": {"nestingLevels": [{"glyphType": "DECIMAL"}]}
            },
        },
        "body": {
            "content": [
                {"endIndex": 1, "sectionBreak": {}},
                _paragraph(1, 18, "NFRHC Assessment\n", "HEADING_1"),
                _paragraph(
                    18,
                    32,
                    "Control exists\n",
                    "NORMAL_TEXT",
                    bullet={"listId": "list-1", "nestingLevel": 0},
                ),
                _paragraph(
                    32,
                    48,
                    "Confirm owner\n",
                    "NORMAL_TEXT",
                    bullet={"listId": "list-2", "nestingLevel": 0},
                ),
                {
                    "startIndex": 48,
                    "endIndex": 60,
                    "table": {
                        "tableRows": [
                            {
                                "tableCells": [
                                    _cell_text(50, "Requirement"),
                                    _cell_text(54, "Status"),
                                ]
                            }
                        ]
                    },
                },
            ]
        },
    }
    summary = summarize_document(document)
    assert summary["url"] == "https://docs.google.com/document/d/abcdefghij/edit"
    assert summary["outline"][0] == {
        "type": "heading",
        "level": 1,
        "text": "NFRHC Assessment",
    }
    assert summary["outline"][1]["type"] == "bullets"
    assert summary["outline"][2]["type"] == "numbered"
    assert summary["outline"][3]["rows"] == [["Requirement", "Status"]]
    assert "NFRHC Assessment" in summary["text"]


def test_document_id_accepts_url_and_rejects_junk() -> None:
    assert (
        normalize_document_id(
            "https://docs.google.com/document/d/abcdefghij/edit?usp=sharing"
        )
        == "abcdefghij"
    )
    with pytest.raises(BlockError):
        normalize_document_id("not a doc")


def test_batch_requests_reject_non_docs_upload_keys() -> None:
    with pytest.raises(BlockError, match="Word"):
        validate_batch_requests([{"uploadFile": {"mimeType": "application/vnd.openxmlformats"}}])
    cleaned = validate_batch_requests(
        [
            {
                "replaceAllText": {
                    "containsText": {"text": "DRAFT", "matchCase": True},
                    "replaceText": "FINAL",
                }
            }
        ]
    )
    assert cleaned[0]["replaceAllText"]["replaceText"] == "FINAL"


def test_parse_response_403_tells_user_to_reconnect_for_docs_scopes() -> None:
    import httpx

    response = httpx.Response(
        403,
        json={"error": {"message": "Request had insufficient authentication scopes."}},
    )
    with pytest.raises(DocsApiError, match=DOCUMENTS_SCOPE) as caught:
        _parse_response(response)
    assert caught.value.status_code == 403


def _cell(start: int) -> dict:
    return {
        "content": [
            {
                "startIndex": start,
                "endIndex": start + 1,
                "paragraph": {
                    "elements": [
                        {
                            "startIndex": start,
                            "endIndex": start + 1,
                            "textRun": {"content": "\n"},
                        }
                    ]
                },
            }
        ]
    }


def _cell_text(start: int, text: str) -> dict:
    end = start + len(text) + 1
    return {
        "content": [
            {
                "startIndex": start,
                "endIndex": end,
                "paragraph": {
                    "elements": [
                        {
                            "startIndex": start,
                            "endIndex": end,
                            "textRun": {"content": text + "\n"},
                        }
                    ]
                },
            }
        ]
    }


def _paragraph(
    start: int,
    end: int,
    content: str,
    named_style: str,
    bullet: dict | None = None,
) -> dict:
    paragraph: dict = {
        "elements": [
            {"startIndex": start, "endIndex": end, "textRun": {"content": content}}
        ],
        "paragraphStyle": {"namedStyleType": named_style},
    }
    if bullet:
        paragraph["bullet"] = bullet
    return {"startIndex": start, "endIndex": end, "paragraph": paragraph}
