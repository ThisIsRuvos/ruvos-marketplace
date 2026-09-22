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
4. Re-consent after a scope change: disconnect **Ruvos Google Docs**, then Connect again and approve the new consent screen. Existing tokens do not pick up a newly added scope. Chat Connect is a separate consent and stays as it is.

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
| `https://www.googleapis.com/auth/drive.file` | Upload an image this app creates, then insert it into the Doc. Not full Drive. |

This Connect does **not** request full `drive`, Gmail, or Calendar. `documents.create` already creates the Doc, and text edits go through `batchUpdate` on that Doc. There is no export and no re-upload of HTML, Word, or markdown.

`drive.file` is only for the inline-image helper. The caller passes image bytes (or a file on the MCP host). A hosted public image URL is not accepted. Do not add full `drive`. The shared Google OAuth client also serves Chat; those Chat scopes stay on the Chat Connect flow and are not requested here.

### Re-consent after `drive.file`

Tokens minted before this scope was added cannot upload images.

1. In Cursor, disconnect **Ruvos Google Docs**.
2. Connect again. Sign in as a Frans Workspace user.
3. Approve the consent screen. It now includes `https://www.googleapis.com/auth/drive.file` plus the existing Docs scopes (`documents`, `openid`, `userinfo.email`) on the **same** Google OAuth client.
4. Confirm an image insert on a non-PHI Doc (soft-prove below). Text tools keep working on that new token.

Ops add `https://www.googleapis.com/auth/drive.file` on that existing OAuth client's consent screen and enable `drive.googleapis.com` before users reconnect. Do not create a second Google client and do not add `https://www.googleapis.com/auth/drive`.

## Tools

| Tool | What it does |
|------|----------------|
| `create_doc` | Create a Google Doc. Optional `blocks` write the first body in the same call. Returns `documentId` and `https://docs.google.com/document/d/<id>/edit`. |
| `replace_body` | Replace (`mode=replace`, default) or append (`mode=append`) the body in place. Optional text color and highlight. `{type: "page_break"}` inserts a page break. `{type: "toc"}` fails closed. |
| `insert_toc` | Fails closed. The Docs API cannot insert a native table of contents. |
| `set_header_footer` | Set default and optional first-page header/footer text on an existing Doc. Optional `page_number` right-aligns that default segment. |
| `batch_update_doc` | Raw `documents.batchUpdate` requests for a follow-up edit on the **same** `documentId` (for example `replaceAllText`, `updateTextStyle`, `insertPageBreak`, `createHeader`, `createFooter`). `insertTableOfContents` is rejected. `insertText` and `updateParagraphStyle` may use a header or footer `segmentId`. `updateTextStyle` and `insertInlineImage` stay on the allowed set. |
| `get_doc` | Read title, URL, plain text, and a **body** outline. Headers and footers are omitted (`outlineScope` is `body`). A page break in the body is `{type: "page_break"}`. A TOC added in the Doc UI is `{type: "toc", entries: [...]}`. |
| `insert_image` | Upload PNG, JPEG, or GIF bytes with `drive.file`, then `insertInlineImage` on that `documentId`. Optional `index`, `width_pt`, and `height_pt`. |

`blocks` is a list of objects:

- `{"type": "heading", "level": 1, "text": "..."}` — level `1`, `2`, or `3` only
- `{"type": "paragraph", "text": "..."}`
- `{"type": "bullets", "items": ["...", "..."]}` (alias `bullet_list`)
- `{"type": "numbered", "items": ["...", "..."]}` (alias `numbered_list`)
- `{"type": "table", "header": true, "rows": [["H1", "H2"], ["a", "b"]]}`
- `{"type": "page_break"}` — `insertPageBreak` between the surrounding blocks. Aliases: `pagebreak`, `page-break`, `insert_page_break`. It does not take text.
- `{"type": "toc"}` — rejected. The Google Docs API cannot insert a native TOC. Alias `table_of_contents` is rejected the same way.

Optional on a heading, paragraph, list item, or table cell:

- `color` — foreground text
- `backgroundColor` — character highlight (`highlight` is the same field; pass one of them)
- `spans` — `[{"text": "this phrase", "backgroundColor": "#FFF3B0"}]` on a heading, paragraph, or list item. The first match is styled. Table cells do not take `spans`.

A list item or table cell can be a string, or `{"text": "...", "color": "...", "backgroundColor": "..."}`.

Color values are `#RGB`, `#RRGGBB`, or RGB floats from 0 to 1 (`[red, green, blue]` or `{"red": 0.0, "green": 0.0, "blue": 0.0}`). Docs `rgbColor` uses that 0–1 range, not 0–255. Hex is converted as `channel / 255`. Named colors such as `navy` are rejected. There is no brand palette.

The compiler emits `updateTextStyle`. You do not hand-write indexes for `create_doc` or `replace_body`. When you call `batch_update_doc` with a raw `updateTextStyle`, `startIndex` and `endIndex` are UTF-16 code units and `endIndex` is exclusive. `fields` is `foregroundColor`, `backgroundColor`, or both.

`get_doc` returns the words. It does not return colors. Confirm color in the Doc UI.

Do not pass `type: html`, `docx`, `word`, or `markdown`. Those are rejected. Markdown characters inside a paragraph are stored as literal text; they are not a file upload and they are not rendered as a Doc export.

`set_header_footer` takes `header` and/or `footer`:

- `default` — text for every page, or for pages after the first when `first_page` is set
- `first_page` — text for page 1. This turns on different first-page header/footer for both the header and the footer
- `page_number` — `true` right-aligns the default segment

`get_doc` does not echo that header or footer back. Confirm them in the Doc UI. Headers and footers use the `documents` scope. They do not use `drive.file`.

### Table of contents

The Google Docs API cannot insert a native TOC. `documents.batchUpdate` has no `insertTableOfContents` field. Sending that name returns HTTP 400 (`Unknown name "insertTableOfContents"`).

`{"type": "toc"}` and `insert_toc` fail closed with that limitation. They do not call the Docs API. `batch_update_doc` rejects `insertTableOfContents` the same way. There is no synthetic TOC (no heading list standing in for one) and no Apps Script.

Write the headings with `create_doc` or `replace_body`. Then in the Doc, use **Insert → Table of contents**. No new OAuth scope. No re-consent.

If a TOC is already in the body because someone used the Doc UI, `get_doc` can return `{type: "toc", entries: [...]}` from that element. That read does not create the TOC. Confirm the list in the Doc UI.

### `insert_image`

Pass **one** of:

- `image_base64` — standard base64, or a `data:image/png;base64,...` URL. This is the path for remote Connect: read the local file in the agent and send the bytes.
- `image_path` — a `.png`, `.jpg`, `.jpeg`, or `.gif` file on the **MCP server**. Use this when `ruvos-google-docs-mcp` is running locally and the file is on that host. A remote Cloud Run server cannot see a path on your laptop.

Optional:

- `index` — UTF-16 body location. Omit it to insert at the end of the body (just before the final newline).
- `width_pt` / `height_pt` — display size in points. Omit both to keep the image's native size. Each value must be greater than 0 and at most 2000.

The helper does not take a hosted image URL.

What happens:

1. Bytes are checked (format, size, pixel count).
2. They are uploaded with `drive.file` (multipart, no parent folder, not full `drive`).
3. The staging file is shared as anyone-with-the-link so the Docs API can fetch it. The Docs API does not send the user's token when it fetches an image, and it does not accept raw bytes.
4. `insertInlineImage` writes the image into the Doc. Docs stores its own copy.
5. The staging Drive file is deleted in a `finally` path, including when `insertInlineImage` fails. If delete fails, the tool response includes `stagingFileId` so you can remove it. The anyone-with-the-link URL is not logged. A Drive file id in a debug line is fine.

That link share is brief and is an implementation detail of the Docs fetch. It is not a caller-supplied public URL. If Workspace policy blocks anyone-with-the-link, the insert fails closed (the image is not written) and the staging file is still deleted when Drive allows the delete.

