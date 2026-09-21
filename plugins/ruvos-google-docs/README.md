# Ruvos Google Docs

Cursor plugin that creates and edits **Google Docs in place** via the Docs API (`documents.batchUpdate`).

The deliverable is the Google Doc (URL + `documentId`). **Not** an HTML handoff, **not** Word / `.docx`, **not** a raw markdown upload. The featured Google Drive connector is not used: `create_file` can mint an empty Doc and cannot style or replace the body.

## Install

1. Admin: Dashboard → Plugins → Team Marketplaces → Ruvos Marketplace (import the marketplace repo if it is not already listed).
2. Marketplace Access: All Members. Auto Refresh on.
3. Customize → install **Ruvos Google Docs**.

## Connect

1. Open the plugin and click **Connect**.
2. Cursor performs DCR against the Ruvos Authorization Server. There is **no Google client secret** to paste into Cursor.
3. Sign in as a **Frans Workspace user** (fine for EA tooling) and approve the scopes below. The Doc must live in that Workspace, not in a personal Gmail account.
4. Re-consent (disconnect and connect again) after a scope change.

Tokens stay in the MCP connector vault (the server’s encrypted token store). Never paste them into Chat, issues, or logs.

Connect stays red until ops deploys `services/google-docs-mcp/` and maps `https://google-docs-mcp.ruvos.com` (see that service README). This plugin does not extend the featured Drive MCP, and it does not add Docs scopes onto the Google Chat Connect consent.

## MCP endpoint

`https://google-docs-mcp.ruvos.com/mcp`

## OAuth scopes

Requested on the Ruvos Authorization Server (the existing Ruvos Google OAuth client — not a second client):

| Scope | Why |
|-------|-----|
| `openid` | Subject on the user token (same as Google Chat) |
| `https://www.googleapis.com/auth/userinfo.email` | User identity on the token |
| `https://www.googleapis.com/auth/documents` | Create and edit in place: `documents.create`, `documents.get`, `documents.batchUpdate` |
| `https://www.googleapis.com/auth/drive.file` | Upload PNG, JPEG, or GIF bytes for `insert_image`, then insert them with `insertInlineImage`. File create for that staging image only. |

This Connect requests `drive.file` together with the Docs scopes above. It does **not** request full `drive`, Gmail, or Calendar. A hosted image URL is not an input. There is no export and no re-upload of the Doc.

Disconnect and connect again after this scope change so consent includes `https://www.googleapis.com/auth/drive.file`. Do not add full `drive`. The shared Google OAuth client also serves Chat; those Chat scopes stay on the Chat Connect flow and are not requested here.

## Tools

| Tool | What it does |
|------|----------------|
| `create_doc` | Create a Google Doc. Optional `blocks` write the first body in the same call, including `color`, `backgroundColor` (alias `highlight`), `spans`, and one `{type: "toc"}` block. Returns `documentId` and `https://docs.google.com/document/d/<id>/edit`. |
| `replace_body` | Replace (`mode=replace`, default) or append (`mode=append`) the body in place. Blocks take the same `color`, `highlight`, and `spans` fields, and one `{type: "toc"}` block. |
| `batch_update_doc` | Raw `documents.batchUpdate` requests for a follow-up edit on the **same** `documentId` (for example `replaceAllText`). `insertText` and `updateParagraphStyle` may target a header or footer `segmentId`. `createHeader` and `createFooter` are allowed. `updateTextStyle` is already allowlisted (foreground and background color). `insertTableOfContents` is allowlisted. |
| `get_doc` | Read title, URL, plain text, and an outline back from that Doc. The outline is the body only. Headers and footers are omitted. When the body has a TOC, the outline includes `{type: "toc", entries: [...]}`. |
| `insert_toc` | Insert a table of contents on an existing Doc. Omit `index` to insert at the start of the body. Entries come from H1–H3 styles already in the Doc. |
| `set_header_footer` | Set the default and optional first-page header and/or footer on an existing Doc. Body and tables are left unchanged. |
| `insert_image` | Upload PNG, JPEG, or GIF bytes with `drive.file` and insert them inline with `insertInlineImage`. A hosted image URL is not an input. |

