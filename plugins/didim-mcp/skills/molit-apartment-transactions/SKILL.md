---
name: molit-apartment-transactions
description: >
  Use this skill for Korean MOLIT apartment transaction queries that involve
  apartment sales, trade prices, jeonse, monthly rent, apartment rent, deposits,
  real transaction prices, district (시군구) names, legal-dong codes, or
  natural-language contract months. It resolves a district name through
  odcloud__get_legal_dong_codes, extracts the first five digits as LAWD_CD,
  converts the requested month to DEAL_YMD, and calls either
  molit-apt-trade__get_apt_trade_real_transactions or
  molit-apt-rent__get_apt_rent_real_transactions.
  Trigger for requests such as 아파트 매매 실거래가, 아파트 전월세 실거래가,
  전세 거래, 월세 거래, 보증금, 임대차, 국토교통부 실거래가, 지역명으로 아파트
  거래 조회, 법정동코드를 모르는 조회, 구로구 작년 7월 거래, 종로구 지난달 거래,
  apartment trade/sale transactions, apartment rent transactions, jeonse,
  monthly rent, MOLIT apartment transactions, resolve legal-dong code, and
  search transactions by district name.
---

# MOLIT Apartment Transactions

This skill is a **router**. The working procedure — legal-dong resolution,
paging rules, date conversion, response format, error distinction — lives in the
Didim Skill Registry and is fetched at runtime.

**Registry key:** `molit.apartment-transactions`

## Step 1 — fetch the current workflow

Call `didim-skill__get_skill` with `{"skill_key": "molit.apartment-transactions"}`
and follow the `instructions` it returns. Operators change that body without a
plugin update, so **do not answer from memory of a previous session** — the
field lists and paging caps in particular are tuned there.

## Step 2 — apply the invariants below no matter what the registry says

These are safety rules, not workflow. The registry cannot relax them.

1. **Never generate a legal-dong code from memory.** It comes only from
   `odcloud__get_legal_dong_codes`. Never use an abolished (폐지) code.
2. Never accept or print a `serviceKey`, access token, or any auth header value.
   The user never supplies a Didim credential — Codex runs the OAuth sign-in and
   the MCP server injects provider credentials server-side.
3. Never show Vault resource IDs in normal replies.
4. Compute dates against the **actual current date**. Do not hardcode a year.
   Confirm before querying a future month.
5. **Never auto-pick among multiple candidates** (several 시·도 have a 중구).
   If the transaction type is not stated, ask instead of choosing.
6. Cap repeated calls. Never request the same page twice; resolve the legal-dong
   code and `DEAL_YMD` once per district+month even when querying both types.
7. Use only the fields that actually appear in a tool response. Do not invent
   field names or units.
8. Keep "no data" (a successful response with an empty array) strictly separate
   from a tool being unavailable, an auth failure, a provider credential
   failure, or an upstream API error.
9. Tool authorization is decided by the Didim MCP server. A tool listed in a
   registry entry is **not** permission to call it.

## Tool availability

Confirm the needed tools are exposed before starting:

- Trade: `odcloud__get_legal_dong_codes`,
  `molit-apt-trade__get_apt_trade_real_transactions`
- Rent: `odcloud__get_legal_dong_codes`,
  `molit-apt-rent__get_apt_rent_real_transactions`

If one is missing while other Didim tools work, that is portal entitlement:

> 법정동코드 조회 Tool이 현재 내 MCP 도구에 없습니다. Didim 사용자 포털에서 `국토교통부 법정동코드 조회`를 활성화한 뒤 Codex를 새로 시작하고 다시 요청해주세요.

## Delegation

MCP auth failure → **didim-mcp-connect**. Never request or print any key, token,
or header here.

## If the registry cannot be reached

Fail closed **on the procedure, not on the tools.** Do not improvise the query
procedure from memory — the legal-dong resolution rules are exactly the part
that must not be guessed. A missing recipe is still not a missing capability.

- **No Didim tool at all** → connection problem → `didim-mcp-connect`.
- **`didim-skill__get_skill` missing while other Didim tools work** → portal
  entitlement: enable the Didim Skill Registry tools and restart Codex.
- **Registry error, timeout, or the skill not published** → say the curated
  procedure could not be loaded, then continue with the exposed tools under the
  invariants above. Those invariants already carry the parts that must not be
  guessed: **the legal-dong code comes from `odcloud__get_legal_dong_codes` and
  never from memory**, dates are computed against the actual current date, and
  ambiguous districts or transaction types are asked about rather than chosen.
  If you cannot satisfy them without the recipe, say so instead of guessing.