### Image limits

| Limit | Value |
|-------|--------|
| Formats | PNG, JPEG, GIF |
| Rejected | WebP, SVG, BMP, PDF, and anything else |
| Max decoded size | 5 MiB (5,242,880 bytes), the Drive multipart upload cap this helper uses |
| Max pixels | 25,000,000 (Docs API limit) |
| Max `width_pt` / `height_pt` | 2000 points each |
| Docs API ceiling | 50 MB, which this helper does not reach |

## Workspace BAA

Google Docs and Drive count as Workspace-covered only when **both** are true:

- Ruvos has an active Google Workspace BAA, and
- the Doc lives in that Workspace (Workspace account, not personal Gmail).

Confirm the BAA covers Docs before an NFRHC assessment, any other PHI-adjacent assessment, or a PHI-adjacent image is written into a native Doc. Images use that same gate as Doc text. If the BAA is absent or unclear, keep those assessments and images in the GitLab wiki or in non-PHI Drive folders until James or Frans confirms.

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
5. `get_doc` on the same id returns that text. The outline is the body. It omits headers and footers.

6. On the **same** `documentId`, `set_header_footer`:

```json
{
  "header": {"default": "Ruvos — Confidential"},
  "footer": {"page_number": true}
}
```

7. Refresh the Doc. The header reads `Ruvos — Confidential`. Headings, lists, the table, and `FINAL` from the earlier steps are still in the body.
8. `get_doc` on the same id still returns that body text. `outlineScope` is `body`. The header and footer are absent from the outline.
9. Footer page number: the call creates the footer and right-aligns it. `pageNumber.liveField` is false on a new footer. `documents.batchUpdate` can read an existing AutoText `PAGE_NUMBER` and cannot insert one. Click the footer and use Insert → Page numbers, then confirm the number in the UI. Leave the body and the table as they are.

If step 3 or the header in step 7 does not show up in the Doc UI, the soft-prove failed. Hand back the Doc URL only after the UI shows the body writes and the header text.

To set a different first page, pass `first_page` as well as `default` (non-PHI text only). Example: `"first_page": "Cover"` and `"default": "Ruvos — Confidential"`.

### 1b. Non-PHI text color

Use a synthetic Doc. No patient data and no PHI. `get_doc` returns the words. Confirm color in the Doc UI.

1. `create_doc` with title `Docs MCP color sample (non-PHI)`.
2. `replace_body` on that `documentId`:

```json
[
  {
    "type": "heading",
    "level": 1,
    "text": "Docs MCP color sample",
    "color": "#122949"
  },
  {
    "type": "paragraph",
    "text": "Synthetic note. This phrase is highlighted. No patient data.",
    "color": "#000000",
    "spans": [
      {
        "text": "This phrase is highlighted",
        "backgroundColor": "#FFF3B0"
      }
    ]
  }
]
```

3. Refresh the Doc. The heading is navy (`#122949`). The body is black. The yellow highlight covers `This phrase is highlighted` and stops at the end of that phrase.
4. `get_doc` on the same id returns that text. It does not return `foregroundColor` or `backgroundColor`.

`#122949` is the sample navy. It is not a palette: any `#RRGGBB` or 0–1 RGB is valid. That hex converts to `{"red": 0.07058823529411765, "green": 0.1607843137254902, "blue": 0.28627450980392155}`.

If the heading, the black body, or the single highlighted phrase is missing in the Doc UI, the color soft-prove failed.

### 1c. Non-PHI table of contents

Use a synthetic Doc. No patient data and no PHI. MCP writes the headings. The table of contents is **Insert → Table of contents** in the Doc UI. MCP does not insert it.

1. `create_doc` with title `Docs MCP TOC sample (non-PHI)`, or `replace_body` on a new Doc:

```json
[
  {"type": "heading", "level": 1, "text": "Docs MCP sample"},
  {"type": "heading", "level": 2, "text": "Scope"},
  {"type": "paragraph", "text": "Synthetic note. No patient data."}
]
```