`blocks` is a list of objects:

- `{"type": "heading", "level": 1, "text": "..."}` — level `1`, `2`, or `3` only
- `{"type": "paragraph", "text": "..."}`
- `{"type": "bullets", "items": ["...", "..."]}` (alias `bullet_list`)
- `{"type": "numbered", "items": ["...", "..."]}` (alias `numbered_list`)
- `{"type": "table", "header": true, "rows": [["H1", "H2"], ["a", "b"]]}`
- `{"type": "toc"}` — one table of contents. Other blocks are written first, then the TOC is inserted at that position. Entries come from H1–H3 styles already in the Doc.

`color`, `backgroundColor`, and `spans` are optional on a heading, paragraph, or list item. A table cell takes `color` and `backgroundColor` on the cell.

- `color` is foreground.
- `backgroundColor` is a character highlight. Alias `highlight`.
- `spans` styles the first matching phrase inside that heading, paragraph, or list item. Each span is `{"text": "<phrase>", "color": "...", "backgroundColor": "..."}` (or `highlight`). Block color is applied first so the phrase span overlays it.
- A list item or table cell may be a string, or an object `{"text": "..."}` with the same color fields. Header bold stays when a header cell is highlighted.

Values are `#RGB`, `#RRGGBB`, or RGB channel floats from 0 to 1 (`red`, `green`, `blue`). Hex is converted as channel / 255. Named colors are rejected. Integer channels from 0 to 255 are rejected.

The compiler emits `updateTextStyle` with `foregroundColor` / `backgroundColor` `rgbColor`. Ranges are UTF-16 code units, `endIndex` is exclusive, and the trailing newline is left unstyled. Color does not change OAuth scopes. No re-consent.

Do not pass `type: html`, `docx`, `word`, or `markdown`. Those are rejected. Markdown characters inside a paragraph are stored as literal text; they are not a file upload and they are not rendered as a Doc export.

`set_header_footer` takes `document_id` plus optional `header` and `footer` objects. Each object accepts:

- `default` — text shown on every page, or on pages after the first when `first_page` is set
- `first_page` — different first-page text. Setting this turns on `useFirstPageHeaderFooter` for both the header and the footer
- `page_number` — `true` right-aligns the default segment

Example: header `{"default": "Ruvos — Confidential"}` and footer `{"page_number": true}`.

The Docs API cannot insert a live AutoText PAGE_NUMBER field. If one is already in the segment it is kept and `pageNumber.liveField` is true. Otherwise the segment is created and `pageNumber.liveField` is false. Add the number in the Doc UI with Insert > Page numbers. `get_doc`'s outline stays body-only and does not list headers or footers.

`insert_image` takes `document_id` plus the image bytes as `image_base64`, or `image_path` on the MCP host. Formats are PNG, JPEG, and GIF. Optional `width_pt` and `height_pt` are capped at 2000 points. The file must be at most 5 MiB and 25 megapixels. The server uploads those bytes with `drive.file`, inserts them with `insertInlineImage`, and deletes the staging Drive file afterward, including when the insert fails. The temporary anyone-with-the-link fetch URL is redacted from tool errors. If Workspace policy blocks anyone-with-the-link sharing, the insert fails closed and the staging file is still deleted when Drive allows it. Full `drive` is not requested.

## Workspace BAA

Google Docs and Drive count as Workspace-covered only when **both** are true:

- Ruvos has an active Google Workspace BAA, and
- the Doc lives in that Workspace (Workspace account, not personal Gmail).

Confirm the BAA covers Docs before an NFRHC assessment, or any other PHI-adjacent assessment, is written into a native Doc. The same gate covers images. If the BAA is absent or unclear, keep those assessments in the GitLab wiki or in non-PHI Drive folders until James or Frans confirms.

## Soft-prove (Annie, after this service is deployed)

Prove on a **non-PHI sample Doc first**. NFRHC comes only after the BAA check above. Confirm both writes in the Docs UI. The artifact is the Doc URL, not an exported file.

### 1. Non-PHI sample

1. `create_doc` with title `Docs MCP sample (non-PHI)`, signed in as a Frans Workspace user.
2. `replace_body` on that `documentId`:

