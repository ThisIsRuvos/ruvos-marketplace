# Ruvos Google Chat

Cursor / Grok Bot plugin that connects agents to [Google Chat](https://chat.google.com) through Google's remote [Model Context Protocol](https://modelcontextprotocol.io/) server — the same packaging pattern as Cursor's Featured [Gmail](https://github.com/cursor/plugins/tree/main/third_party/gmail), [Google Calendar](https://github.com/cursor/plugins/tree/main/third_party/google-calendar), and [Drive](https://github.com/cursor/plugins/tree/main/third_party/google-drive) plugins.

## MCP

```json
{
  "mcpServers": {
    "ruvos-google-chat": {
      "type": "http",
      "url": "https://chatmcp.googleapis.com/mcp/v1"
    }
  }
}
```

Auth is OAuth 2.0 against Google. Cursor / Grok Bot should prompt for Google sign-in when the plugin connects (same Connect UX as Featured Gmail).

**Tools (Google Chat MCP):** `search_conversations`, `list_messages`, `search_messages`, `send_message`, `mark_as_read`, `mark_as_unread`, `list_memberships`.

## Install (Ruvos)

### Team Marketplace (preferred for Ruvos employees)

1. Admin: Dashboard → Plugins → Team Marketplaces → import this repo (or add plugin).
2. Set Marketplace Access for Ruvos; Default On or Required as desired.
3. Each user: Customize → install **Ruvos Google Chat** → complete Google sign-in.

### Local test

1. Copy this folder to `~/.cursor/plugins/local/ruvos-google-chat`.
2. Reload Cursor / Grok Bot window.
3. Open Customize and confirm the connector; authenticate with Google.

## Status (2026-09-16)

- Developer Preview: registered for GCP project `533586060544` (chatsAuth).
- Remote MCP prove: `search_conversations`, `list_messages`, `send_message` succeeded.
- Next: GitHub twin + Team Marketplace import + Connect prove (Eng).

## Google Cloud (Workspace) prerequisites

Google documents Chat MCP as **Developer Preview**. Per [Configure the Chat MCP server](https://developers.google.com/workspace/chat/api/guides/configure-mcp-server):

1. Enable `chat.googleapis.com` and `chatmcp.googleapis.com` on a GCP project.
2. Configure OAuth consent + scopes (`chat.spaces.readonly`, `chat.memberships.readonly`, `chat.messages.readonly`, `chat.messages.create`, `chat.users.readstate`).
3. For **send** / write tools: configure a Chat app with **interactive features off** (not a Marketplace inbound front door).

Cursor's Featured Gmail plugin does not embed an OAuth client in `mcp.json`; Connect is host-managed. If Ruvos Team Marketplace Connect does not attach Google OAuth the same way, Eng may need to add host `auth` / plugin `variables` — treat that as a follow-up prove.

## Docs

- Chat MCP configure: https://developers.google.com/workspace/chat/api/guides/configure-mcp-server
- Chat MCP reference: https://developers.google.com/workspace/chat/api/reference/mcp
- Workspace MCP overview: https://developers.google.com/workspace/guides/configure-mcp-servers
- Cursor plugins: https://cursor.com/docs/plugins

## Relation to prior seed

Annie's live `user-Google-chat-rest` is a **local REST API wrapper** used when chatmcp Connect was not available in Featured form. This plugin targets Google's official remote Chat MCP URL so Install / Connect can match Gmail.

## GitLab mirror

Optional Eng mirror (not Team Marketplace home): https://gitlab.com/ruvos/frans/ruvos-google-chat-plugin

## License

MIT
