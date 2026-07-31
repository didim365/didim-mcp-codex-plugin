# Didim MCP (Codex Plugin)

This plugin connects Codex to the Didim MCP server. It **does not register an MCP
server by itself.** Instead it ships:

- **Skills** — `didim-mcp-setup` (first-time setup & troubleshooting) and
  `didim-mcp-usage` (safe usage).
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

Then fully restart Codex and run `/mcp` to confirm `didim-mcp` and its tools.

## Remove

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\remove-didim-mcp.ps1"
```

Removes only the `[mcp_servers.didim-mcp]` block (a timestamped backup is created
first). Other MCP servers and settings are preserved.

## Safety

- Read-only operations first; approval required before changes or high-risk actions.
- API keys, tokens, and credentials are never echoed or logged.
- The real API key is never stored in this repository — only in your local
  `config.toml`.
- MCP execution results are kept distinct from model analysis.
