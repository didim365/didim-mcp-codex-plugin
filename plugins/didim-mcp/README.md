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

## Connect

Install the plugin, press **Connect**, sign in with your Microsoft account, then
restart Codex and run `/mcp` to confirm `didim-mcp`.

If Connect is not offered, ask Codex in a new chat:

```
Didim MCP 연결해줘
```

The `didim-mcp-connect` skill diagnoses the cause and walks through the fix.

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
into closing exact-match `codex` processes. Restart Codex, then press Connect.

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

## Remove

Remove the plugin from the Codex plugin screen. The MCP server goes with it —
there is no `config.toml` entry to clean up. To drop the stored OAuth
credentials, use **Disconnect** (or `codex mcp logout didim-mcp`).

## Safety

- Read-only operations first; approval required before changes or high-risk actions.
- The plugin never asks for, stores, or transmits a user credential. Tokens are
  held by Codex; skills and the model never read or print them.
- Tokens, credentials, and auth headers returned by a tool are never echoed.
- The MCP endpoint is HTTPS.
- MCP execution results are kept distinct from model analysis.
