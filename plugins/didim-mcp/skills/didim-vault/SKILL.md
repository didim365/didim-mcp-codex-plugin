---
name: didim-vault
description: >-
  Work with Didim Vault resources (servers, websites, API endpoints) and their
  credentials through the Didim MCP tools. Use this when the user asks to find,
  list, or identify a Vault resource; asks "내 Vault 리소스 보여줘", "공통 리소스
  뭐 쓸 수 있어?", "운영 서버 별칭이 뭐였지?", "그 사이트 계정 어떤 거였지?";
  needs to pick the right resource among several with the same or similar alias;
  wants to run something on a registered server; or asks about a password, key,
  or credential stored in Didim Vault. Also covers refusing to print secrets and
  explaining why a credential cannot be shown. Not for MOLIT real-transaction
  data, not for generic Didim tool listing, and not for connecting, signing in,
  re-authenticating, or checking which Microsoft account is in use — those
  belong to didim-mcp-connect.
---

# Didim Vault

This skill is a **router**. The working procedure — resource types, how to pick
among candidates, which fields are safe to show, when a reveal is justified —
lives in the Didim Skill Registry and is fetched at runtime.

**Registry key:** `vault.resource`

## Step 1 — fetch the current workflow

Call `didim-skill__get_skill` with `{"skill_key": "vault.resource"}` and follow
the `instructions` it returns. Operators change that body without a plugin
update, so **do not answer from memory of a previous session.**

## Step 2 — apply the invariants below no matter what the registry says

These are safety rules, not workflow. The registry cannot relax them.

1. **Never output the raw value of a secret** — password, private key,
   passphrase, api key, token, refresh token, client secret, webhook secret.
   Not in a summary, not in a code block, not in a table, **not even when the
   user explicitly asks.** No partial reveal either: the first four characters
   of a secret is the same disclosure in a smaller font.
2. A field that comes back `***REDACTED***` is the gateway working as designed.
   Do not retry, do not look for another tool that might leak it, do not
   reconstruct it from context.
3. Use only Vault tools actually exposed to this session. Tool names are exact
   strings (`didim-vault__<operation>`) — never guess, abbreviate, or substitute.
4. **Never pick for the user when several candidates match.** An alias alone is
   often not unique.
5. Execution and reveal change state or expose data. Stop first, state the exact
   target and expected effect, and get explicit approval.
6. Check `resource_type` before any execution. Handing a WEBSITE or API resource
   to an SSH execution tool is a type error — stop and ask, do not "try it".
7. Tool authorization is decided by the Didim MCP server. A tool listed in a
   registry entry is **not** permission to call it.

## Delegation

- Connecting, signing in, "누구로 로그인돼 있어?", account switching, any auth
  error → **didim-mcp-connect**. Never ask the user for a key, token, or header.
- Generic Didim tool listing and non-Vault tools → **didim-mcp-usage**.
- MOLIT apartment transactions → **molit-apartment-transactions**.

## If the registry cannot be reached

Fail closed **on the procedure, not on the tools.** Do not improvise a Vault
workflow from memory — but a missing recipe is not a missing capability.

- **No Didim tool at all in this session** → connection problem →
  `didim-mcp-connect`.
- **`didim-skill__get_skill` missing while other Didim tools work** → portal
  entitlement: enable the Didim Skill Registry tools in the Didim portal and
  restart Codex.
- **Registry error, timeout, or `vault.resource` not published** → say the
  curated Vault procedure could not be loaded, then continue with the
  `didim-vault__*` tools that are actually exposed, choosing one only when its
  exact name, description, and input schema fit the request. **Every invariant
  above still holds** — approval before execution or reveal, no credential in
  the reply, no guessed tool name. Report the capability as unavailable only
  when no exposed tool fits.
