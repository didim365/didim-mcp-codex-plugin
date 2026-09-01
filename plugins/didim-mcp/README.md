# Didim MCP (Codex Plugin)

This plugin connects Codex to the hosted Didim MCP server using **OAuth only**.

- The plugin manifest declares the MCP server (`mcpServers` in
  `.codex-plugin/plugin.json`), so installing the plugin registers it.
- **Codex** performs the sign-in through its built-in MCP OAuth client:
  Microsoft (Entra) login → Didim consent → tokens stored by Codex.
- There is **no API key**. Nothing is typed, pasted, or written to
  `~/.codex/config.toml` by this plugin.

```
url: https://didimmcp-dev.didimservice.com/mcp   (Streamable HTTP)
auth: OAuth 2.1 — discovered from the server, run by Codex
```

It also ships:

- **Skills** — `didim-mcp-connect` (connect, reconnect, upgrade, troubleshooting),
  `didim-mcp-usage` (safe usage), and `molit-apartment-transactions` (MOLIT
  apartment trade/rent real-transaction queries by district name + month).
- **Scripts** — `scripts/migrate-didim-mcp.ps1` / `.cmd`, for users upgrading
  from 0.1.x.

For full installation, connection, update, and removal instructions, see the
[repository root README](../../README.md).

## Sign in

Installing the plugin opens the Microsoft sign-in. Complete it, restart Codex,
and run `/mcp` to confirm `didim-mcp`.

To sign in later, or again:

```bash
codex mcp list --json        # auth_status (read-only)
codex mcp login  didim-mcp   # sign in / re-authenticate
codex mcp logout didim-mcp   # sign out (run before login to switch accounts)
```

**In the Codex App UI as tested, an installed plugin-provided MCP server has no
Connect button, Disconnect button, gear, or toggle.** The install-time sign-in
is real; everything after it goes through the commands above. A future Codex
release may add such controls.

Or just ask Codex in a new chat:

```
Didim MCP 연결해줘
```

The `didim-mcp-connect` skill checks the actual state and walks through the fix.

### Closed the sign-in window? Do not reinstall

Installing opens the Microsoft sign-in. Closing or cancelling it leaves the
plugin installed and the MCP server registered — registration and sign-in are
separate. Just start the sign-in again with `codex mcp login didim-mcp`, or ask
in a new chat.

### Account management, in natural language

| Intent | Say |
| --- | --- |
| Retry an abandoned sign-in | `아까 로그인 창 닫았는데 다시 로그인해줘` |
| Check the signed-in account | `지금 Didim MCP 누구로 로그인돼있어?` |
| Switch Microsoft account | `Didim MCP 다른 Microsoft 계정으로 로그인해줘` |
| Re-authenticate after expiry | `Didim MCP 다시 인증해줘` |

The skill checks `auth_status` first, then explains and asks for approval
before running `login` or `logout`, since both change authentication state. If
it cannot run commands in your environment it hands you the exact command
instead. Skill auto-selection depends on phrasing and is not guaranteed — the
commands above always work directly.

Two behaviours worth knowing: `codex mcp login` **blocks** until you finish in
the browser (and prints the URL if the browser does not open), and
`codex mcp logout` can exit non-zero when there was nothing stored to remove —
check `codex mcp list --json` for the real state.

## Upgrading from 0.1.x — required once

Plugin 0.1.x wrote `[mcp_servers.didim-mcp]` (with an `X-Didim-Vault-Api-Key`
header) into the user's `config.toml`. That block **shadows** the
plugin-provided server, so Codex keeps using the old entry and OAuth never runs.
Didim no longer accepts user API keys, so every call fails.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\migrate-didim-mcp.ps1"
```

It takes a timestamped backup, removes only the `[mcp_servers.didim-mcp]` and
`[mcp_servers.didim-mcp.*]` tables (other MCP servers and settings keep their
content and order), and writes UTF-8 without BOM. It never reads back, compares,
prints, or logs the old key — only `legacy credential removed`. It is idempotent:
if there is no legacy block it changes nothing.

By default it does **not** touch any process; pass `-KillCodexProcesses` to opt
into closing exact-match `codex` processes. Restart Codex, then run
`codex mcp login didim-mcp`.

Users with the standalone `codex` CLI can run `codex mcp remove didim-mcp`
instead.

## Apartment real-transaction queries (MOLIT)

Ask by district name + natural-language month; no `LAWD_CD`, `DEAL_YMD`, 10-digit
legal-dong code, or `serviceKey` needed. The `molit-apartment-transactions` skill
resolves the code via `odcloud__get_legal_dong_codes`, derives `LAWD_CD` (first 5
digits) and `DEAL_YMD` (`YYYYMM`), and calls the trade or rent tool.

```
구로구 작년 7월 아파트 매매 실거래가 알려줘
구로구 작년 7월 아파트 전월세 실거래가 알려줘
서울 중구 2025년 7월 전세 거래 조회해줘
마포구 지난달 월세 거래 알려줘
종로구 작년 12월 매매와 전월세를 모두 비교해줘
```

Enable the matching tools in the Didim user portal, then restart Codex:
국토교통부 법정동코드 조회 (always) · 국토교통부 아파트 매매 실거래가 조회 (trade)
· 국토교통부 아파트 전월세 실거래가 조회 (rent). Upstream provider credentials are
injected server-side from your OAuth identity.

## Tools are dynamic

The plugin does not ship a tool catalog. On every connection the MCP server
returns, via `tools/list`, only the tools the signed-in user has enabled in the
Didim portal. The set differs per user and changes without a plugin update.

## Provider credentials are not the removed API key

Two different things:

- **User login credential** — the old `dv_` Didim API key. **Removed**, replaced
  by Microsoft OAuth.
- **Vault resource credentials** — public-data `serviceKey`, SSH credentials,
  third-party API credentials. **Still in use.** Held in Didim Vault, injected
  server-side after the server authorizes the OAuth identity. Never entered by
  the user, never seen by Codex or the skills.

## Direct MCP (development / UAT only)

Registering `https://didimmcp-dev.didimservice.com/mcp` directly in Codex runs
the same OAuth flow, but that is an auxiliary path for server development.
**Disable any direct registration before running plugin UAT** — with both active
you cannot tell which one served a request.

## Remove

Remove the plugin from the Codex plugin screen. The MCP server goes with it —
there is no `config.toml` entry to clean up. To drop the stored OAuth
credentials, run `codex mcp logout didim-mcp`.

## Safety

- Read-only operations first; approval required before changes or high-risk actions.
- The plugin never asks for, stores, or transmits a user credential. Tokens are
  held by Codex; skills and the model never read or print them.
- Tokens, credentials, and auth headers returned by a tool are never echoed.
- The MCP endpoint is HTTPS.
- MCP execution results are kept distinct from model analysis.
