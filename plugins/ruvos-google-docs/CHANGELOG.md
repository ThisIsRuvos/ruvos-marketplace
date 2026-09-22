# Changelog

## 0.5.1

- Fail closed on a horizontal rule. The Google Docs API cannot insert one: `insertHorizontalRule` is not a `documents.batchUpdate` field (the published Request schema has `insertPageBreak` and no `insertHorizontalRule`; `HorizontalRule` is only a paragraph element on `documents.get`). An unknown name is HTTP 400, the same class of failure as `insertTableOfContents`.
- `{type: "horizontal_rule"}` and aliases `hr`, `horizontal-rule`, and `insert_horizontal_rule` raise that error and do not call the Docs API. `insertHorizontalRule` is not on the allowed batch keys.
- No line of underscores, no table border, and no Apps Script. No new OAuth scope. No re-consent.
- An API-inserted rule cannot be soft-proved. Write the paragraphs with MCP, then **Insert → Horizontal line** in the Doc UI.
- `get_doc` can still read a horizontal rule that was added in the Doc UI. Page breaks and the fail-closed TOC are unchanged.

## 0.5.0

- `create_doc` and `replace_body` accept `{type: "page_break"}` (aliases `pagebreak`, `page-break`, `insert_page_break`). The compiler emits `insertPageBreak`.
- `insertPageBreak` was already an allowed `documents.batchUpdate` key. No new OAuth scope. No re-consent. No Apps Script.
- A page break is two UTF-16 units (the break and the newline the Docs API inserts after it). Content in the blocks before and after it stays on either side.
- `get_doc` outlines a page break already in the body as `{type: "page_break"}`. Confirm the new page in the Doc UI.

## 0.4.1

- Fail closed on a native table of contents. The Google Docs API cannot insert one: `insertTableOfContents` is not a `documents.batchUpdate` field and returns HTTP 400.
- `{type: "toc"}` and `insert_toc` raise that error and do not call the Docs API. `insertTableOfContents` is not allowlisted.
- Soft-prove is headings via MCP, then **Insert → Table of contents** in the Doc UI. No synthetic TOC. No Apps Script.
- `get_doc` can still read a TOC that was added in the Doc UI.

## 0.4.0

- Attempted a `toc` block and `insert_toc` via `insertTableOfContents`. Soft-prove failed: Docs API HTTP 400 `Unknown name "insertTableOfContents"`. Superseded by 0.4.1.

## 0.3.0

- `create_doc` and `replace_body` accept optional `color` (foreground) and `backgroundColor` or `highlight` (character highlight) on headings, paragraphs, list items, and table cells. `spans` highlight one phrase inside a heading, paragraph, or list item. The compiler emits `updateTextStyle` with `rgbColor` floats from 0 to 1. Callers do not hand-write UTF-16 indexes.
- `updateTextStyle` was already allowlisted (header bold). No new batch key. No OAuth scope change. No re-consent.

## 0.2.0

- `insert_image` uploads PNG, JPEG, or GIF bytes with `drive.file` and inserts them in place (`insertInlineImage`). A hosted image URL is not accepted. Full `drive` is not requested.
- OAuth scope `https://www.googleapis.com/auth/drive.file` is requested with the existing Docs scopes on the same Google OAuth client. Disconnect and reconnect Ruvos Google Docs so consent includes it.
- Limits: 5 MiB, 25 megapixels, optional size in points. The staging Drive file is deleted in a `finally` path, including when `insertInlineImage` fails. Anyone-with-the-link fetch URLs are redacted from logs. A Workspace block on that share fails closed. Non-PHI images only until the same Docs BAA gate as Doc text.

## 0.1.1

- `set_header_footer`: default and first-page header/footer text on an existing Doc. Optional `page_number` right-aligns the default segment. A live page-number field is kept when the Doc already has one; the Docs API cannot insert a new AutoText `PAGE_NUMBER`.
- `batch_update_doc` allows `createHeader` and `createFooter`, including `insertText` and `updateParagraphStyle` on a header or footer segment.
- `get_doc` outline stays body-only and omits headers and footers.

## 0.1.0

- Create and edit Google Docs in place via Docs API `documents.batchUpdate`.
- Tools: `create_doc`, `get_doc`, `replace_body`, `batch_update_doc` (H1–H3, bullets, numbered lists, tables, full body replace, follow-up edit on the same documentId).
- OAuth via the Ruvos Authorization Server (DCR). Same pattern as Ruvos Google Chat. No Google client secret in Cursor.
- Scopes: `documents` plus `openid` and `userinfo.email`. No Drive, Gmail, or Calendar scopes. Add `drive.file` only if a parent folder is required later.
- Explicit ban: the deliverable is the Google Doc. Not Word/.docx, not HTML, not a raw markdown upload.
