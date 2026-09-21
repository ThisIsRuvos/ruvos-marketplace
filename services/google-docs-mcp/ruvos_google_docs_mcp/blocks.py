"""Structured Google Doc blocks compiled to Docs API batchUpdate requests.

The deliverable is always a Google Doc edited in place. Callers pass headings,
paragraphs, lists, and tables — not HTML, Word, or a markdown file upload.
"""

from __future__ import annotations

from typing import Any

from ruvos_google_docs_mcp.config import (
    MAX_BLOCKS,
    MAX_TABLE_COLS,
    MAX_TABLE_ROWS,
    MAX_TEXT_CHARS,
)

HEADING_STYLES = {
    1: "HEADING_1",
    2: "HEADING_2",
    3: "HEADING_3",
}

_TEXT_TYPES = {
    "heading": "heading",
    "paragraph": "paragraph",
    "bullets": "bullets",
    "bullet_list": "bullets",
    "numbered": "numbered",
    "numbered_list": "numbered",
}

_REJECTED_TYPES = {
    "html",
    "docx",
    "doc",
    "word",
    "markdown",
    "md",
    "file",
    "upload",
}

_BULLET_PRESETS = {
    "bullets": "BULLET_DISC_CIRCLE_SQUARE",
    "numbered": "NUMBERED_DECIMAL_ALPHA_ROMAN",
}


class BlockError(ValueError):
    """Raised when structured blocks cannot be compiled to a Docs edit."""


def utf16_len(text: str) -> int:
    """Docs API indexes count UTF-16 code units, not Python code points."""
    return len(text.encode("utf-16-le")) // 2


def validate_blocks(blocks: Any) -> list[dict[str, Any]]:
    """Normalize agent blocks into the compiler's canonical shape."""
    if not isinstance(blocks, list) or not blocks:
        raise BlockError("blocks must be a non-empty list.")
    if len(blocks) > MAX_BLOCKS:
        raise BlockError(f"blocks exceeds the limit of {MAX_BLOCKS}.")

    normalized: list[dict[str, Any]] = []
    total_chars = 0
    for index, raw in enumerate(blocks):
        if not isinstance(raw, dict):
            raise BlockError(f"blocks[{index}] must be an object.")
        block_type = raw.get("type")
        if not isinstance(block_type, str):
            raise BlockError(f"blocks[{index}].type is required.")
        key = block_type.strip().lower()
        if key in _REJECTED_TYPES:
            raise BlockError(
                "HTML, Word/.docx, and raw markdown are not a deliverable. "
                "Pass structured blocks (heading, paragraph, bullets, numbered, table) "
                "so documents.batchUpdate edits the Google Doc in place."
            )
        canonical = _TEXT_TYPES.get(key)
        if canonical is None and key != "table":
            raise BlockError(
                f"blocks[{index}].type '{block_type}' is not supported. "
                "Use heading, paragraph, bullets, numbered, or table."
            )
        if key == "table":
            table = _normalize_table(raw, index)
            total_chars += sum(utf16_len(cell) for row in table["rows"] for cell in row)
            normalized.append(table)
            continue

        if canonical == "heading":
            level = _heading_level(raw.get("level", raw.get("headingLevel")), index)
            text = _require_text(raw.get("text"), index, allow_empty=False)
            total_chars += utf16_len(text)
            normalized.append({"type": "heading", "level": level, "text": text})
        elif canonical == "paragraph":
            text = _require_text(raw.get("text"), index, allow_empty=True)
            total_chars += utf16_len(text)
            normalized.append({"type": "paragraph", "text": text})
        else:
            items = raw.get("items")
            if not isinstance(items, list) or not items:
                raise BlockError(f"blocks[{index}].items must be a non-empty list.")
            cleaned: list[str] = []
            for item_index, item in enumerate(items):
                text = _require_text(
                    item,
                    index,
                    allow_empty=False,
                    label=f"blocks[{index}].items[{item_index}]",
                )
                if text.startswith("\t"):
                    raise BlockError(
                        f"blocks[{index}].items[{item_index}] must not start with a tab "
                        "(Docs removes leading tabs when creating bullets and shifts indexes)."
                    )
                total_chars += utf16_len(text)
                cleaned.append(text)
            normalized.append({"type": canonical, "items": cleaned})

        if total_chars > MAX_TEXT_CHARS:
            raise BlockError(f"Document text exceeds {MAX_TEXT_CHARS} characters.")

    if total_chars > MAX_TEXT_CHARS:
        raise BlockError(f"Document text exceeds {MAX_TEXT_CHARS} characters.")
    return normalized


