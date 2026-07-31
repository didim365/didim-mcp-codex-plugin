---
name: didim-mcp-setup
description: >-
  First-time setup and troubleshooting for connecting the Didim MCP server in
  Codex on Windows. Use this when the user wants to set up, configure, connect,
  reconfigure, or re-register Didim MCP; register, change, or update their
  personal dv_ API key; or reports that Didim MCP does not appear under /mcp,
  its tools are not loading, or they see "No Didim MCP tools are exposed in this
  session." Triggers include phrases like "Didim MCP 설정해줘", "Didim MCP API
  Key 등록해줘", "dv_ 키를 등록해줘", "Didim MCP가 /mcp에 안 보여", "Didim MCP
  도구가 로드되지 않아", "Didim MCP 초기 설정", "Didim MCP 재설정", and
  "Didim MCP 키 변경".
---

# Didim MCP Setup

Guide the user through configuring the Didim MCP server for their own machine by
running the bundled setup script. This plugin does **not** register an MCP server
by itself — the setup script writes the connection and the user's personal API
key into their `~/.codex/config.toml`.

## Preconditions

1. Confirm the operating system is **Windows**. The setup script is PowerShell
   (`.ps1`) with a `.cmd` launcher and targets `%USERPROFILE%\.codex\config.toml`.
   If the user is on macOS or Linux, explain that the script is Windows-only and
   offer the manual `config.toml` steps in the plugin README instead.
2. Locate the bundled script. It ships inside this plugin at
   `scripts/setup-didim-mcp.ps1` (with `scripts/setup-didim-mcp.cmd`). Because the
   plugin is installed under the Codex plugin cache, the concrete path is:
   `%USERPROFILE%\.codex\plugins\cache\didim\didim-mcp\<version>\scripts\`.
   If the exact path is uncertain, find `setup-didim-mcp.cmd` under
   `%USERPROFILE%\.codex\plugins\cache\` and use that folder.

## Explain before running (get approval first)

Briefly tell the user, then ask for explicit approval before doing anything:

- They will enter their personal Didim Vault API key (`dv_...`) in a **separate
  PowerShell window using hidden input** — not in this chat.
- The script **backs up** `config.toml` (timestamped) and then **modifies** it,
  adding/replacing only the `[mcp_servers.didim-mcp]` block. Other settings are
  preserved.
- The key is stored **in plaintext inside `config.toml` on this PC** — the same
  security level as configuring an MCP header manually. It is not sent to this
  chat and not committed anywhere.

## Run (only after the user approves)

- Preferred: run the launcher so input works in its own console window:
  - `%USERPROFILE%\.codex\plugins\cache\didim\didim-mcp\<version>\scripts\setup-didim-mcp.cmd`
  - or: `powershell -NoProfile -ExecutionPolicy Bypass -File "<...>\scripts\setup-didim-mcp.ps1"`
- If you cannot launch an interactive process, or hidden-input prompting is not
  possible from the current shell, do **not** try to collect the key yourself.
  Give the user the exact `.cmd` path and ask them to double-click it (or paste
  the `powershell ... -File` command into a Windows terminal) and enter the key
  there.

## Hard rules

- Never run the script without the user's explicit approval.
- Never ask the user to paste their API key into this chat.
- Never pass the API key as a command-line argument. It is collected only via the
  script's hidden PowerShell prompt (`Read-Host -AsSecureString`).
- Never read back, echo, log, or repeat the API key value.

## After setup

Tell the user to:

1. Fully quit every Codex window/session.
2. Start Codex again.
3. Run `/mcp` and confirm `didim-mcp` and its tools are listed.

If tools still do not appear, have them re-run setup (verify the `dv_` key is
current), or run `remove-didim-mcp.cmd` and set up again.
