# GW Holiday

Answer "내 연차/휴가 현황" questions for **the signed-in user only**, for one
calendar year at a time. The user never supplies an employee number, an account,
a token, or an API key — the Didim MCP server resolves the caller from the
Microsoft OAuth identity Codex already signed in with.

This skill never looks up anyone else's leave.

## Tool (exact MCP name — do not guess or substitute)

`didim-gw__get_my_holiday_info` — 내 연차 현황 조회.

Input — exactly one field:

```json
{ "year": 2025 }
```

- `year` is an **integer** (not a string), between 2000 and 2100.
- There is no other input. Do not add an employee id, a name, a department, a
  date range, or a `confirm` flag. Confirmation and authorization are MCP
  concerns, never business arguments.

Call this tool, and only this tool, **exactly once** per answer.

## Overall flow

1. Decide whether the request is about the user's **own** leave/holiday status.
   If it names another person, refuse (see **Scope**).
2. Resolve the target year (see **Years**).
3. Confirm `didim-gw__get_my_holiday_info` is exposed to this session (see
   **Tool availability**).
4. Call it once with the resolved year.
5. Explain the result from the **actual response only**.
6. Never infer, compute, or fill in a number the response does not contain.

## Years

Resolve the year against the **actual current date**. Do not hardcode a current
year in this procedure, and do not carry one over from an earlier session.

| 사용자 표현 | `year` |
| --- | --- |
| `2025년 연차` | `2025` |
| `올해 연차`, `이번 연도 연차` | 현재 연도 |
| `작년 연차`, `지난해 연차` | 현재 연도 - 1 |
| `재작년 연차` | 현재 연도 - 2 |
| `내 연차`, `남은 연차` (연도 없음) | 현재 연도 |
| `25년 연차` (두 자리) | 문맥이 분명하면 `2025` |

Example: if the current year is 2026, "작년 연차 조회" →
`didim-gw__get_my_holiday_info` with `{"year": 2025}`.

If the expression is ambiguous, or a two-digit year could plausibly mean a
different century, ask before calling:

> 어느 연도의 연차 현황을 조회할까요? 예: 2025년

A future year is allowed by the schema but rarely intended — confirm it first.
If the resolved year falls outside 2000–2100, ask for a valid year instead of
clamping it.

## Scope — 본인만

- Only the signed-in user's own leave is available.
- If the user asks for someone else ("김대리 연차 알려줘", "팀원 연차 현황",
  "우리 팀 잔여 연차"), do not call the tool and do not attempt a workaround:
  > 이 도구는 로그인한 본인의 연차 현황만 조회할 수 있습니다. 다른 사람의 연차는 조회할 수 없습니다.
- Never ask the user for an employee number, account, or department to query on
  someone's behalf. There is no such parameter.

## Tool availability

Didim MCP exposes only the tools the user has enabled, so confirm
`didim-gw__get_my_holiday_info` is in this session's tool list before using it.

If it is missing, do **not** substitute another tool, invent a tool name, guess
an endpoint, or answer from memory:

> 내 연차 현황 조회 Tool이 현재 Didim MCP 도구에 없습니다. Didim 사용자 포털에서 `내 연차 현황 조회`를 활성화한 뒤 Codex를 새로 시작하고 다시 요청해주세요.

If **no** Didim tool at all is exposed, this is a connection problem, not an
entitlement problem — delegate to `didim-mcp-connect`.

## Response format

Start with the applied criteria:

```
조회 기준
- 대상: 현재 로그인한 사용자 본인
- 연도: 2025년
```

Then present **only the fields that actually appear** in the tool response.
Depending on what GW returns, that may include 총 연차, 사용 연차, 잔여 연차,
이월/조정 같은 항목 — but read the response and use its real field names and
units. Do not invent a field, do not convert 일/시간 units the response did not
state, and do not compute 잔여 연차 yourself when the response already carries
it (or when it does not carry the inputs for it).

If the response is valid but carries no leave data for that year:

> 2025년 연차 데이터가 조회되지 않았습니다. 해당 연도에 등록된 연차 정보가 없습니다.

Keep the MCP result and your own commentary clearly separated.

## Error distinction (never conflate with "no data")

- **Tool not exposed** → 포털 활성화 + Codex 재시작 안내 (above).
- **Authentication / authorization failure** (401·403, expired or invalid
  session, Graph token rejected) → 인증 문제로 보고하고 `didim-mcp-connect` 에
  위임한다. **절대 "연차가 없다" 로 바꿔 말하지 않는다.**
  > Didim MCP 인증이 만료되었거나 실패했습니다. Microsoft 계정으로 다시 로그인한 뒤 요청해주세요.
- **Upstream GW error** (5xx, timeout) → 그룹웨어 연동 오류로 설명하고, 재시도
  여부를 사용자에게 맡긴다. 같은 호출을 자동으로 반복하지 않는다.
- **No data** → only when the call **succeeded** and the returned leave data is
  actually empty.

## Security

- The user never types a credential. Never ask for an access token, API key,
  Authorization header, employee password, or Graph token.
- Never print, echo, or log any credential, token, or auth header value that
  appears anywhere in a response.
- Never query, display, or infer another user's leave data.
- Send nothing beyond `year` to the tool. Leave data is personal information —
  do not copy it into unrelated contexts, files, or external services.
