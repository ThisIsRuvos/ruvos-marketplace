# Ruvos Marketplace

Cursor / Grok Bot **Team Marketplace** for Ruvos plugins.

## Layout

- `.cursor-plugin/marketplace.json` — marketplace manifest
- `plugins/<name>/` — one Cursor plugin per folder (Gmail-shaped)

## Plugins

| Plugin | Path |
|--------|------|
| Ruvos Google Chat | `plugins/ruvos-google-chat/` |

## Install (Ruvos)

1. Admin: Dashboard → Plugins → Team Marketplaces → **Import from Repo** → this GitHub URL.
2. Marketplace Access: All Members (or restrict as needed). Auto Refresh on.
3. Customize → install **Ruvos Google Chat** → Google Connect.
4. Prove via the plugin: `search_conversations` + `send_message` (not local Google-chat-rest).

## Repo

https://github.com/ThisIsRuvos/ruvos-marketplace

## License

MIT (see per-plugin LICENSE files).
