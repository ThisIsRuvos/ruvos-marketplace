# Ruvos Google Docs MCP (middle layer)

Ruvos-owned **remote HTTP MCP** so Cursor can create and edit Google Docs **in place** through our OAuth Authorization Server (DCR + PKCE). The server calls the Docs API (`documents.create`, `documents.get`, `documents.batchUpdate`) with the signed-in user's token.

```
Cursor ──DCR/OAuth──► ruvos-google-docs-mcp (FastMCP OAuthProxy)
                           │
                           ├──► Google OAuth (existing Ruvos client)
                           └──► docs.googleapis.com (user Bearer, per request)
```

The Cursor plugin does **not** point at a featured Google Drive MCP. Users never paste a Google client secret into Cursor. This server does not upload HTML, Word/`.docx`, or markdown.

## Why this is a sibling of Google Chat

`services/google-chat-mcp` is the Ruvos OAuth middle layer (GoogleProvider, DCR, exact-match Cursor redirects, encrypted tokens, revoke-on-disconnect, Memorystore TLS). Docs reuses that pattern.

Docs scopes are **not** added to the Chat Connect consent. `https://www.googleapis.com/auth/documents` is all-docs write; Chat users should not be asked for it. Ops reuse the **same Google OAuth client** (add scopes + one redirect URI). Do not create a second Google client.

## Tools

| Tool | Docs API | Description |
|------|----------|-------------|
| `create_doc` | `documents.create`, then `batchUpdate` if `blocks` is set | Create a Doc; return `documentId` + URL |
| `get_doc` | `documents.get` | Title, URL, plain text, outline |
| `replace_body` | `documents.batchUpdate` | Replace or append headings (H1–H3), paragraphs, bullets, numbered lists, tables |
| `batch_update_doc` | `documents.batchUpdate` | Raw body-edit requests on the same `documentId` (follow-up edit) |

Tables are inserted in their own `batchUpdate`, then cell text is written from a fresh `documents.get`. The Docs API shifts cell indexes if you write them in the same batch as `insertTable`.

`batch_update_doc` allowlists body-edit request keys (`insertText`, `replaceAllText`, `updateParagraphStyle`, `insertTable`, …). Other keys are rejected.

## AuthZ locks

| Control | Implementation |
|---------|----------------|
| User-scoped only | Every tool calls `get_access_token()`; no admin/act-as |
| Fail-closed | Missing token → error; upstream errors propagate; unknown batch keys rejected |
| Redirect allowlist (exact) | `http://localhost:8787/callback`, `https://www.cursor.com/agents/mcp/oauth/callback` |
| State/nonce + PKCE | FastMCP OAuthProxy |
| Tokens encrypted at rest | Fernet-wrapped storage |
| No secrets in logs | Log redaction filter |
| Revoke on disconnect | `upstream_revocation_endpoint` → `oauth2.googleapis.com/revoke` |
| No shared broker token | Clients receive FastMCP JWTs only |
| No file handoff | In-place `batchUpdate` only. No export and no re-upload |
| Token vault | Encrypted server-side token store. Never paste tokens into Chat, issues, or logs |
| Workspace user | Connect as a Frans Workspace user for EA tooling. Docs belong in that Workspace, not personal Gmail |

## OAuth scopes

```
openid
https://www.googleapis.com/auth/userinfo.email
https://www.googleapis.com/auth/documents
```

`documents` is the create/edit scope for `documents.create`, `documents.get`, and `documents.batchUpdate`. Edits stay on that Doc. This server does not export the Doc and does not re-upload a file.

Not requested:

| Scope | Why it is absent |
|-------|------------------|
| `https://www.googleapis.com/auth/drive.file` | File create / parent only. Not needed until a Doc must be placed in a specific folder. Add this scope then, not full `drive`. |
| `https://www.googleapis.com/auth/drive` | Broader than file create / parent. |
| Gmail scopes | Not used. The shared OAuth client does not gain them from this Connect. |
| Calendar scopes | Not used. Same rule. |

Chat scopes stay on the Chat Connect flow. They are not part of this authorization request.

**Re-consent** after `documents` is added on the Google consent screen: disconnect and reconnect **Ruvos Google Docs** in Cursor. Chat Connect is unchanged.

## Workspace BAA

Docs and Drive are Workspace-covered only if Ruvos has an active Google Workspace BAA **and** the Doc lives in that Workspace (not personal Gmail). Confirm the BAA covers Docs before NFRHC or any PHI-adjacent assessment is written into a native Doc. If the BAA is absent or unclear, keep those assessments in the GitLab wiki or in non-PHI Drive folders until James or Frans confirms.

Soft-prove a **non-PHI sample Doc first**, then NFRHC. Steps: [`plugins/ruvos-google-docs/README.md`](../../plugins/ruvos-google-docs/README.md).

## Local development

