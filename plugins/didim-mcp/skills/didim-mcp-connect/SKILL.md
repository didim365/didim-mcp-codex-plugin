---
name: didim-mcp-connect
description: >-
  Connecting, re-authenticating, checking the signed-in account, switching
  accounts, and troubleshooting the Didim MCP server in Codex. Didim MCP uses
  Microsoft (Entra) sign-in through Codex's own OAuth Connect — there is no API
  key. Use this when the user wants to connect, sign in, log in, reconnect,
  re-authorize, disconnect, or switch to a different Microsoft account; asks who
  they are currently signed in as; closed, cancelled, or missed the sign-in
  window that opened after installing the plugin; is upgrading from an older
  plugin version that used a personal API key; or reports that Didim MCP does
  not appear under /mcp, its tools are not loading, authentication failed, a
  tool returned 401/Unauthorized, the connection expired, Connect does nothing,
  or they see "No Didim MCP tools are exposed in this session."
  Korean triggers: "Didim MCP 연결해줘", "Didim MCP 로그인", "Didim MCP 인증해줘",
  "Microsoft 로그인해줘", "Didim MCP 재연결", "Didim MCP 다시 인증해줘",
  "아까 로그인 창 닫았는데 다시 로그인해줘", "설치할 때 인증 취소했어",
  "Connect 다시 해줘", "MCP 연결 안 됐어", "인증 만료됐어", "MCP 로그인 풀렸어",
  "지금 Didim MCP 누구로 로그인돼있어?", "현재 로그인 계정 알려줘",
  "Didim MCP 인증된 사용자 확인해줘", "내 MCP 계정 정보 보여줘",
  "Didim MCP 계정 바꿔줘", "다른 Microsoft 계정으로 로그인해줘",
  "Didim MCP 사용자 변경", "Didim MCP가 /mcp에 안 보여", "도구가 안 보여",
  "예전 API Key 설정이 남아 있어", "업그레이드 후 연결이 안 돼".
  English triggers: "connect Didim MCP", "sign in to Didim MCP", "retry OAuth",
  "reconnect Didim MCP", "authentication expired", "Didim MCP 401",
  "current Didim account", "who am I signed in as", "switch Didim MCP account",
  "sign in with another Microsoft account", "Didim MCP tools unavailable",
  "migrate Didim MCP from API key to OAuth".
---

# Didim MCP Connect

Didim MCP is **OAuth-only**. The plugin declares the hosted MCP server in its
manifest, and Codex's own MCP OAuth client performs the sign-in. Nothing in this
flow involves an API key, a bearer token, or an auth header.

**Never** ask the user for an API key, a `dv_` key, an access token, a refresh
token, a header value, or an MCP URL. Never edit `~/.codex/config.toml`, never
touch the credential store, and never build a Microsoft or Didim authorization
URL by hand. You start Codex's own sign-in; Codex owns discovery, PKCE, the
loopback callback, token storage, and refresh.

## Always check the state first

Before proposing any fix, establish which of these is true:

| Check | Codex app | Codex CLI (only if separately installed) |
| --- | --- | --- |
| Is the plugin installed and enabled? | plugin screen | `codex plugin list` |
| Is `didim-mcp` registered? | `/mcp` in a new chat | `codex mcp list` |
| Is it signed in? | `/mcp` / plugin Connect state | `codex mcp list` → `Auth` column, or `codex mcp list --json` → `auth_status` |

`auth_status` is `not_logged_in` until OAuth completes. **Registration and
sign-in are two different things** — the server can be registered and listed
while no one is signed in. Do not treat "not logged in" as a broken install.

## The sign-in window was closed or cancelled

Installing the plugin opens the Microsoft sign-in. If the user closed it,
cancelled, or never finished, **the plugin is still installed and the MCP server
is still registered.** Nothing is broken and nothing needs reinstalling.

Confirm the state above, then simply start the sign-in again:

- **Codex app:** press **Connect** on the Didim MCP plugin.
- **Codex CLI:** `codex mcp login didim-mcp`

Retrying after an abandoned attempt is verified to work without reinstalling.
Say so plainly — users often assume they have to remove and re-add the plugin.

## Who am I signed in as?

Only meaningful once signed in. If `auth_status` is `not_logged_in`, do **not**
call a tool to find out. Say:

> 현재 Didim MCP에 로그인되어 있지 않습니다. Microsoft 로그인 연결을 시작할까요?

and offer the sign-in above. Never suggest an API key.

When signed in, look in `tools/list` for whichever of these the user actually
has exposed, and call it with `{}`:

- `didim-mcp-auth__get_current_user_profile`
- `didim-vault__get_current_user_profile`

Use only a tool that is present. If neither is exposed, that is a portal
entitlement matter, not an auth failure — say the identity tool is not enabled
for this account and stop.

Report only what the tool returns and policy allows: display name, email, role,
status, `auth_provider`, `auth_type`, scopes. A healthy Microsoft OAuth session
shows `auth_provider = MICROSOFT`, `auth_type = OAUTH`.

