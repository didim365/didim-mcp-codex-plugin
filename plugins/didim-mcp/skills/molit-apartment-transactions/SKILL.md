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

Answer Korean apartment real-transaction questions from a district name and a
natural-language month, without the user knowing `LAWD_CD`, `DEAL_YMD`, the
10-digit legal-dong code, the public-data `serviceKey`, or any Vault resource ID.

## Tools (exact MCP names — do not guess or substitute)

1. `odcloud__get_legal_dong_codes` — 국토교통부 법정동코드 조회. Input:
   `{ "page": 1, "perPage": 100, "returnType": "json" }`. Returns legal-dong
   code, name, and abolition status (paged; no name-search argument).
2. `molit-apt-trade__get_apt_trade_real_transactions` — 아파트 매매 실거래가.
   Input: `{ "LAWD_CD": "11530", "DEAL_YMD": "202507" }`.
3. `molit-apt-rent__get_apt_rent_real_transactions` — 아파트 전월세 실거래가.
   Input: `{ "LAWD_CD": "11530", "DEAL_YMD": "202507" }`.

`LAWD_CD` = first 5 digits of the legal-dong code (kept as a string).
`DEAL_YMD` = contract year-month as a 6-digit `YYYYMM` string.

## Overall flow

1. Extract the district name (시군구), the month, and the transaction type.
2. Confirm the required tools are exposed (see **Tool availability**).
3. Resolve `LAWD_CD` via `odcloud__get_legal_dong_codes` (see **Legal-dong**).
4. Convert the month to `DEAL_YMD` (see **Dates**).
5. Call the trade tool, the rent tool, or both (see **Transaction type**).
6. Reply with the applied criteria header, then results per type.

Resolve the legal-dong code and compute `DEAL_YMD` **once** per district+month,
even when querying both trade and rent. Never call the code tool twice for the
same district+month.

## Transaction type

- **Trade** (매매/매매가/거래금액/매수/매도/sale/trade/purchase) →
  `molit-apt-trade__get_apt_trade_real_transactions`.
- **Rent** (전월세/전세/월세/임대차/보증금/월세금/갱신 계약/rent/jeonse/monthly
  rent/lease) → `molit-apt-rent__get_apt_rent_real_transactions`.
- **Both** (매매와 전월세/둘 다/전체 거래/매매·임대차 비교/sales and rent) →
  call both tools.
- **Ambiguous** (e.g. "구로구 작년 7월 아파트 실거래가 알려줘" with no type) →
  do NOT pick one. Ask:
  > 아파트 매매 실거래가와 전월세 실거래가 중 어떤 자료를 조회할까요? 둘 다 조회할 수도 있습니다.
  Skip this question only if the surrounding conversation already makes the type
  clear.

## Legal-dong code resolution

Always obtain the code from `odcloud__get_legal_dong_codes`. Never invent it from
memory, never hardcode a code list in this skill, never assume an unspoken
metropolitan area, and never use an abolished code.

Selection rules:
- The legal-dong name must match the user's district name.
- Use only active/existing rows; exclude abolished (폐지) ones — judge this from
  the tool's actual response fields (do not assume field names; observe them).
- Prefer the 시군구 representative row: the 10-digit code whose lower 5 digits are
  `00000`.
- The API input is the **first 5 digits** of that code, kept as a string (do not
  convert to a number). Example: code `1153000000` → `LAWD_CD` = `"11530"`.
- Auto-confirm only when exactly one valid candidate matches. If several
  metropolitan areas contain the name, ask which 시·도:
  > 어느 지역의 중구인지 확인이 필요합니다. 예: 서울특별시 중구, 부산광역시 중구, 대구광역시 중구
  Do not silently default (e.g. do not assume 서울 중구).
- If a nationwide search yields a single active match, it may be used even
  without the user naming the 시·도. Always show the full resolved region name in
  the reply.
- If a user supplies a code directly, still validate its format and confirm it
  against the tool; if a name and code are both given, verify they match.
- No results → ask for a more specific district name.

### Paging the code tool (no name-search argument)

The tool only accepts `page`, `perPage`, `returnType`, so page through it:
- Start with `{ "page": 1, "perPage": 100, "returnType": "json" }`. If upstream
  rejects `perPage: 100`, lower it to an accepted value; don't use an absurdly
  large value.