def segment_blocks(
    blocks: list[dict[str, Any]],
) -> list[tuple[str, Any]]:
    """Split blocks into text runs separated by tables.

    A table cannot share a batchUpdate with later insertText that targets
    indexes inside that table (Docs shifts those indexes past the table).
    """
    segments: list[tuple[str, Any]] = []
    text_run: list[dict[str, Any]] = []
    for block in blocks:
        if block["type"] == "table":
            if text_run:
                segments.append(("text", text_run))
                text_run = []
            segments.append(("table", block))
        else:
            text_run.append(block)
    if text_run:
        segments.append(("text", text_run))
    return segments


def compile_text_run(
    blocks: list[dict[str, Any]],
    *,
    insert_at: int,
) -> tuple[list[dict[str, Any]], int]:
    """Build insertText + paragraph style + bullet requests for non-table blocks.

    Indexes assume ``blocks`` are inserted as one string at ``insert_at`` and
    that no earlier request in the same batch shifts that index.
    Returns ``(requests, utf16_units_inserted)``.
    """
    if insert_at < 1:
        raise BlockError("insert_at must be >= 1.")

    pieces: list[str] = []
    styles: list[tuple[int, int, str]] = []
    bullet_ranges: list[tuple[int, int, str]] = []
    cursor = 0

    for block in blocks:
        block_type = block["type"]
        if block_type in _BULLET_PRESETS:
            start = cursor
            for item in block["items"]:
                line = item + "\n"
                pieces.append(line)
                cursor += utf16_len(line)
            styles.append((start, cursor, "NORMAL_TEXT"))
            bullet_ranges.append((start, cursor, _BULLET_PRESETS[block_type]))
            continue

        if block_type == "heading":
            style = HEADING_STYLES[block["level"]]
            line = block["text"] + "\n"
        else:
            style = "NORMAL_TEXT"
            line = block["text"] + "\n"
        pieces.append(line)
        styles.append((cursor, cursor + utf16_len(line), style))
        cursor += utf16_len(line)

    text = "".join(pieces)
    if not text:
        return [], 0

    requests: list[dict[str, Any]] = [
        {
            "insertText": {
                "location": {"index": insert_at},
                "text": text,
            }
        }
    ]
    for start, end, style in styles:
        requests.append(_paragraph_style_request(insert_at + start, insert_at + end, style))
    for start, end, preset in bullet_ranges:
        requests.append(
            {
                "createParagraphBullets": {
                    "range": {
                        "startIndex": insert_at + start,
                        "endIndex": insert_at + end,
                    },
                    "bulletPreset": preset,
                }
            }
        )
    return requests, cursor


def delete_body_request(end_index: int) -> dict[str, Any] | None:
    """Delete existing body content, keeping the required trailing newline."""
    if end_index <= 2:
        return None
    return {
        "deleteContentRange": {
            "range": {
                "startIndex": 1,
                "endIndex": end_index - 1,
            }
        }
    }


def insert_table_request(*, index: int, rows: int, columns: int) -> dict[str, Any]:
    return {
        "insertTable": {
            "rows": rows,
            "columns": columns,
            "location": {"index": index},
        }
    }


def body_end_index(document: dict[str, Any]) -> int:
    """Return the body segment end index (empty docs are 2)."""
    content = (document.get("body") or {}).get("content") or []
    if not content:
        return 2
    end = content[-1].get("endIndex")
    if not isinstance(end, int) or end < 2:
        return 2
    return end


def find_table_element(document: dict[str, Any], start_index: int) -> dict[str, Any]:
    """Return the body table structural element that starts at ``start_index``."""
    for element in (document.get("body") or {}).get("content") or []:
        if "table" in element and element.get("startIndex") == start_index:
            return element
    raise BlockError(
        f"Inserted table was not found at index {start_index}. "
        "Refused to write cell text into a different table."
    )


