# Changelog

## 0.5.6

- **Fix:** Memorystore `rediss://` TLS now verifies the server CA via `REDIS_CA_CERT` (PEM env/secret) using `ssl_ca_certs`. Fixes `SSL: CERTIFICATE_VERIFY_FAILED` on OAuth token/DCR Redis paths. `rediss://` without CA fails closed at startup (no verify-off in production).

## 0.5.5

- **Fix:** Declare `py-key-value-aio[redis]` so Cloud Run startup succeeds when `REDIS_URL` is set (`RedisStore` requires the `redis` extra).

## 0.5.4

- **Fix:** App Send registry `put` now stores a `dict` (`{"registered": true}`) instead of bare string `"1"`, matching `key_value` `BaseStore.put` type hints. Restores `app_send_message` after v0.5.3 deploy regression.

## 0.5.3

- **Fix:** `edit_message` / `delete_message` now fail closed on App Send messages **before** any Chat REST PATCH/DELETE. Chat REST `GET` can return `sender.type=HUMAN` with a matching `users/{id}` for App Send; we record `messageName`s from `app_send_message` in encrypted KV and consult that registry at mutate time. Field checks also reject non-`users/` and `bots/` senders.
- App/bot and registered App Send attempts return the explicit app/bot error (not scope 403, not "not authored").

## 0.5.2

- **Fix:** `edit_message` / `delete_message` ownership now matches message `sender.name` numeric `users/{id}` to OAuth userinfo `sub` (Google account id). Fixes false-negative when Chat returns numeric sender ids without `sender.email` (0.5.1 email-only fallback was insufficient).
- App-authored and other-user messages still fail closed with explicit errors.

## 0.5.1

- **Fix:** `edit_message` / `delete_message` no longer call non-existent Chat `GET /users/me` (404). Ownership checks resolve identity via OAuth userinfo (`userinfo.email`) and compare message `sender` by email or `users/{email}` alias.
- App-authored and other-user messages still fail closed with explicit errors (not user-resolve 404).

## 0.5.0

- **Dual send:** `send_message` now posts via Chat REST as the authenticated human (default for tell/DM/reply).
- **App Send:** new `app_send_message` retains the Chat MCP proxy path (App · for You badge) for system/notifications.
- **Edit/delete:** `edit_message` and `delete_message` via Chat REST on user-authored messages only (fail closed on app/other-user).
- OAuth scope added: `https://www.googleapis.com/auth/chat.messages` (re-consent required).

## 0.4.2

- Ruvos-branded OAuth consent page (CSP-safe logo, auth styling).

## 0.3.0

- Point remote HTTP MCP at Ruvos middle-layer (`https://google-chat-mcp.ruvos.com/mcp`) instead of `chatmcp.googleapis.com`.
- OAuth via Ruvos Authorization Server with DCR — users no longer paste Google client secrets into Cursor.
- Chat-min tools: `search_conversations`, `list_messages`, `search_messages`, `send_message`.
- AuthZ: user-scoped, fail-closed, exact-match Cursor redirect allowlist, encrypted per-user tokens, revoke on disconnect.

## 0.1.0

- Initial Ruvos packaging of Google's Chat remote MCP (direct `chatmcp.googleapis.com`).
