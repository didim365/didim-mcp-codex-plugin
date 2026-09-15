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
  Didim — if no published Didim skill matches, this skill does not invent a
  procedure; it falls back to using the Didim MCP tools that are actually
  exposed. Authentication and sign-in problems belong to didim-mcp-connect.
---

# Didim Dynamic Skill (registry router)

This skill exists because Codex selects skills from the static frontmatter
above, but Didim's **working procedures live in the Skill Registry database**
and are published by operators without a plugin release. The four dedicated
skills cover the procedures that existed when the plugin shipped. This one
covers everything published **since**.

It has no workflow of its own. It finds one.

## Skill and tool are different things

| | What it is | Without it |
| --- | --- | --- |
| **MCP tool** | The executable capability — an exact name, a description, an input schema, a server-side policy | The request genuinely cannot be carried out |
| **Runtime skill** | An optional recipe *on top of* tools: which tools, in what order, under what rules | The work still runs, just without curated guidance |

`Skill = how to use tools. Tool = what can be executed.`

A missing runtime skill is **not** an execution failure. The registry decides
how well a request is handled, never whether it can be handled at all.

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

- **One clear match** → use it. A curated recipe always beats improvising, so
  do not skip it in favour of picking tools yourself.
- **Several plausible matches** → show the user the candidate names and short
  descriptions and ask which one. Do not pick silently.
- **No match** → go to **Step 3b**. Do not stop, and do not invent a Didim
  procedure to stand in for the missing one.

Never invent a `skill_key`. A key that is not in the list does not exist.

## Step 3 — fetch and follow it

Call `didim-skill__get_skill` with the chosen `{"skill_key": "..."}` and follow
the `instructions` it returns. That body is the published, operator-maintained
procedure; it changes without a plugin update, so **do not answer from memory
of a previous session.**

## Step 3b — no matching runtime skill: use the tools directly

Nothing in the registry matched. That means there is **no recipe**, not that
there is **no capability**. Continue the user's request in normal MCP tool mode:

1. Do not invent a Didim skill, workflow, or procedure, and do not answer from a
   remembered older version of one.
2. Do not stop merely because the registry had no match — that is not a failure.
3. Look at the Didim MCP tools actually exposed to this session.
4. Pick a tool only when its **exact name, description, and input schema**
   clearly support what the user asked. Judge from those fields, not from the
   tool's name alone.
5. Build the arguments only from the user's request, the conversation, the
   **actual current date/time** when a date is involved, and the documented
   input schema. Respect `required`, types, `enum`, and min/max. Never add an
   argument the schema does not define.
6. Call the tool, then answer from its real response.
7. Only when **no exposed tool fits** do you report that the capability is
   unavailable — and say it is the tool that is missing, not the skill.

Everything in Step 4 still applies. A missing recipe relaxes nothing.

Worked example — the user asks "didim mcp 작년 연차 조회", the registry has no
leave-related skill, and `didim-gw__get_my_holiday_info` is exposed with a
required integer `year`. Resolve 작년 against today's date, call that tool once
with that year, and answer from the response. Refusing because no skill is
registered would be wrong.

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
6. If a required tool is unavailable, state that limitation — **the missing
   tool is the only reason to stop.** Do not invent a tool name, an alternate
   endpoint, or any other unauthorized workaround, and never substitute a
   differently named tool for the one a recipe asked for.
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

Fail closed **on the procedure, not on the tools.** Never reconstruct a Didim
workflow from memory. But a registry that is down says nothing about whether the
other Didim tools work, so judge those separately.

- **No Didim tool at all in this session** → the server is unavailable to this
  session. Delegate to `didim-mcp-connect`. Never run `codex mcp list` as a
  preflight; a nested `codex` command runs in a different runtime from the
  Codex app.
- **`didim-skill__list_skills` missing while other Didim tools work** → portal
  entitlement. The user enables `Didim Skill Registry` tools in the Didim portal
  and restarts Codex. Meanwhile the request can still proceed in Step 3b mode.
- **The registry tool errors (5xx), times out, or the list comes back empty** →
  recipe lookup is unavailable, which is not the same as the work being
  impossible. Say the curated procedure could not be loaded, then continue in
  **Step 3b** with the tools that are exposed. An empty catalogue is a normal
  state: it means no recipes are published, not that no tools exist.
- **The registry tool returns 401/403 while other Didim tools work** → that is a
  Skill Registry entitlement/authorization problem, not a session-wide auth
  failure. Continue in Step 3b. If **every** Didim tool returns 401/403, treat it
  as an authentication problem and delegate to `didim-mcp-connect`.

Never work around a failing registry by bypassing credentials, guessing at tools
that are not exposed, or relaxing any rule in Step 4.
