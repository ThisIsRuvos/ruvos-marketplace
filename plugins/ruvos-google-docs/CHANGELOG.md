# Changelog

## 0.4.0

- `create_doc` and `replace_body` accept one `{type: "toc"}` block. Other blocks are written first, then the TOC is inserted at that position so H1–H3 styles already in the Doc supply the entries.
- `insert_toc` does the same on an existing Doc. Omit `index` to insert at the start of the body.
- `batch_update_doc` allowlists `insertTableOfContents`.
- `get_doc` outline includes `{type: "toc", entries: [...]}` when the body has one.
- No new OAuth scopes. No Drive change. No re-consent.
- Page break, horizontal rule, and heading bookmarks stay out of scope. `insertPageBreak` remains a raw batch key only.

## 0.3.0

- `create_doc` and `replace_body` set text color and a character highlight without hand-written Docs indexes.
- `color` is foreground. `backgroundColor` (alias `highlight`) is a character highlight. `spans` styles the first matching phrase inside a heading, paragraph, or list item. Table cells take `color` / `backgroundColor` on the cell.
- Values are `#RGB`, `#RRGGBB`, or RGB channel floats from 0 to 1. Hex is converted as channel / 255. Named colors and 0–255 integer channels are rejected.
- The compiler emits `updateTextStyle` (`foregroundColor` / `backgroundColor` `rgbColor`). Ranges are UTF-16 code units, `endIndex` is exclusive, and the trailing newline is left unstyled. Block color is applied first so a phrase span overlays it.
- `updateTextStyle` stays on the `batch_update_doc` allowlist. No new request key. OAuth scopes are unchanged. No re-consent.

## 0.2.0

- `insert_image`: PNG, JPEG, or GIF bytes (`image_base64`, or `image_path` on the MCP host). Uploads with `drive.file` and inserts with `insertInlineImage`. A hosted image URL is not an input. Full `drive` is not requested.
- Scope `https://www.googleapis.com/auth/drive.file` is requested with the existing Docs scopes on the same Google OAuth client. Disconnect and connect again to re-consent.
- Limits: 5 MiB, 25 megapixels, optional `width_pt` / `height_pt` (max 2000 points).
- The staging Drive file is deleted after the insert, including when `insertInlineImage` fails. The temporary anyone-with-the-link URL is redacted from errors. If Workspace policy blocks that share, the insert fails closed and the staging file is still deleted when Drive allows it.
- Soft-prove images are non-PHI only. NFRHC and other PHI-adjacent images use the same Workspace BAA gate as Doc text.

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
