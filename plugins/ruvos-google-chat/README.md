# Ruvos Google Chat

Cursor / Grok Bot plugin for [Google Chat](https://chat.google.com) via Google's remote Chat MCP (`chatmcp.googleapis.com`).

## Why static OAuth?

Featured Gmail/Drive get host-managed Google Connect. Chat MCP does **not** support OAuth dynamic client registration, so this plugin uses Cursor **static OAuth**: your GCP OAuth client ID/secret (set in Dashboard → Plugins → Configure).

## One-time GCP (chatsAuth / project `533586060544`)

1. Google Auth Platform → Clients → create **Web application** (or reuse).
2. Authorized redirect URIs (register **both**):
   - `http://localhost:8787/callback` (desktop Cursor)
   - `https://www.cursor.com/agents/mcp/oauth/callback` (web / Agents)
   - Optional fallback: `cursor://anysphere.cursor-mcp/oauth/callback`
3. Enable Chat API + Chat MCP API; Chat app interactive features **off** (already done for write prove).
4. Scopes used by the plugin: `chat.spaces.readonly`, `chat.memberships.readonly`, `chat.messages.readonly`, `chat.messages.create`, `chat.users.readstate`.

## Install

1. Team Marketplace **Ruvos Marketplace** → install **Ruvos Google Chat**.
2. Dashboard → Plugins → **Configure** → paste Client ID + Client Secret.
3. Customize → Connect / authenticate when prompted (Google sign-in).
4. Prove: `search_conversations` + `send_message`.

## MCP

```json
{
  "mcpServers": {
    "ruvos-google-chat": {
      "type": "http",
      "url": "https://chatmcp.googleapis.com/mcp/v1",
      "auth": {
        "CLIENT_ID": "${GOOGLE_OAUTH_CLIENT_ID}",
        "CLIENT_SECRET": "${GOOGLE_OAUTH_CLIENT_SECRET}",
        "scopes": [ "...chat scopes..." ]
      }
    }
  }
}
```

## License

MIT
