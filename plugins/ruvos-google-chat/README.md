# Ruvos Google Chat

Cursor plugin for Google Chat via the **Ruvos OAuth middle-layer MCP**.

## Connect

1. Install from the Ruvos Team Marketplace.
2. Click **Connect** — Cursor performs DCR against our Authorization Server (no Google client secret needed).
3. Sign in with Google and approve scopes (re-consent after 0.5.0 scope expand).

## MCP endpoint

`https://google-chat-mcp.ruvos.com/mcp`

## Tools

- `search_conversations` — find spaces/DMs by name or participants
- `list_messages` — read messages from a conversation
- `search_messages` — search message content
- `send_message` — **default** send as the authenticated human (tell/DM/reply)
- `app_send_message` — App Send for system notifications (App · for You badge)
- `edit_message` / `delete_message` — user-authored messages only

## Server source

Implementation: [`services/google-chat-mcp/`](../../services/google-chat-mcp/)