```bash
cd services/google-docs-mcp
cp .env.example .env   # fill in values; reuse the Chat Google client id/secret
pip install -e ".[dev]"
export $(grep -v '^#' .env | xargs)
export USE_MEMORY_STORAGE=true
ruvos-google-docs-mcp
```

MCP endpoint: `http://localhost:8080/mcp`  
OAuth metadata: `http://localhost:8080/.well-known/oauth-authorization-server`

```bash
pytest
```

## GCP / Cloud Run deploy checklist

### 1. Enable the Docs API (same Ruvos GCP project as Chat)

```bash
gcloud services enable \
  docs.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  --project=PROJECT_ID
```

Enable `drive.googleapis.com` later only if `drive.file` is added for a parent folder. This service does not upload files through Drive.

### 2. Extend the existing OAuth client (do not create a new one)

1. Open the OAuth client already used by `google-chat-mcp`.
2. Add authorized redirect URI: `https://google-docs-mcp.ruvos.com/auth/callback`
3. On the OAuth consent screen, add `https://www.googleapis.com/auth/documents`. Do not add Gmail, Calendar, full `drive`, or `drive.file` for this wave.
4. Keep using that client's `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` (Secret Manager). Do not commit them. Do not put them in the Cursor plugin or in Chat. User tokens stay in this service's encrypted store.

### 3. Generate signing keys for this service only

```bash
python3 -c "import secrets; print('JWT_SIGNING_KEY=' + secrets.token_urlsafe(48))"
python3 -c "from cryptography.fernet import Fernet; print('STORAGE_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

Store in Secret Manager. Do **not** reuse Chat's `JWT_SIGNING_KEY` or `STORAGE_ENCRYPTION_KEY` (those keys are Chat's token store). Keep this service's keys stable across deploys.

### 4. Redis

Use the same Memorystore instance as Chat with a **different DB index** (for example `/1` instead of Chat's `/0`) so DCR registrations do not collide. `REDIS_CA_CERT` is required for `rediss://` (same fail-closed TLS behavior as Chat). `ALLOW_REDIS_INSECURE_TLS=1` is local/non-prod only.

### 5. Build and deploy

```bash
PROJECT_ID=your-project
REGION=us-central1
SERVICE=google-docs-mcp
IMAGE=gcr.io/$PROJECT_ID/$SERVICE

gcloud builds submit --tag $IMAGE services/google-docs-mcp

gcloud run deploy $SERVICE \
  --image $IMAGE \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars BASE_URL=https://google-docs-mcp.ruvos.com,REDIS_URL=rediss://:AUTH@10.0.0.1:6378/1 \
  --set-secrets \
    GOOGLE_CLIENT_ID=google-chat-mcp-client-id:latest,\
    GOOGLE_CLIENT_SECRET=google-chat-mcp-client-secret:latest,\
    JWT_SIGNING_KEY=google-docs-mcp-jwt-key:latest,\
    STORAGE_ENCRYPTION_KEY=google-docs-mcp-storage-key:latest,\
    REDIS_CA_CERT=google-chat-mcp-redis-ca:latest
```

`GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` in that example point at the **existing Chat** secrets. JWT and storage keys are new secrets for this service.

### 6. Custom domain

Map `google-docs-mcp.ruvos.com` → this Cloud Run service. That host is what `plugins/ruvos-google-docs/mcp.json` calls.

### 7. Verify

```bash
curl -s https://google-docs-mcp.ruvos.com/health
curl -s https://google-docs-mcp.ruvos.com/.well-known/oauth-authorization-server | jq .
```

Install **Ruvos Google Docs** from the Team Marketplace and Connect as a Frans Workspace user. Soft-prove a non-PHI sample Doc first; NFRHC waits on the BAA confirmation in the plugin README. Annie confirms the follow-up edit in the Doc UI. The prove-out artifact is that Doc.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_CLIENT_ID` | Yes | Existing Ruvos Google OAuth client id |
| `GOOGLE_CLIENT_SECRET` | Yes | Existing Ruvos Google OAuth client secret |
| `BASE_URL` | Yes | Public HTTPS URL (no trailing slash) |
| `JWT_SIGNING_KEY` | Yes | Signs FastMCP JWTs for this service |
| `STORAGE_ENCRYPTION_KEY` | Yes | Fernet key for encrypted token storage |
| `PORT` | No | HTTP port (Cloud Run sets it) |
| `HOST` | No | Bind address (default `0.0.0.0`) |
| `REDIS_URL` | **Yes (Cloud Run)** | Redis URL; use a different DB index than Chat |
| `REDIS_CA_CERT` | **Yes (`rediss://`)** | Memorystore server CA PEM |
| `ALLOW_REDIS_INSECURE_TLS` | No | `1` for local/non-prod only |
| `USE_MEMORY_STORAGE` | No | `true` for local dev only |

## License

MIT — see repository root.
