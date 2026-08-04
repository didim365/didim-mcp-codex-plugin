# Didim MCP (Codex Plugin)

This plugin connects Codex to the Didim MCP server. It **does not register an MCP
server by itself.** Instead it ships:

- **Skills** — `didim-mcp-setup` (first-time setup & troubleshooting),
  `didim-mcp-usage` (safe usage), and `molit-apartment-transactions` (MOLIT
  apartment trade/rent real-transaction queries by district name + month).
- **Scripts** — `scripts/setup-didim-mcp.ps1` / `.cmd` and
  `scripts/remove-didim-mcp.ps1` / `.cmd`.

For full installation, setup, update, and removal instructions, see the
[repository root README](../../README.md).

## Setup (Windows)

Ask Codex in a new chat:

```
Didim MCP 설정해줘
```

The `didim-mcp-setup` skill explains what happens and, after your approval, runs
the setup script. You enter your personal `dv_...` API key in a **hidden
PowerShell prompt** (never in chat). The script writes this block into your
`~/.codex/config.toml`, preserving all other settings:

```toml
[mcp_servers.didim-mcp]
url = "http://49.50.138.22:31083/mcp/"
startup_timeout_sec = 120

[mcp_servers.didim-mcp.http_headers]
X-Didim-Vault-Api-Key = "<your dv_ key>"
```

Manual run (if the skill cannot launch it):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\setup-didim-mcp.ps1"
```

The config is saved regardless of process state. To reload it you must fully
restart Codex — the plugin cannot reload live. When run in a **separate `.cmd`
window**, the script offers to close exact-match `codex` processes (`[y/N]`,
default No). When run **inside Codex**, it will not close the app itself and asks
you to quit all Codex windows manually. It never closes its own process or
ancestors. Default match is the exact ProcessName `codex` (no substring, no
`gpt`). Options: `-SkipProcessKill`, `-KillWithoutConfirmation`, `-ProcessNames`.

Then fully restart the Codex app and run `/mcp` to confirm `didim-mcp` and its tools.

## Change / rotate the API key

Ask Codex `Didim MCP API Key 변경해줘` (or "change/rotate Didim MCP key"). This
re-runs the **same** setup script — no reinstall, no remove first. It auto-detects
the existing `[mcp_servers.didim-mcp]` block, backs up `config.toml`, and replaces
only the key. Enter the new `dv_` key in the hidden prompt. If you cancel or the
key is invalid, the existing config is left unchanged. Restart Codex to apply.

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
· 국토교통부 아파트 전월세 실거래가 조회 (rent).

## Remove

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\remove-didim-mcp.ps1"
```

Removes only the `[mcp_servers.didim-mcp]` block (a timestamped backup is created
first). Other MCP servers and settings are preserved. By default it does **not**
touch any process (no prompt); pass `-KillCodexProcesses` to opt into closing
exact-match `codex` processes. Restart Codex manually to apply.

## Safety

- Read-only operations first; approval required before changes or high-risk actions.
- API keys, tokens, and credentials are never echoed or logged.
- The real API key is never stored in this repository — only in your local
  `config.toml`.
- MCP execution results are kept distinct from model analysis.