def build_cell_fill_requests(
    table_element: dict[str, Any],
    rows: list[list[str]],
    *,
    header: bool,
) -> list[dict[str, Any]]:
    """Insert cell text using paragraph indexes from a documents.get response.

    Requests are ordered from the highest index so earlier cells stay put.
    Header-row text is bolded in the same batch, immediately after its insert.
    """
    indexes = _cell_paragraph_indexes(table_element)
    if len(indexes) != len(rows):
        raise BlockError(
            "Google Doc table row count does not match the requested table."
        )

    coords: list[tuple[int, int, str, int]] = []
    for row_index, row in enumerate(rows):
        if len(row) != len(indexes[row_index]):
            raise BlockError(
                "Google Doc table column count does not match the requested table."
            )
        for col_index, text in enumerate(row):
            if text:
                coords.append((row_index, col_index, text, indexes[row_index][col_index]))

    requests: list[dict[str, Any]] = []
    for row_index, _col_index, text, index in reversed(coords):
        requests.append(
            {
                "insertText": {
                    "location": {"index": index},
                    "text": text,
                }
            }
        )
        if header and row_index == 0:
            requests.append(
                {
                    "updateTextStyle": {
                        "range": {
                            "startIndex": index,
                            "endIndex": index + utf16_len(text),
                        },
                        "textStyle": {"bold": True},
                        "fields": "bold",
                    }
                }
            )
    return requests


def summarize_document(document: dict[str, Any]) -> dict[str, Any]:
    """Return a compact outline (headings, paragraphs, lists, tables) plus plain text."""
    document_id = document.get("documentId")
    outline = _outline_from_body(document)
    lines: list[str] = []
    for block in outline:
        block_type = block["type"]
        if block_type == "heading":
            lines.append(block["text"])
        elif block_type == "paragraph":
            lines.append(block["text"])
        elif block_type in ("bullets", "numbered"):
            lines.extend(block["items"])
        elif block_type == "table":
            for row in block["rows"]:
                lines.append(" | ".join(row))
    url = document_url(str(document_id)) if isinstance(document_id, str) else None
    return {
        "documentId": document_id,
        "title": document.get("title"),
        "url": url,
        "revisionId": document.get("revisionId"),
        "bodyEndIndex": body_end_index(document),
        "text": "\n".join(line for line in lines if line).strip(),
        "outline": outline,
    }


def document_url(document_id: str) -> str:
    return f"https://docs.google.com/document/d/{document_id}/edit"


def _paragraph_style_request(start: int, end: int, named_style: str) -> dict[str, Any]:
    return {
        "updateParagraphStyle": {
            "range": {"startIndex": start, "endIndex": end},
            "paragraphStyle": {"namedStyleType": named_style},
            "fields": "namedStyleType",
        }
    }


def _normalize_table(raw: dict[str, Any], index: int) -> dict[str, Any]:
    rows = raw.get("rows")
    if not isinstance(rows, list) or not rows:
        raise BlockError(f"blocks[{index}].rows must be a non-empty list of rows.")
    if len(rows) > MAX_TABLE_ROWS:
        raise BlockError(f"blocks[{index}] exceeds {MAX_TABLE_ROWS} rows.")

    normalized_rows: list[list[str]] = []
    width: int | None = None
    for row_index, row in enumerate(rows):
        if not isinstance(row, list) or not row:
            raise BlockError(
                f"blocks[{index}].rows[{row_index}] must be a non-empty list of cells."
            )
        if len(row) > MAX_TABLE_COLS:
            raise BlockError(f"blocks[{index}] exceeds {MAX_TABLE_COLS} columns.")
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise BlockError(
                f"blocks[{index}].rows[{row_index}] has {len(row)} cells; "
                f"expected {width}."
            )
        normalized_rows.append(
            [
                _require_text(
                    cell,
                    index,
                    allow_empty=True,
                    label=f"blocks[{index}].rows[{row_index}][{col_index}]",
                )
                for col_index, cell in enumerate(row)
            ]
        )

    header = raw.get("header", True)
    if not isinstance(header, bool):
        raise BlockError(f"blocks[{index}].header must be a boolean.")
    return {"type": "table", "rows": normalized_rows, "header": header}


def _heading_level(level: Any, index: int) -> int:
    if isinstance(level, str) and level.strip() in {"1", "2", "3"}:
        return int(level.strip())
    if isinstance(level, float) and level.is_integer():
        level = int(level)
    if isinstance(level, bool) or level not in (1, 2, 3):
        raise BlockError(f"blocks[{index}].level must be 1, 2, or 3 (H1–H3).")
    return level


