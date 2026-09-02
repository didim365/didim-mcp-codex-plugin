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
manifest; the Codex host's own MCP OAuth client performs the sign-in and owns
discovery, PKCE, the callback, token storage, and refresh.

**Never** ask the user for an API key, a `dv_` key, an access token, a refresh
token, a header value, or an MCP URL. Never edit `~/.codex/config.toml`, never
touch the credential store, and never build a Microsoft or Didim authorization
URL by hand.

## Source of truth: this session, not a nested CLI

Read this before doing anything else. Getting it wrong is the single largest
failure mode of this skill.

Judge the connection **from the session you are running in**, in this order:

1. **Tools exposed to this session.** If Didim MCP tools are present in your
   own tool registry, the plugin is installed and its server is registered.
   That is direct evidence and it outranks everything below.
2. **The result of actually calling a tool.** Three different outcomes, three
   different answers — see the table below.
3. **Plugin context.** If the request arrived through
   `plugin://didim-mcp@didim`, or this skill was selected because the Didim MCP
   plugin is attached, the plugin exists in this session. It does **not** by
   itself prove the sign-in completed or that tools are exposed.
4. **`/mcp` in the composer.** A host-side view of the servers connected to
   this session. Ask the user to check it when you need a second opinion.

| Tool call outcome | What it means | What to say |
| --- | --- | --- |
| Succeeds | Signed in and working | Report the result |
| Auth error (401, `unauthorized`, `authentication_required`, `invalid_token`) | Server reachable in this session, Microsoft sign-in needed | See "Sign-in is needed" |
| Tool not present, **other Didim tools work** | This session does not expose that one tool | Portal entitlement — not an auth problem |
| **No Didim tool at all** | The server itself is unavailable to this session | See "No Didim tools at all" — do **not** call it a portal entitlement problem |

### The nested `codex` CLI is a different runtime

A `codex` command you run in a shell is **not** a window into the Codex app you
are running inside. Verified on a real installation:

- The Codex app executes shell commands as a **separate sandbox OS user**
  (`CodexSandboxOffline` / `CodexSandboxOnline` on Windows), so a nested
  `codex` reads that user's Codex home, not the app user's.
- The app's plugins live in the app user's Codex home
  (`plugins/didim-mcp`, `plugins/cache/didim/didim-mcp/<version>`), and its MCP
  OAuth credentials live in that same home, in the app's own encrypted store.
  The sandbox user has neither.

That is why, in a real Human UAT, a chat that was **demonstrably running the
Didim MCP plugin** got `codex mcp list` = no servers and `codex plugin list` =
no plugins. Both outputs were correct *for the shell's own runtime* and
irrelevant to the app.

So, absolutely:

- **Never run `codex mcp list` or `codex plugin list` as a preflight** before
  answering a Didim question. Call the tool.
- **Never conclude "the plugin is not installed" or "you are not signed in"**
  from an empty nested CLI listing.
- If a CLI result and this session's tools disagree, **this session wins.**
- Say `codex mcp list` shows the **CLI context's** registry — never that it
  shows what the Codex app has.

## What you can and cannot do — say it precisely

You **can**: call read-only Didim tools, report the signed-in identity, explain
exactly what state the connection is in, and trigger the host's own
authentication flow by attempting a tool call.

You **cannot**: type the Microsoft password, approve MFA, or pick the account in
Microsoft's account picker. Those happen in the user's browser.

Do **not** answer with a blanket "저는 인증 화면을 조작할 수 없습니다". Name the
specific step that is the user's, and do the rest yourself.

## What the authentication UI actually is

Verified:

- **Install-time sign-in is real.** The marketplace entry sets
  `policy.authentication: ON_INSTALL`, and installing the plugin opens the
  Microsoft OAuth flow.
- **A tool call on an unauthenticated OAuth MCP server triggers the host's
  authentication.** This is the documented Codex/ChatGPT plugin behaviour: the
  user authenticates when a tool is first invoked, driven by the server's `401`
  + `WWW-Authenticate` (`_meta["mcp/www_authenticate"]`) response. This is the
  natural-language re-auth path — use it.
- Codex documents an **Authenticate** action in Settings → MCP servers "when an
  OAuth server requires sign-in".

Not verified, and therefore never promised:

- In the Codex app UI that was tested, the plugin-provided `didim-mcp` entry
  under "플러그인 제공" showed **no** Connect button, Disconnect button, gear, or
  toggle. Never send the user looking for one. (This describes the build that
  was tested; a later release may add controls.)
