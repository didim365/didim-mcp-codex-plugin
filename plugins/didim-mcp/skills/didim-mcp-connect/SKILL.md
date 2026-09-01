---
name: didim-mcp-connect
description: >-
  Signing in to, re-authenticating, and troubleshooting the Didim MCP server in
  Codex, plus checking or switching the Microsoft account. Didim MCP is
  OAuth-only — Microsoft (Entra) sign-in run by Codex's own MCP OAuth client;
  there is no API key. Use this when the user wants to connect, sign in, log in,
  reconnect, re-authenticate, sign out, or switch to a different Microsoft
  account; asks who they are currently signed in as; closed, cancelled, or
  missed the sign-in window that opened when the plugin was installed; is
  upgrading from an older plugin version that used a personal API key; or
  reports that Didim MCP does not appear under /mcp, its tools are not loading,
  authentication failed, a tool returned 401/Unauthorized, or the connection
  expired.
  Korean triggers: "Didim MCP 연결해줘", "Didim MCP 로그인", "Didim MCP 인증해줘",
  "Microsoft 로그인해줘", "Didim MCP 다시 로그인해줘", "Didim MCP 재연결",
  "Didim MCP 다시 인증해줘", "아까 로그인 창 닫았는데 다시 연결해줘",
  "설치할 때 인증 취소했어", "로그인 창 닫았어", "MCP 연결 안 됐어",
  "Didim 로그인 안 됐어", "인증 만료됐어", "MCP 로그인 풀렸어", "401 떠",
  "지금 Didim MCP 누구로 로그인돼있어?", "현재 로그인 계정 알려줘",
  "Didim MCP 인증된 사용자 확인해줘", "내 MCP 계정 정보 보여줘",
  "Didim MCP 계정 바꿔줘", "다른 Microsoft 계정으로 로그인해줘",
  "Didim MCP 사용자 변경", "Didim MCP 로그아웃", "Didim MCP가 /mcp에 안 보여",
  "도구가 안 보여", "예전 API Key 설정이 남아 있어", "업그레이드 후 연결이 안 돼".
  English triggers: "connect Didim MCP", "sign in to Didim MCP", "log in again",
  "retry OAuth", "cancelled sign-in", "closed the sign-in window",
  "reconnect Didim MCP", "re-authenticate", "authentication expired",
  "Didim MCP 401", "current signed-in account", "who am I signed in as",
  "switch Didim MCP account", "change Microsoft account", "sign out of Didim MCP",
  "Didim MCP tools unavailable", "migrate Didim MCP from API key to OAuth".
---

# Didim MCP Connect

Didim MCP is **OAuth-only**. The plugin declares the hosted MCP server in its
manifest; Codex's own MCP OAuth client performs the sign-in and owns discovery,
PKCE, the loopback callback, token storage, and refresh.

**Never** ask the user for an API key, a `dv_` key, an access token, a refresh
token, a header value, or an MCP URL. Never edit `~/.codex/config.toml`, never
touch the credential store, and never build a Microsoft or Didim authorization
URL by hand.

## What you can and cannot do — say it precisely

You **can**: read the connection state, call the read-only profile tool, and —
where the environment allows shell commands — run Codex's own
`codex mcp login` / `codex mcp logout` to start or clear the sign-in.

You **cannot**: type the Microsoft password, approve MFA, or pick the account in
Microsoft's account picker. Those are the user's steps, inside the browser.

Do **not** answer with a blanket "저는 인증 화면을 조작할 수 없습니다". Name the
specific step the user has to do, and do the rest yourself.

## The authentication UI: what is actually verified

- The **install-time** sign-in is real: installing the plugin opens the
  Microsoft OAuth flow. This is verified.
- In the Codex App UI that was tested, a plugin-provided MCP server such as
  `didim-mcp` appears under "플러그인 제공" **without** a Connect button,
  Disconnect button, gear, or toggle.

So **never tell the user to press Connect or Disconnect on the plugin screen**
for an already-installed plugin, and never send them looking for a gear icon.
Drive the lifecycle through the commands below instead. (This describes the UI
as tested; a future Codex release may add such controls.)

## Step 1 — always read the state first

Never prescribe a fix before knowing which state you are in.