```json
[
  {"type": "heading", "level": 1, "text": "Docs MCP sample"},
  {"type": "heading", "level": 2, "text": "Scope"},
  {"type": "paragraph", "text": "Synthetic note. Status: DRAFT."},
  {"type": "heading", "level": 3, "text": "Checks"},
  {"type": "bullets", "items": ["Heading sticks", "List sticks"]},
  {"type": "numbered", "items": ["Create", "Edit in place"]},
  {"type": "table", "header": true, "rows": [["Check", "Result"], ["Follow-up edit", "Pending"]]}
]
```

3. Follow-up edit on the **same** `documentId` via `batch_update_doc`:

```json
[
  {
    "replaceAllText": {
      "containsText": {"text": "DRAFT", "matchCase": true},
      "replaceText": "FINAL"
    }
  }
]
```

4. Refresh the Doc in the browser. Headings, lists, and the table from step 2 are there, and `DRAFT` now reads `FINAL`.
5. `get_doc` on the same id returns that text. The outline is the body only. It does not include headers or footers.
6. `set_header_footer` on the same `documentId`: header `{"default": "Ruvos — Confidential"}` and footer `{"page_number": true}`. Refresh the Doc. The header reads `Ruvos — Confidential`. A new footer reports `pageNumber.liveField` false because the Docs API cannot insert a live AutoText PAGE_NUMBER. Add the page number in the Doc UI (Insert > Page numbers) if it is missing. Body and tables from steps 2–3 stay as they were.

7. After re-consent (so `drive.file` is on the token), `insert_image` on the same `documentId` with a local non-PHI PNG (`image_base64` or `image_path`). Refresh the Doc. The image is visible inline. Do not use a hosted image URL. NFRHC and other PHI-adjacent images stay out of this step.

If step 3 does not show up in the Doc UI, or the image from step 7 is missing, the soft-prove failed. Hand back the Doc URL only after the UI shows both writes, the header, and the inline image.

### 1b. Text color and one highlighted phrase

Non-PHI. OAuth scopes are unchanged. No re-consent. Run this after Cloud Run has the color compiler.

`replace_body` on the sample `documentId` (or a new non-PHI Doc):

```json
[
  {"type": "heading", "level": 1, "text": "Color sample", "color": "#122949"},
  {
    "type": "paragraph",
    "text": "Body stays black. This phrase is highlighted.",
    "color": "#000000",
    "spans": [
      {"text": "This phrase is highlighted", "highlight": "#FFF3B0"}
    ]
  }
]
```

Refresh the Doc. The heading is navy `#122949`. The body is black `#000000`. The words `This phrase is highlighted` have a `#FFF3B0` character highlight. `get_doc` returns those words. Color is confirmed in the Doc.

### 1c. Table of contents

Non-PHI. OAuth scopes are unchanged. No re-consent. No Drive change. Run this after Cloud Run has the TOC insert.

`replace_body` on the sample `documentId` (or a new non-PHI Doc) with an H1, an H2, and one `toc` block:

```json
[
  {"type": "heading", "level": 1, "text": "TOC sample"},
  {"type": "heading", "level": 2, "text": "Scope"},
  {"type": "toc"}
]
```

Other blocks are written first. The TOC is inserted at the `toc` block's position so those heading styles supply the entries.

On a Doc that already has headings, `insert_toc` with that `document_id` does the same. Omit `index` to insert at the start of the body.

Refresh the Doc. The TOC lists the H1 and the H2. `get_doc` outline includes `{type: "toc", entries: [...]}`. A follow-up `replace_body` rebuilds the body, including the previous TOC.

Page break, horizontal rule, and heading bookmarks stay out of scope. `insertPageBreak` remains a raw `batch_update_doc` key only.

### 2. NFRHC

After James or Frans confirms the Workspace BAA covers Docs, repeat the same create / `replace_body` / follow-up edit with the NFRHC assessment in a Workspace Doc. Images in that Doc use the same BAA gate. Until that confirmation, leave NFRHC in the GitLab wiki or a non-PHI Drive folder.

## Server source

Implementation: [`services/google-docs-mcp/`](../../services/google-docs-mcp/)
