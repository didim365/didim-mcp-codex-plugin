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

Didim Vault holds registered access targets (**resources**) and their
credentials. This skill is about picking the right resource and using its
credential safely — always through the Didim MCP tools, never through a direct
REST call.

## Boundaries

- Connecting, signing in, re-authenticating, "누구로 로그인돼 있어?", account
  switching, and every auth error → **didim-mcp-connect**. Never handle those
  here, and never ask the user for a key, token, or header.
- Generic "what Didim tools can I use" listing and non-Vault tools →
  **didim-mcp-usage**.
- MOLIT apartment transactions → **molit-apartment-transactions**.

## The session decides which tools exist

Didim MCP exposes only the tools the user has enabled in the portal. Vault tools
are named `didim-vault__<operation>`. Check that a tool is exposed to this
session before using it; if it is missing, say so and stop.

Operations that exist in the Didim Vault API, and therefore are the possible
tool names — use the exact string, never a guess or an abbreviation:

| Purpose | Tool |
| --- | --- |
| My own resources | `didim-vault__list_my_resources` |
| Search my resources | `didim-vault__search_my_resources` |
| Everything I may use (mine + COMMON) | `didim-vault__list_available_resources` |
| Shared (COMMON) resources | `didim-vault__list_common_resources`, `didim-vault__search_common_resources`, `didim-vault__get_common_resource` |
| SSH targets by alias | `didim-vault__list_accessible_servers`, `didim-vault__get_server_by_alias` |
| Run a command on a registered SERVER | `didim-vault__execute_ssh_command` |
| Reveal a credential | `didim-vault__reveal_my_ssh_credential`, `didim-vault__reveal_common_credential` |

If none of these are exposed, count the Didim tools in the session first. **No
Didim tool at all** is a connection problem → delegate to `didim-mcp-connect`.
A single missing Vault tool while other Didim tools work is a portal entitlement
problem → the user enables it in the Didim portal and restarts Codex.

## Secrets are never yours to print

1. Never output the raw value of a password, private key, passphrase, api key,
   token, refresh token, client secret, or webhook secret — not in a summary,
   not in a code block, not in a table.
2. This holds **even when the user explicitly asks for it.** Say plainly that
   Vault credentials are not delivered through the chat, and offer the action
   they actually need instead (run the command on the server, or open the Vault
   portal).
3. Do not offer a partial reveal. Showing "the first 4 characters" or a
   fingerprint of a secret is the same disclosure in a smaller font.
4. Do not paste a whole credential response object into the answer.
5. The server enforces this too: the Didim MCP gateway redacts credential values
   out of every tool response before it reaches this session, and fails closed
   if it cannot. A field that comes back as `***REDACTED***` is working as
   designed — do not retry, do not look for another tool that might leak it, and
   do not reconstruct it from context.

## Do not over-hide the identifying fields

Masking the things that tell resources apart makes the answer useless. These are
registered non-sensitive metadata, and they are safe to show:

`alias`, `resource_type`, `scope`, `description`, `host`, `ssh_port`,
`environment`, `service_name`, `site_url`, `base_url`, `login_id`, `auth_type`,
`status`, `credential_configured`, `updated_at`.

The Vault resource `id` is not printed in normal answers — it is a tool
argument, not something the user needs to read.

Only the secret values above are withheld.

## Resource types

One resource is one access target with one credential. There are exactly three
types, and the type decides which fields are filled:

- **SERVER** — SSH target. Uses `host` / `ssh_port`. This is the only type SSH
  commands can run against.
- **WEBSITE** — web login target. Uses `site_url` / `login_id`.
- **API** — HTTP API target. Uses `base_url`, and `auth_type` decides the
  credential shape.

There is no separate database type. A database is registered as a **SERVER**
resource when it is reached over SSH. Do not tell the user to look for a "DB"
type, and do not invent one in a filter argument.

Fields that do not apply to a type come back as `null` — omit them from the
answer instead of printing empty rows.

## Picking the right resource

- Report the filter you applied before the result — type, scope, search term.
- **Never pick for the user when several candidates match.** An `alias` alone is
  often not unique: the same site is registered once per account, and
  environments repeat the same service name. Show the candidates with the
  distinguishing fields that are actually present in the response
  (`login_id`, `host`, `site_url`, `base_url`, `environment`, `scope`) and ask
  which one.
- Do not assume a field name. Use only the fields the response actually
  contains.
- `list_available_resources` separates **개인(PERSONAL)** from **공통(COMMON)**
  via `scope` / `scope_display_name`, and returns `total`, `personal_count`,
  `common_count`. Show the scope badge next to each resource — a shared resource
  is not the user's own, and being listed is not the same as being permitted for
  every operation.

## Credentials are for execution, not for reading

- Do not call a reveal tool to answer a lookup question. Listing, searching, and
  identifying a resource never require a credential.
- Use a reveal tool only when an execution step immediately consumes the
  credential, and say which step that is before calling it.
- Reveal is a write-class, confirmation-gated, audited operation, and the
  gateway still redacts the value on the way back. Treat a reveal request with
  no execution behind it as a request to decline, not a request to route.
- Prefer the execution tool over the credential: `didim-vault__execute_ssh_command`
  runs against a registered SERVER using the credential the server resolves
  itself. Nothing sensitive has to pass through this session.
- Before any execution, check `resource_type`. Handing a WEBSITE or API resource
  to an SSH execution tool is a type error — stop and ask, do not "try it".
- Execution and reveal change state or expose data. Stop first, state the exact
  target and the expected effect, and get explicit approval.

## Response pattern

- **Applied filter** — type / scope / search term used.
- **MCP result** — the fields the tool actually returned.
- **Analysis** — interpretation or a recommendation, marked as inference.

When something cannot be done, name the reason (tool not exposed, not
permitted, no such resource) and stop. Do not substitute another tool, another
endpoint, or a shell command.