```bash
codex mcp list --json      # → auth_status: "not_logged_in" | logged in
codex mcp get didim-mcp    # url / transport / headers
codex plugin list          # is the plugin installed and enabled?
```

These are read-only; run them under the normal policy. In a chat, `/mcp` also
shows whether `didim-mcp` and its tools are present.

**Registration and sign-in are two different things.** `didim-mcp` can be listed
and enabled while `auth_status` is `not_logged_in`. That is not a broken
install, and it is not a reason to reinstall anything.

If you cannot run shell commands in this environment, ask the user to run
`codex mcp list` and paste the `Auth` column, or to check `/mcp`.

## Step 2 — the commands (these are the only ones that exist)

```bash
codex mcp login  didim-mcp     # start / restart Microsoft OAuth sign-in
codex mcp logout didim-mcp     # clear the stored sign-in
```

There is no `codex mcp connect`, `reconnect`, or `enable`. Do not invent one.

Two behaviours to handle correctly:

- **`login` blocks** until the browser callback completes, and prints
  `Authorize ... by opening this URL in your browser:` with the URL. If you run
  it, tell the user first that it will wait for them to finish signing in. If
  the browser does not open on its own, give them the printed URL.
- **`logout` can exit non-zero** when there was nothing stored to delete (e.g.
  `failed to delete OAuth tokens from keyring`). Do **not** report that as a
  failure — confirm the real outcome with `codex mcp list --json`.

Both change authentication state: explain and get approval before running
either. For example:

> Didim MCP의 Microsoft OAuth 연결을 다시 시작합니다. 브라우저에서 Microsoft
> 로그인 창이 열리면 계정 선택·비밀번호·MFA를 직접 완료해주세요. 진행할까요?

If shell execution is unavailable, do not fall back to imaginary UI. Say so and
hand over the exact command:

> 이 환경에서는 제가 Codex CLI 명령을 직접 실행할 수 없습니다. 터미널에서 아래를
> 실행해주세요:
> `codex mcp login didim-mcp`

## Not signed in → sign in

Triggers: "Didim MCP 연결해줘", "Microsoft 로그인해줘", "MCP 인증 다시 해줘",
"Didim 로그인 안 됐어".

Confirm `auth_status: not_logged_in`, then run (or hand over)
`codex mcp login didim-mcp`. Never remove the plugin, reinstall it, re-register
the MCP URL, or edit `config.toml`.

## The sign-in window was closed or cancelled

Triggers: "아까 로그인 창 닫았는데 다시 연결해줘", "설치할 때 인증 취소했어".

Installing opens the Microsoft sign-in; closing or cancelling it leaves the
plugin **installed** and `didim-mcp` **registered**, with
`auth_status: not_logged_in`. Verified: after an abandoned sign-in the
registration and the installation both survive and the login can simply be run
again.

Say that plainly — users assume they must remove and re-add the plugin — then
do the same thing as above: `codex mcp login didim-mcp`.

## "다시 로그인해줘" — branch on the current state

Do not blindly re-run `login`.

- **`not_logged_in`** → just `codex mcp login didim-mcp`.
- **Already signed in** → the user means "end this session and sign in again".
  1. Show the current account (below).
  2. Explain that the current sign-in is cleared and every Didim tool stops
     working until the new sign-in completes.
  3. Get explicit approval.
  4. `codex mcp logout didim-mcp`, then `codex mcp login didim-mcp`.
  5. Confirm the new state and identity.

## Who am I signed in as?

If `auth_status` is `not_logged_in`, do **not** call a tool to find out. Say:

> 현재 Didim MCP에 로그인되어 있지 않습니다. Microsoft 로그인을 시작할까요?

and offer the sign-in. Never mention an API key.

When signed in, use whichever of these is actually present in `tools/list`, with
`{}`:

- `didim-mcp-auth__get_current_user_profile`
- `didim-vault__get_current_user_profile`

Call only a tool that is exposed. If neither is, that is a portal entitlement
matter, not an auth failure — say the identity tool is not enabled for this
account and stop.

Report what the tool returns and policy allows: display name, email, role,
status, `auth_provider`, `auth_type`, scopes. A healthy session shows
`auth_provider = MICROSOFT`, `auth_type = OAUTH`.

**Never** print an access token, refresh token, authorization code, session
secret, or any Vault credential — not even truncated.