**Never** print an access token, refresh token, authorization code, session
secret, or any Vault credential — not even truncated.

## Sign in as a different Microsoft account

1. Show the current account first (above), so the user sees what is being
   replaced.
2. Explain the effect: the current session is signed out, and every Didim tool
   stops working until the new sign-in finishes.
3. Get explicit approval, then:
   - **Codex app:** **Disconnect**, then **Connect**.
   - **Codex CLI:** `codex mcp logout didim-mcp` then `codex mcp login didim-mcp`
4. Confirm the new identity with the profile tool.

The browser may reuse an existing Microsoft SSO session and sign the user
straight back into the same account. If that happens, tell them to pick
**"다른 계정으로 로그인"** on the Microsoft sign-in page. Account selection is
the Didim login service's behaviour — do not try to force it from here.

During an account switch, never remove the plugin, remove the marketplace,
re-register the MCP URL, edit `config.toml`, or delete credential files.
Sign-out is `logout` / Disconnect, nothing else.

## Expired, 401, or "login dropped"

Codex refreshes tokens on its own. If it still fails, the fix is the same
sign-in retry: Connect (app) or `codex mcp login didim-mcp` (CLI). No
reinstall, no cleanup script — unless the triage below points at legacy config.

## Running a CLI command

`codex mcp login` / `logout` change authentication state and may open a browser.
Explain what will happen and get approval before running either, e.g.:

> Didim MCP의 Microsoft OAuth 연결을 다시 시작합니다. 브라우저에서 Microsoft
> 로그인 창이 열립니다. 진행할까요?

Only propose CLI commands to users who installed the standalone `codex` CLI.
Codex app users have Connect/Disconnect in the plugin screen; do not tell them
to run the `codex.exe` bundled inside the app.

Reading state (`codex mcp list`, `codex plugin list`) and calling the read-only
profile tool need no special approval beyond normal policy.

## Upgrading from 0.1.x (API key era)

Plugin versions 0.1.x wrote an `[mcp_servers.didim-mcp]` block, including an
`X-Didim-Vault-Api-Key` header, into the user's `~/.codex/config.toml`. That
block **shadows the plugin-provided server**: Codex keeps using the old entry,
Connect never runs, and the server rejects the request because Didim no longer
accepts user API keys.

Symptoms: `/mcp` shows `didim-mcp` but every tool call fails authentication, or
the connection points at an old URL, or Connect is not offered at all.

Fix — run the bundled cleanup script, on Windows:

- Double-click
  `%USERPROFILE%\.codex\plugins\cache\didim\didim-mcp\<version>\scripts\migrate-didim-mcp.cmd`
- or: `powershell -NoProfile -ExecutionPolicy Bypass -File "<...>\scripts\migrate-didim-mcp.ps1"`

Explain before running and get explicit approval. The script:

- backs up `config.toml` with a timestamp,
- removes only the `[mcp_servers.didim-mcp]` and `[mcp_servers.didim-mcp.*]`
  tables (other MCP servers and settings are preserved, in order),
- never reads back, prints, or logs the old key value.

Users who installed the `codex` CLI separately can instead run
`codex mcp remove didim-mcp`, which has the same effect on that block.

Afterwards: fully quit all Codex windows, start Codex again, then press
**Connect**.

The old timestamped `config.toml.backup-*` files still contain the retired key.
Mention that they can be deleted; do not open them.

## Error triage — do not answer all of these the same way

| State | Evidence | Action |
| --- | --- | --- |
| Plugin/MCP not registered at all | `didim-mcp` absent from `/mcp` and `codex mcp list` | Confirm the plugin is installed and enabled, then restart Codex. Reinstall only if it is genuinely missing |
| Registered, never signed in | `auth_status: not_logged_in` | Connect / `codex mcp login didim-mcp` |
| Session expired or 401 | was working, now auth errors | Same sign-in retry. Disconnect → Connect if it repeats |
| Legacy 0.1.x config shadowing | old URL, or auth fails right after upgrading | Cleanup script (above), then restart, then Connect |
| Connected but a tool is missing | other Didim tools work | Portal entitlement. Enable the tool in the Didim portal, restart Codex. **Not** an auth problem |
| Tool authorization denied | tool exists, server refuses this user | The account lacks permission. Point at the portal/admin, do not retry or reconnect |
| Provider credential failure | tool runs, upstream credential injection fails | Server-side Vault resource credential. Ask an admin to check it. Never ask the user for a `serviceKey` |
| Upstream API error | provider returned an error | Report the HTTP status and the safe error text |

## Hard rules

- **Reinstalling is not a troubleshooting step.** Propose removing and
  re-adding the plugin only when you have evidence the plugin itself is absent
  or its cache is corrupt. A cancelled sign-in, an expired session, and a
  missing tool are all fixed without it.
- Never run the cleanup script without explicit approval.
- Never ask for, echo, log, or store any credential, token, or header value.
- Never register, rewrite, or repair the MCP server entry yourself, and never
  hand-edit `config.toml` or the credential store.
