---
name: didim-mcp-connect
description: >-
  Connecting, reconnecting, and troubleshooting the Didim MCP server in Codex.
  Didim MCP uses Microsoft (Entra) sign-in through Codex's own OAuth Connect —
  there is no API key. Use this when the user wants to connect, sign in to,
  reconnect, disconnect, or re-authorize Didim MCP; asks how to set it up or log
  in; is upgrading from an older plugin version that used a personal API key; or
  reports that Didim MCP does not appear under /mcp, its tools are not loading,
  authentication or the OAuth login failed, the connection expired, Connect does
  nothing, or they see "No Didim MCP tools are exposed in this session."
  Korean triggers: "Didim MCP 연결해줘", "Didim MCP 설정해줘", "Didim MCP 로그인",
  "Didim MCP 인증해줘", "Didim MCP 재연결", "Didim MCP 다시 인증",
  "Didim MCP 연결 끊고 다시 연결", "Microsoft 계정으로 Didim MCP 연결",
  "Didim MCP가 /mcp에 안 보여", "Didim MCP 인증이 실패해",
  "예전 API Key 설정이 남아 있어", "Didim MCP 업그레이드 후 연결이 안 돼".
  English triggers: "connect Didim MCP", "sign in to Didim MCP",
  "reconnect Didim MCP", "Didim MCP OAuth failed", "Didim MCP tools missing",
  "migrate Didim MCP from API key to OAuth".
---

# Didim MCP Connect

Didim MCP is **OAuth-only**. The plugin declares the hosted MCP server in its
manifest, and Codex's own MCP OAuth client performs the sign-in. Nothing in this
flow involves an API key, a bearer token, or an auth header.

**Never** ask the user for an API key, a `dv_` key, an access token, a refresh
token, a header value, or an MCP URL. Never edit `~/.codex/config.toml` yourself.
Never build a Microsoft or Didim authorization URL by hand.

## What the user actually does

1. Install **Didim MCP** from the Didim marketplace in the Codex plugin screen.
2. Press **Connect** on the plugin (Codex may offer it right after install).
3. A browser opens: sign in with the **Microsoft account**, then approve the
   Didim consent screen.
4. Codex stores the connection. Tools appear under `/mcp` as `didim-mcp`.

Codex handles discovery, PKCE, the loopback callback, and token refresh. There is
nothing for the user to copy or paste.

## Connect is not visible / the server is missing

Check in this order:

1. Is the plugin installed and enabled in the Codex plugin screen?
2. Was Codex restarted after installing or updating the plugin? A plugin-provided
   MCP server is picked up on a fresh start (and a new thread).
3. **Legacy config from plugin 0.1.x** — see below. This is the most common cause
   after an upgrade.

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

## Disconnect / reconnect

Use the plugin's own Disconnect, then Connect again — Codex clears and re-runs
the OAuth flow. If the user wants to sign in as a different Microsoft account,
they may have to choose "다른 계정으로 로그인" on the Microsoft sign-in page;
account selection is controlled by the Didim login service, not by this plugin.

## After connecting

Tell the user to run `/mcp` and confirm `didim-mcp` is connected. Didim exposes
only the tools that user enabled in the Didim portal, so a missing tool means
"enable it in the portal, then restart Codex" — not an authentication problem.

## Hard rules

- Never run the cleanup script without explicit approval.
- Never ask for, echo, log, or store any credential, token, or header value.
- Never register, rewrite, or repair the MCP server entry yourself. If the
  plugin-provided server is missing, the fix is reinstall + restart, not a
  hand-written config.
