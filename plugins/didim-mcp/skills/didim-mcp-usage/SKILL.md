---
name: didim-mcp-usage
description: >-
  Use the Didim MCP server safely for user-requested work once it is configured.
  Use this when the user asks to list or use Didim MCP tools; query available
  Didim servers, APIs, or resources; check AIOps status; inspect server status,
  logs, ports, or service health via Didim; perform a task with a Didim resource
  or MCP tool; or says things like "didim-mcp로 확인해줘" or names a specific
  Didim tool. Prioritizes read-only lookups and requires approval before changes
  or high-risk actions. This skill does not handle authentication: connecting,
  reconnecting, sign-in failures, checking the currently signed-in account, and
  switching Microsoft accounts all belong to the didim-mcp-connect skill.
---

# Didim MCP Usage

Use this skill when a request calls for the Didim MCP server or one of its
exposed tools, and the server is already connected.

For MOLIT apartment trade or rent (전월세) real-transaction queries by district
name and contract month, prefer the `molit-apartment-transactions` skill.

## Authentication is not this skill's job

Delegate to **didim-mcp-connect** — do not handle it here — whenever the request
is about connecting, reconnecting, a cancelled or expired sign-in, an auth
error, which account is currently signed in, or switching Microsoft accounts.
Suggest the user say "Didim MCP 연결해줘". Never ask for an API key, token, or
auth header, and never run a login/logout command from this skill.

## The current session is the source of truth

The tools exposed to this session tell you what is available. Answer "내가 쓸 수
있는 Didim MCP 도구를 보여줘" from that registry.

Never run `codex mcp list` or `codex plugin list` as a preflight, and never
conclude from an empty CLI listing that Didim MCP is unavailable. A nested
`codex` command runs in a different runtime from the Codex app — verified: the
app runs shell commands as a separate sandbox OS user with its own Codex home —
so it can report zero servers while this session has Didim tools working.

## If Didim MCP is not available

If no Didim tools are exposed in the current session, or a needed tool is
missing:

- Do **not** repeatedly retry the same failing call or invent a fallback.
- Count first. **No Didim tool at all** means the server is unavailable to this
  session — delegate to `didim-mcp-connect`. Do not tell the user to enable
  tools in the portal, and do not treat `/mcp` showing 인증됨 as proof that the
  connection works.
- **A single missing tool while other Didim tools work** is the portal
  entitlement case: the user enables it in the Didim portal and restarts Codex.

## Rules

1. Use only Didim MCP tools that are exposed to the user in the current session.
2. Prefer read-only lookup and inspection operations.
3. Before changing data or performing a high-risk action, explain the intended
   action and obtain explicit user approval.
4. Never expose the raw value of a token, credential, authorization header, or
   secret returned by a tool. Never ask the user for one either — the connection
   is authenticated by Codex's OAuth sign-in, not by anything the user types.
5. Clearly separate MCP execution results from model analysis, inference, or
   recommendation.
6. If a required tool is unavailable, state that limitation. Do not invent a
   tool, alternate endpoint, or other unauthorized workaround, and do not guess
   at tools that are not exposed.
7. Keep tool inputs scoped to the user's request and minimize sensitive data
   sent to the server.

## Response Pattern

- **MCP result:** Report the relevant facts returned by the exposed tool.
- **Analysis:** Provide interpretation or recommendations separately, and
  identify any inference.

For a proposed write or high-risk operation, stop before execution and ask for
approval with the exact target and expected effect.
