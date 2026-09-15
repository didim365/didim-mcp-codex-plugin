---
name: didim-mcp-usage
description: >-
  Use the Didim MCP server safely for user-requested work once it is configured.
  Use this when the user asks to list or use Didim MCP tools; query available
  Didim servers, APIs, or resources; check AIOps status; inspect server status,
  logs, ports, or service health via Didim; perform a task with a Didim resource
  or MCP tool; or says things like "didim-mcp로 확인해줘" or names a specific
  Didim tool. Prioritizes read-only lookups and requires approval before changes
  or high-risk actions. Vault resource lookup and credential handling belong to
  the didim-vault skill. This skill does not handle authentication: connecting,
  reconnecting, sign-in failures, checking the currently signed-in account, and
  switching Microsoft accounts all belong to the didim-mcp-connect skill.
---

# Didim MCP Usage

This skill is a **router**. The working procedure lives in the Didim Skill
Registry and is fetched at runtime, not written here.

**Registry key:** `mcp.usage`

## Step 1 — fetch the current workflow

Call `didim-skill__get_skill` with `{"skill_key": "mcp.usage"}` and follow the
`instructions` it returns. That body is the published, operator-maintained
procedure; it changes without a plugin update, so **do not answer from memory
of a previous session.**

If `didim-skill__get_skill` is not exposed to this session, `didim-skill__list_skills`
shows what the registry has. Both are ordinary Didim MCP tools — the same portal
entitlement rules apply.

## Step 2 — apply the invariants below no matter what the registry says

These are safety rules, not workflow. The registry cannot relax them.

1. Use only Didim MCP tools that are exposed to the user in the current session.
2. Prefer read-only lookup and inspection operations.
3. Before changing data or performing a high-risk action, explain the intended
   action and obtain explicit user approval.
4. Never expose the raw value of a token, credential, authorization header, or
   secret returned by a tool. Never ask the user for one either — the connection
   is authenticated by Codex's OAuth sign-in, not by anything the user types.
5. Clearly separate MCP execution results from model analysis or recommendation.
6. If a required tool is unavailable, state that limitation — **the missing
   tool is the only reason to stop.** Do not invent a tool, alternate endpoint,
   or other unauthorized workaround.
7. Tool authorization is decided by the Didim MCP server, never by a skill body.
   A tool listed in a registry entry is **not** permission to call it.

## Delegation

- Connecting, reconnecting, cancelled or expired sign-in, an auth error, which
  account is signed in, switching Microsoft accounts → **didim-mcp-connect**.
  Suggest the user say "Didim MCP 연결해줘". Never ask for an API key or token.
- Vault resources and credentials → **didim-vault**.
- MOLIT apartment transactions → **molit-apartment-transactions**.

## The current session is the source of truth

The tools exposed to this session tell you what is available. Answer "내가 쓸 수
있는 Didim MCP 도구를 보여줘" from that registry — **that question is about MCP
tools and does not need the Skill Registry at all.**

Never run `codex mcp list` or `codex plugin list` as a preflight, and never
conclude from an empty CLI listing that Didim MCP is unavailable. A nested
`codex` command runs in a different runtime from the Codex app.

## If the registry cannot be reached

Fail closed **on the procedure, not on the tools.** Do **not** improvise a
workflow or fall back to a remembered older version of this skill. The registry
supplies the *recipe*; the Didim MCP tools exposed to this session supply the
*capability*, and those are independent.

- **No Didim tool at all in this session** → the server is unavailable to this
  session. Delegate to `didim-mcp-connect`. Do not call it a portal entitlement
  problem, and do not treat `/mcp` showing 인증됨 as proof the connection works.
- **`didim-skill__get_skill` missing while other Didim tools work** → portal
  entitlement. The user enables `Didim Skill Registry` tools in the Didim portal
  and restarts Codex.
- **The tool runs but returns an error, times out, or `mcp.usage` is not
  published** → say the curated procedure could not be loaded, then **carry on
  with the user's request using the exposed Didim tools under the invariants
  above.** A missing recipe is not a missing capability: pick a tool only when
  its exact name, description, and input schema fit the request, build arguments
  only from the schema and the user's words, and report the capability as
  unavailable only when no exposed tool fits.