## Sign in as a different Microsoft account

Triggers: "Didim MCP 계정 바꿔줘", "다른 Microsoft 계정으로 로그인해줘",
"switch Didim MCP account".

1. Show the current account, so the user sees what is being replaced.
2. Explain the effect (sign-out, then a fresh sign-in).
3. Get explicit approval.
4. `codex mcp logout didim-mcp`
5. `codex mcp login didim-mcp`
6. Tell the user to pick **"다른 계정으로 로그인"** in the Microsoft window — the
   browser may still hold an SSO session and would otherwise sign them straight
   back into the same account.
7. Confirm the new identity with the profile tool.

Account selection belongs to Microsoft and the Didim login service; do not try
to force it from here. During a switch, never remove the plugin or marketplace,
re-register the MCP URL, edit `config.toml`, or delete credential files.

## Expired, 401, or "login dropped"

Codex refreshes tokens on its own. If it still fails, this is the same
`logout` → `login` cycle above, with approval. No reinstall, and no cleanup
script — unless the triage table points at legacy config.

## Upgrading from 0.1.x (API key era)

Plugin versions 0.1.x wrote an `[mcp_servers.didim-mcp]` block, including an
`X-Didim-Vault-Api-Key` header, into the user's `~/.codex/config.toml`. That
block **shadows the plugin-provided server**: Codex keeps using the old entry,
OAuth never runs, and the server rejects the request because Didim no longer
accepts user API keys.

Symptoms: `didim-mcp` is present but every tool call fails authentication, or it
points at an old URL.

Fix — run the bundled cleanup script, on Windows:

- Double-click
  `%USERPROFILE%\.codex\plugins\cache\didim\didim-mcp\<version>\scripts\migrate-didim-mcp.cmd`
- or: `powershell -NoProfile -ExecutionPolicy Bypass -File "<...>\scripts\migrate-didim-mcp.ps1"`

Explain before running and get explicit approval. The script backs up
`config.toml` with a timestamp, removes only the `[mcp_servers.didim-mcp]` and
`[mcp_servers.didim-mcp.*]` tables (other MCP servers keep their content and
order), and never reads back, prints, or logs the old key value.

`codex mcp remove didim-mcp` has the same effect on that block.

Afterwards: fully quit Codex, start it again, then sign in with
`codex mcp login didim-mcp`.

The old timestamped `config.toml.backup-*` files still contain the retired key.
Mention that they can be deleted; do not open them.

## Error triage — these are not the same problem

| State | Evidence | Action |
| --- | --- | --- |
| Plugin or MCP not registered | `didim-mcp` absent from `codex mcp list` and `/mcp` | Confirm the plugin is installed and enabled, restart Codex. Reinstall only if it is genuinely absent |
| Registered, never signed in | `auth_status: not_logged_in` | `codex mcp login didim-mcp` |
| Session expired / 401 | worked before, auth errors now | `logout` → `login`, with approval |
| Legacy 0.1.x config shadowing | old URL, or auth fails right after upgrading | Cleanup script, restart, then `login` |
| Signed in but a tool is missing | other Didim tools work | Portal entitlement — enable it in the Didim portal, restart Codex. **Not** an auth problem |
| Tool authorization denied | tool exists, server refuses this user | The account lacks permission. Point at the portal/admin; do not reconnect |
| Provider credential failure | tool runs, upstream credential injection fails | Server-side Vault resource credential. Ask an admin. Never ask the user for a `serviceKey` |
| Upstream API error | provider returned an error | Report the HTTP status and the safe error text |

## Hard rules

- **Reinstalling is not a troubleshooting step.** A cancelled sign-in, an
  expired session, and a missing tool are all fixed without it. Propose removing
  and re-adding the plugin only with evidence that the plugin itself is absent
  or its cache is corrupt — or when the user has no way to run `codex`, in which
  case say explicitly that reinstalling is a last resort that re-triggers the
  install-time sign-in.
- Never point at a Connect/Disconnect button or gear for an installed
  plugin-provided MCP server; the tested Codex App UI does not expose them.
- Never run `login`, `logout`, or the cleanup script without explicit approval.
- Never ask for, echo, log, or store any credential, token, or header value.
- Never register, rewrite, or repair the MCP server entry yourself.
