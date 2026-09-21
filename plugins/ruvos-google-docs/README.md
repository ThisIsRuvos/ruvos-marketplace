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

This Connect does **not** request Drive (`drive` or `drive.file`), Gmail, or Calendar. `documents.create` already creates the Doc, and edits go through `batchUpdate` on that Doc. There is no export and no re-upload.

`drive.file` (file create / parent only) is the scope to add later if a Doc must be placed in a specific Workspace folder. Do not add full `drive` for that. The shared Google OAuth client also serves Chat; those Chat scopes stay on the Chat Connect flow and are not requested here.

## Tools

| Tool | What it does |
|------|----------------|
| `create_doc` | Create a Google Doc. Optional `blocks` write the first body in the same call. Returns `documentId` and `https://docs.google.com/document/d/<id>/edit`. |
| `replace_body` | Replace (`mode=replace`, default) or append (`mode=append`) the body in place. |
| `batch_update_doc` | Raw `documents.batchUpdate` requests for a follow-up edit on the **same** `documentId` (for example `replaceAllText`). |
| `get_doc` | Read title, URL, plain text, and an outline back from that Doc. |

`blocks` is a list of objects:

- `{"type": "heading", "level": 1, "text": "..."}` — level `1`, `2`, or `3` only
- `{"type": "paragraph", "text": "..."}`
- `{"type": "bullets", "items": ["...", "..."]}` (alias `bullet_list`)
- `{"type": "numbered", "items": ["...", "..."]}` (alias `numbered_list`)
- `{"type": "table", "header": true, "rows": [["H1", "H2"], ["a", "b"]]}`

Do not pass `type: html`, `docx`, `word`, or `markdown`. Those are rejected. Markdown characters inside a paragraph are stored as literal text; they are not a file upload and they are not rendered as a Doc export.

## Workspace BAA

Google Docs and Drive count as Workspace-covered only when **both** are true:

- Ruvos has an active Google Workspace BAA, and
- the Doc lives in that Workspace (Workspace account, not personal Gmail).

Confirm the BAA covers Docs before an NFRHC assessment, or any other PHI-adjacent assessment, is written into a native Doc. If the BAA is absent or unclear, keep those assessments in the GitLab wiki or in non-PHI Drive folders until James or Frans confirms.

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
5. `get_doc` on the same id returns that text.

If step 3 does not show up in the Doc UI, the soft-prove failed. Hand back the Doc URL only after the UI shows both writes.

### 2. NFRHC

After James or Frans confirms the Workspace BAA covers Docs, repeat the same create / `replace_body` / follow-up edit with the NFRHC assessment in a Workspace Doc. Until that confirmation, leave NFRHC in the GitLab wiki or a non-PHI Drive folder.

## Server source

Implementation: [`services/google-docs-mcp/`](../../services/google-docs-mcp/)