- There is **no verified way** for this skill to clear the app's stored Didim
  sign-in. Do not claim one.

## Case A — "지금 Didim MCP 누구로 로그인돼있어?"

Also: "현재 로그인 계정 알려줘", "내 MCP 계정 정보 보여줘", "who am I signed in as".

**Call the identity tool first. No CLI, no preflight.**

Use whichever of these is present in this session, with `{}`:

- `didim-mcp-auth__get_current_user_profile`
- `didim-vault__get_current_user_profile`

Then:

- **Success** → report what the tool returned and policy allows: display name,
  email, role, status, `auth_provider`, `auth_type`, scopes. A healthy session
  shows `auth_provider = MICROSOFT`, `auth_type = OAUTH`.
- **Auth error** → "Didim MCP는 현재 세션에 연결되어 있지만 Microsoft 로그인이
  필요합니다." Then Case C.
- **Neither tool exposed** → first check whether *any* Didim tool is exposed.
  If some are, that one is a portal entitlement matter, not an auth failure.
  If **none** are, this is not about entitlements at all — see "No Didim tools
  at all". Either way, do not say the plugin is missing.

**Never** print an access token, refresh token, authorization code, session
secret, or any Vault credential — not even truncated.

## Case B — ordinary Didim tool use

Use the tools exposed to this session. No connection check first. If a call
fails, branch on the outcome table above. `didim-mcp-usage` and
`molit-apartment-transactions` own the actual work; they delegate here only on
an auth error.

## Case C — "Didim MCP 연결해줘"

1. Establish the state the cheap way: call a read-only Didim tool (the identity
   tool is ideal).
2. **It succeeds** → "이미 연결되어 있습니다." Offer the identity as proof. Do
   not sign anything out.
3. **Auth error** → the sign-in is needed; go to "Sign-in is needed".
4. **No Didim tools at all in this session** → see "No Didim tools at all".

## No Didim tools at all

Zero Didim tools in this session means the **server is unavailable to the
session**, not that the user lost portal entitlements. Say so, and never
answer this state with "포털에서 Tool을 활성화해 달라고 요청하세요."

The verified cause, seen on a real installation: Codex holds a stored Didim
sign-in, tries to refresh it at startup, and the Didim auth server rejects the
refresh token. The MCP server then never starts, so no tool is ever exposed —
while `/mcp` still shows `didim-mcp` as **사용함 / 인증됨(OAuth)**, because that
line reflects *stored credentials*, not a successful refresh. A `/mcp` badge is
therefore not proof that the connection works.

Tell the user, in this order:

1. The sign-in Codex has stored is no longer accepted; it has to be renewed.
   This is expected after a token expires or is revoked — it is not a portal
   permission change and not a plugin defect.
2. Fully quit and restart Codex, then use a Didim tool. Invoking a tool is what
   makes the host raise its Microsoft sign-in.
3. If Settings → MCP servers offers **Authenticate** for `didim-mcp`, use it.
4. Only if neither renews the sign-in: reinstall the plugin, which re-runs the
   install-time sign-in. Say plainly that this is the last resort.

Portal entitlement is the right answer **only** when other Didim tools are
working and a specific one is missing.

## Sign-in is needed

State it plainly, then give the paths that are actually verified:

1. **Retry the tool.** The host raises its own authentication when an
   unauthenticated OAuth MCP tool is invoked. Say what will happen: a Microsoft
   window opens and the user completes account selection, password, and MFA
   themselves. Then retry the call.
2. **The host's own MCP settings.** Codex documents an **Authenticate** action
   in Settings → MCP servers for a server that requires sign-in. Offer it as
   the host-side path — and do not insist it exists for the plugin-provided
   entry, because in the tested build it did not.
3. **Reinstalling the plugin re-runs the install-time sign-in**, since the
   marketplace policy is `ON_INSTALL`. Mention this only after 1 and 2, and
   name it as a last resort.

Never point at a Connect/Disconnect button.
Never claim a nested `codex mcp login` fixes the app's sign-in — it does not.

## Case D — "Didim MCP 다시 로그인해줘"

Read the state first, then branch. Do not act blindly.

- **Tool call succeeds** → the user is signed in. Say so, show the account, and
  ask what they actually want: staying as-is, or switching accounts (Case E).
  Do not tear down a working session for no reason.
- **Auth error** → this is simply "Sign-in is needed" above.