Do not pass `{"type": "toc"}`. That call fails closed and does not write the body.

2. Refresh the Doc. The H1 and H2 are there.
3. In the Doc UI, click **Insert → Table of contents**. Refresh again. The TOC lists `Docs MCP sample` and `Scope`.
4. `get_doc` on the same id returns those headings. After the UI insert, the outline may include `{"type": "toc", "entries": ["Docs MCP sample", "Scope"]}`. `outlineScope` stays `body`. The UI is the check that matters.

`insert_toc` on that `documentId` fails closed with the same API limitation. It does not call `documents.batchUpdate`. A raw `insertTableOfContents` request on `batch_update_doc` fails closed the same way.

If the headings are missing, the soft-prove failed. If the TOC is missing after Insert → Table of contents, the UI step failed. Do not invent a TOC out of normal paragraphs, and do not use Apps Script.

### 1d. Non-PHI page break

Use a synthetic Doc. No patient data and no PHI. MCP writes content before the break, the break, and content after it. The check is the Doc UI: the second note is on a new page.

1. `create_doc` with title `Docs MCP page break sample (non-PHI)`, passing `blocks`, or `replace_body` on a new Doc:

```json
[
  {"type": "heading", "level": 1, "text": "Docs MCP page break sample"},
  {"type": "paragraph", "text": "Synthetic note on page 1. No patient data."},
  {"type": "page_break"},
  {"type": "paragraph", "text": "Synthetic note on page 2. No patient data."}
]
```

`page_break` does not take `text`. Aliases `pagebreak`, `page-break`, and `insert_page_break` compile to the same `insertPageBreak` request. No new OAuth scope and no re-consent. No Apps Script.

2. Refresh the Doc. Page 1 shows the heading and `Synthetic note on page 1. No patient data.` Page 2 shows `Synthetic note on page 2. No patient data.` The page break is the gap between those pages.
3. `get_doc` on the same id returns both notes. The body outline includes `{"type": "page_break"}` between them. `outlineScope` stays `body`. The UI is the check that matters.

If both notes sit on one page, the page-break soft-prove failed. Do not pass `{"type": "toc"}` on this Doc.

### 2. Non-PHI inline image (local PNG)

Do this only after the `drive.file` re-consent above. The image must be a synthetic diagram with no patient data and no PHI. Do not use an NFRHC diagram or any other PHI-adjacent image here. Those wait on the same BAA confirmation as Doc text in section 3.

1. Start from the sample Doc in section 1, or `create_doc` with title `Docs MCP image sample (non-PHI)`.
2. On that `documentId`, call `insert_image` with the local PNG as `image_base64` (remote Connect) or `image_path` (MCP running on the same machine as the file). Example arguments:

```json
{
  "document_id": "<id from create_doc>",
  "image_base64": "<base64 of the local PNG>",
  "width_pt": 360
}
```

3. Refresh the Doc in the browser. The PNG is visible inline.
4. The tool result says the staging Drive file was deleted (`stagingFileDeleted: true`). If it instead returns `stagingFileId`, delete that file in Drive.

A hosted URL is not a passing prove. Hand back the Doc URL only after the UI shows the image.

### 3. NFRHC

After James or Frans confirms the Workspace BAA covers Docs, repeat the same create / `replace_body` / follow-up edit with the NFRHC assessment in a Workspace Doc. That same confirmation is required before an NFRHC or other PHI-adjacent image is inserted. Until that confirmation, leave NFRHC text and images in the GitLab wiki or a non-PHI Drive folder.

## Out of scope / soft later

Not implemented as blocks or helpers:

- Live AutoText page numbers. `set_header_footer` still cannot insert a `PAGE_NUMBER` field. `page_number: true` right-aligns the default segment. Add the number in the Doc UI (Insert → Page numbers) when `pageNumber.liveField` is false.
- Horizontal rule.
- Heading bookmarks and internal links.

File those separately if they should become helpers.

## Server source

Implementation: [`services/google-docs-mcp/`](../../services/google-docs-mcp/)
