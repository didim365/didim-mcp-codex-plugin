---
name: didim-mcp-usage
description: >-
  Use the Didim MCP server safely for user-requested work once it is configured.
  Use this when the user asks to list or use Didim MCP tools; query available
  Didim servers, APIs, or resources; check AIOps status; inspect server status,
  logs, ports, or service health via Didim; perform a task with a Didim resource
  or MCP tool; or says things like "didim-mcp로 확인해줘" or names a specific
  Didim tool. Prioritizes read-only lookups and requires approval before changes
  or high-risk actions. If Didim MCP is not exposed under /mcp, defer to the
  didim-mcp-connect skill instead of retrying blindly.
---

# Didim MCP Usage

Use this skill when a request calls for the Didim MCP server or one of its
exposed tools, and the server is already connected.

For MOLIT apartment trade or rent (전월세) real-transaction queries by district
name and contract month, prefer the `molit-apartment-transactions` skill.

## If Didim MCP is not available

If `didim-mcp` is not present under `/mcp`, or its tools are not exposed in the
current session:

- Do **not** repeatedly retry the same failing call or invent a fallback.
- Tell the user the server/tools are not currently exposed and point them to the
  **didim-mcp-connect** skill (e.g. suggest they say "Didim MCP 연결해줘"). Didim
  MCP signs in with a Microsoft account through the plugin's Connect action;
  never ask for an API key, token, or auth header.

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
