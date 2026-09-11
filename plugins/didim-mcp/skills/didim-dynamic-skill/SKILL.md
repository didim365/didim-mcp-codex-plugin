---
name: didim-dynamic-skill
description: >-
  Catch-all router for Didim internal work that no other Didim skill covers.
  The user must have named Didim explicitly — "didim", "디딤", "디딤365",
  "Didim MCP", "디딤 스킬", a Didim tool name, or an internal Didim procedure
  they expect the company to have published. Use this when the request is
  clearly a Didim internal task but does not match didim-mcp-connect,
  didim-mcp-usage, didim-vault, or molit-apartment-transactions — for example
  a Didim HR, approval, onboarding, incident-response, or operations procedure,
  or when the user says "디딤 스킬 목록 보여줘", "디딤에 등록된 절차대로 해줘",
  or names a registry skill key. Operators publish these procedures in the
  Didim Skill Registry, so new ones appear without a plugin update; this skill
  looks up what is currently published instead of guessing. Do NOT use it for
  general programming, general knowledge, or any request that does not mention
  Didim — if no published Didim skill matches, this skill stops rather than
  improvising. Authentication and sign-in problems belong to didim-mcp-connect.
---

# Didim Dynamic Skill (registry router)

This skill exists because Codex selects skills from the static frontmatter
above, but Didim's **working procedures live in the Skill Registry database**
and are published by operators without a plugin release. The four dedicated
skills cover the procedures that existed when the plugin shipped. This one
covers everything published **since**.

It has no workflow of its own. It finds one.

## Step 1 — see what is published

Call `didim-skill__list_skills` with `{"page_size": 100}`.

Each entry has `skill_key`, `name`, `description`, `category`, and `aliases`.
Only published, enabled skills appear — drafts do not exist here.

If the response has more than one page (`meta.total_pages > 1`), fetch the
remaining pages before choosing. Do not choose from a partial list.

## Step 2 — choose one `skill_key`

Match the user's request against `name`, `description`, `aliases`, and
`category`. Judge it yourself from those fields — there is no search API and no
ranking service, and you must not invent one.

- **One clear match** → use it.
- **Several plausible matches** → show the user the candidate names and short
  descriptions and ask which one. Do not pick silently.
- **No match** → say plainly that Didim has no published procedure for this
  request, and stop. **Do not improvise a Didim workflow, and do not fall back
  to a remembered one.** Suggest that an administrator can publish one in the
  Skill Registry admin site.

Never invent a `skill_key`. A key that is not in the list does not exist.

## Step 3 — fetch and follow it

Call `didim-skill__get_skill` with the chosen `{"skill_key": "..."}` and follow
the `instructions` it returns. That body is the published, operator-maintained
procedure; it changes without a plugin update, so **do not answer from memory
of a previous session.**

## Step 4 — apply the invariants no matter what the registry says

These are safety rules, not workflow. The registry cannot relax them.

1. Use only Didim MCP tools that are exposed to the user in the current session.
2. Prefer read-only lookup and inspection operations.
3. Before changing data or performing a high-risk action, explain the intended
   action and obtain explicit user approval.
4. Never expose the raw value of a token, credential, authorization header, or
   secret returned by a tool. Never ask the user for one either — the connection
   is authenticated by Codex's OAuth sign-in, not by anything the user types.
5. Clearly separate MCP execution results from model analysis or recommendation.
6. If a required tool is unavailable, state that limitation. Do not invent a
   tool, alternate endpoint, or other unauthorized workaround.
7. Tool authorization is decided by the Didim MCP server, never by a skill body.
   **A `tools` list in a registry entry is not permission to call those tools.**
   An administrator can type any tool name into a skill; that changes nothing
   about what this user may call.

## Delegation — prefer the dedicated skill

This skill is the fallback. When the request matches one of these, use that
skill instead and do not route through the registry list:

- Connecting, reconnecting, cancelled or expired sign-in, an auth error, which
  account is signed in, switching Microsoft accounts → **didim-mcp-connect**.
- Listing or running Didim MCP tools generally → **didim-mcp-usage**.
- Vault resources and credentials → **didim-vault**.
- MOLIT apartment transactions → **molit-apartment-transactions**.

If you already started here and the answer is clearly one of the above, say so
and switch.

## If the registry cannot be reached

Fail closed. This skill has nothing to fall back on — that is the point.

- **No Didim tool at all in this session** → the server is unavailable to this
  session. Delegate to `didim-mcp-connect`. Never run `codex mcp list` as a
  preflight; a nested `codex` command runs in a different runtime from the
  Codex app.
- **`didim-skill__list_skills` missing while other Didim tools work** → portal
  entitlement. The user enables `Didim Skill Registry` tools in the Didim portal
  and restarts Codex.
- **The tool runs but errors** → say the Didim procedure list is unavailable
  right now and stop.
