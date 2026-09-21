# Changelog

## 0.1.1

- `set_header_footer`: default and optional first-page header and footer text on an existing Doc, plus an optional page-number slot on the default segment.
- `get_doc` outline stays body-only. Headers and footers are omitted.
- `batch_update_doc` may target a header or footer segment (`createHeader`, `createFooter`, `insertText`, `updateParagraphStyle`).
- The Docs API cannot insert a live AutoText PAGE_NUMBER. A new footer or header reports `pageNumber.liveField` false unless a live field is already in that segment. Add page numbers in the Doc UI (Insert > Page numbers) when the field is not live.

## 0.1.0

- Create and edit Google Docs in place via Docs API `documents.batchUpdate`.
- Tools: `create_doc`, `get_doc`, `replace_body`, `batch_update_doc` (H1–H3, bullets, numbered lists, tables, full body replace, follow-up edit on the same documentId).
- OAuth via the Ruvos Authorization Server (DCR). Same pattern as Ruvos Google Chat. No Google client secret in Cursor.
- Scopes: `documents` plus `openid` and `userinfo.email`. No Drive, Gmail, or Calendar scopes. Add `drive.file` only if a parent folder is required later.
- Explicit ban: the deliverable is the Google Doc. Not Word/.docx, not HTML, not a raw markdown upload.