def _require_text(
    value: Any,
    index: int,
    *,
    allow_empty: bool,
    label: str | None = None,
) -> str:
    where = label or f"blocks[{index}].text"
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise BlockError(f"{where} must be a string.")
    if isinstance(value, float) and not value.is_integer():
        text = str(value)
    elif isinstance(value, float):
        text = str(int(value))
    elif isinstance(value, int):
        text = str(value)
    else:
        text = value
    if "\x00" in text or "\r" in text:
        raise BlockError(f"{where} must not contain NUL or carriage-return characters.")
    text = text.replace("\u2028", "\n").replace("\u2029", "\n")
    if not allow_empty and not text.strip():
        raise BlockError(f"{where} must not be empty.")
    return text


def _cell_paragraph_indexes(table_element: dict[str, Any]) -> list[list[int]]:
    table = table_element.get("table") or {}
    indexes: list[list[int]] = []
    for row in table.get("tableRows") or []:
        row_indexes: list[int] = []
        for cell in row.get("tableCells") or []:
            start = _first_paragraph_start(cell)
            if start is None:
                raise BlockError("Table cell has no paragraph to write into.")
            row_indexes.append(start)
        indexes.append(row_indexes)
    if not indexes:
        raise BlockError("Inserted table has no rows.")
    return indexes


def _first_paragraph_start(cell: dict[str, Any]) -> int | None:
    for element in cell.get("content") or []:
        if "paragraph" in element and isinstance(element.get("startIndex"), int):
            return element["startIndex"]
    return None


def _outline_from_body(document: dict[str, Any]) -> list[dict[str, Any]]:
    outline: list[dict[str, Any]] = []
    list_buffer: dict[str, Any] | None = None

    def flush_list() -> None:
        nonlocal list_buffer
        if list_buffer is not None:
            outline.append(list_buffer)
            list_buffer = None

    for element in (document.get("body") or {}).get("content") or []:
        if "paragraph" in element:
            paragraph = element["paragraph"]
            text = _paragraph_plain_text(paragraph)
            bullet = paragraph.get("bullet")
            if isinstance(bullet, dict) and bullet.get("listId"):
                kind = _list_kind(
                    document,
                    str(bullet["listId"]),
                    int(bullet.get("nestingLevel") or 0),
                )
                if list_buffer is None or list_buffer["type"] != kind:
                    flush_list()
                    list_buffer = {"type": kind, "items": []}
                if text:
                    list_buffer["items"].append(text)
                continue
            flush_list()
            if not text and not outline:
                # Leading empty paragraph in an otherwise empty doc.
                continue
            named = (paragraph.get("paragraphStyle") or {}).get("namedStyleType") or ""
            if named in HEADING_STYLES.values() and text:
                level = int(named.rsplit("_", 1)[1])
                outline.append({"type": "heading", "level": level, "text": text})
            elif text or outline:
                if text:
                    outline.append({"type": "paragraph", "text": text})
            continue
        if "table" in element:
            flush_list()
            outline.append(
                {
                    "type": "table",
                    "rows": _table_rows_text(element["table"]),
                }
            )
            continue
    flush_list()
    return outline


def _paragraph_plain_text(paragraph: dict[str, Any]) -> str:
    parts: list[str] = []
    for element in paragraph.get("elements") or []:
        content = (element.get("textRun") or {}).get("content")
        if isinstance(content, str):
            parts.append(content)
    return "".join(parts).strip("\n")


def _table_rows_text(table: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.get("tableRows") or []:
        cells: list[str] = []
        for cell in row.get("tableCells") or []:
            parts: list[str] = []
            for element in cell.get("content") or []:
                if "paragraph" in element:
                    text = _paragraph_plain_text(element["paragraph"])
                    if text:
                        parts.append(text)
            cells.append("\n".join(parts))
        rows.append(cells)
    return rows


def _list_kind(document: dict[str, Any], list_id: str, nesting_level: int) -> str:
    lists = document.get("lists") or {}
    levels = (
        ((lists.get(list_id) or {}).get("listProperties") or {}).get("nestingLevels")
        or []
    )
    glyph = ""
    if 0 <= nesting_level < len(levels):
        glyph = str(levels[nesting_level].get("glyphType") or "")
    numbered = (
        "DECIMAL",
        "ZERO_DECIMAL",
        "ALPHA",
        "UPPER_ALPHA",
        "ROMAN",
        "UPPER_ROMAN",
    )
    if glyph.startswith(numbered):
        return "numbered"
    return "bullets"