Be honest about the middle case: if the user is signed in and wants a *fresh*
sign-in on the **same** account, there is no verified way for this skill to
clear the app's stored credential. Say that, and offer the host-side paths.

## Case E — "다른 Microsoft 계정으로 로그인해줘"

1. Show the current account first, so the user sees what would be replaced.
2. Be accurate about the limit: **no verified skill-side mechanism switches the
   app's Didim sign-in.** Signing out of the app's MCP credential store is not
   something this skill can do.
3. Offer what is verified:
   - the host's **Authenticate** action in Settings → MCP servers, if the build
     offers it for this server;
   - reinstalling the plugin, which re-triggers the `ON_INSTALL` sign-in;
   - and, when the Microsoft window does appear, telling the user to choose
     **"다른 계정으로 로그인"** — the browser may hold an SSO session and would
     otherwise sign them straight back into the same account.
4. Confirm the new identity with the profile tool afterwards.

Account selection belongs to Microsoft and the Didim login service. Never remove
the marketplace, re-register the MCP URL, edit `config.toml`, or delete
credential files to force it.

## Case F — the sign-in window was closed or cancelled

Triggers: "아까 로그인 창 닫았는데 다시 연결해줘", "설치할 때 인증 취소했어".

Closing or cancelling the install-time sign-in leaves the plugin **installed**
and the server **registered** — registration and sign-in are separate things.
Verified: after an abandoned sign-in both survive and the sign-in can simply be
run again.

Say that plainly, since users assume they must remove and re-add the plugin,
then follow "Sign-in is needed".

## The standalone Codex CLI (separate context)

For a user working in a **standalone `codex` CLI** — their own terminal, their
own Codex home — these are the real commands:

```bash
codex mcp list --json      # this CLI's registry and auth_status
codex mcp login  didim-mcp # Microsoft OAuth sign-in for this CLI
codex mcp logout didim-mcp # clear this CLI's stored sign-in
```

There is no `codex mcp connect`, `reconnect`, or `enable`. Do not invent one.
`login` blocks until the browser callback completes and prints the authorize
URL; `logout` can exit non-zero when there was nothing stored to delete.

Offer these **only** when the user is asking about their own CLI, and label them
as such. They do not manage the Codex app's plugin sign-in, and they are not the
answer to "Didim MCP 연결해줘" inside the app.

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

Afterwards: fully quit Codex, start it again, and sign in when prompted.

The old timestamped `config.toml.backup-*` files still contain the retired key.
Mention that they can be deleted; do not open them.

## Error triage — these are not the same problem

| State | Evidence (from this session) | Action |
| --- | --- | --- |
| Signed in, working | tool call succeeds | Nothing to fix |
| Registered, not signed in | tool call returns 401 / `authentication_required` | "Sign-in is needed" |
| Session expired | worked earlier, auth errors now | Same as above; Codex refreshes on its own first |
| Legacy 0.1.x config shadowing | auth fails right after upgrading, or an old URL appears | Cleanup script, restart, sign in |
| One tool missing, others work | other Didim calls succeed | Portal entitlement — enable it in the Didim portal, restart Codex. **Not** auth |
| Tool authorization denied | tool exists, server refuses this user | The account lacks permission. Point at the portal/admin; do not re-authenticate |
| Provider credential failure | tool runs, upstream credential injection fails | Server-side Vault resource credential. Ask an admin. Never ask the user for a `serviceKey` |
| No Didim tools in this session | nothing exposed — even when `/mcp` shows `didim-mcp` as 사용함/인증됨 | Server unavailable to the session, usually a stored sign-in the server no longer accepts. See "No Didim tools at all". **Never** answer this with portal entitlement |
| Upstream API error | provider returned an error | Report the HTTP status and the safe error text |

## Hard rules

- **Never use a nested `codex` CLI result as evidence about the Codex app.**
  Different runtime, different user, different credential store.
- **Never run a CLI preflight before answering.** Call the tool.
- **Reinstalling is not a first-line fix.** It does re-trigger the install-time
  sign-in, so it is a legitimate last resort — say so when you offer it.
- Never point at a Connect/Disconnect button or gear for an installed
  plugin-provided MCP server; the tested Codex app UI does not expose them.
- Never claim a mechanism you have not verified. If the product cannot do it,
  say the product cannot do it.
- Never run the cleanup script without explicit approval.
- Never ask for, echo, log, or store any credential, token, or header value.
- Never register, rewrite, or repair the MCP server entry yourself.