- Read the data array, total count, and current page from the actual response
  before deciding to continue.
- If the district isn't on the current page and a next page exists, fetch the
  next page. Never request the same page twice. Stop early once candidates are
  found; scan far enough to catch multiple candidates when needed.
- Enforce a max page / max record cap to prevent unbounded calls
  (ponytail: stop at ~20 pages or the reported total, whichever is smaller). If
  not found within the cap, ask the user for a more specific district name.

## Dates → DEAL_YMD (always 6-digit `YYYYMM` string)

Compute against the **actual current date** (do not hardcode a current year).
Two-digit month. Show the interpretation in the reply.

- `2025년 7월` / `202507` → `202507`
- `작년 7월` → (current year − 1), month `07`
- `올해 3월` → current year, month `03`
- `지난달` → the month before the current one (roll year at January)
- `이번 달` → current year-month
- `재작년 12월` → (current year − 2), month `12`
- `25년 7월` → confirm the century from context → `202507`

If the result is in the future, confirm before calling. If no month is given, ask
for the contract year-month. Don't guess ambiguous dates.

## Tool availability

Didim MCP may expose only the tools the user enabled, so confirm the needed tools
are in `tools/list`:
- Trade request needs: `odcloud__get_legal_dong_codes`,
  `molit-apt-trade__get_apt_trade_real_transactions`.
- Rent request needs: `odcloud__get_legal_dong_codes`,
  `molit-apt-rent__get_apt_rent_real_transactions`.
- Both needs all three.

If a needed tool is missing, do not guess or work around it. Say, e.g.:
> 법정동코드 조회 Tool이 현재 내 MCP 도구에 없습니다. Didim 사용자 포털에서 `국토교통부 법정동코드 조회`를 활성화한 뒤 Codex를 새로 시작하고 다시 요청해주세요.

Display names: 국토교통부 법정동코드 조회 / 국토교통부 아파트 매매 실거래가 조회
/ 국토교통부 아파트 전월세 실거래가 조회.

## Response format

Start with the applied criteria:

```
조회 기준
- 지역: 서울특별시 구로구
- 법정동코드: 1153000000
- 실거래가 조회 코드: 11530
- 계약년월: 2025년 7월 (`202507`)
- 거래 유형: 아파트 매매        # or 아파트 전월세 / 매매 + 전월세
```

Then results per type, using **only fields that actually appear** in the tool
response (do not invent field names or units):
- Trade: 아파트명 · 법정동 · 계약일 · 거래금액 · 전용면적 · 층 · 건축연도 ·
  거래 유형 · 중개사 소재지 · 해제 여부 · 등기일자.
- Rent: 아파트명 · 법정동 · 계약일 · 전세/월세 구분 · 보증금 · 월세금 ·
  전용면적 · 층 · 건축연도 · 계약기간 · 갱신요구권 사용 여부 · 종전 보증금 ·
  종전 월세.

If many results: give 전체 건수 → 간단한 요약 → 대표 거래 일부 → 유형별 구분.

If the response is valid but the data array is empty:
> 해당 지역과 계약년월 조건으로 조회된 거래가 없습니다. 적용 조건은 LAWD_CD=11530, DEAL_YMD=202507입니다.

Keep MCP results separate from your own analysis.

## Error distinction (never conflate with "no data")

- **Tool not enabled** → 필요한 MCP Tool이 현재 내 도구에 없습니다 (portal + restart).
- **MCP auth failure** → Didim MCP 인증 또는 API Key 설정을 확인해야 합니다.
  Never request or print a `dv_` key.
- **Provider credential failure** → 공공데이터 API 인증정보 주입에 실패했습니다.
  관리자에게 Provider Credential 상태 확인이 필요합니다. Never ask the user for a
  `serviceKey`.
- **Upstream API error** → explain from the HTTP status and the safe error text
  the MCP returned.
- **No data** → only when a successful response has an empty data array.

## Security

- Never generate legal-dong codes from memory; only from the code tool.
- Never accept or print a `serviceKey` or a Didim `dv_` API key.
- Never show Vault resource IDs in normal user replies; never log credentials.
- Validate any user-supplied code's format, and verify name↔code agreement via
  the code tool.
- Never auto-pick among multiple candidates; never use abolished codes; don't
  repeat identical queries unnecessarily.
