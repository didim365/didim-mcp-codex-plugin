---
paths:
  - "plugins/didim-mcp/skills/**"
---

# SKILL.md 작성 규칙

대상: `didim-mcp-connect`, `didim-mcp-usage`, `molit-apartment-transactions`.
이 파일들은 문서가 아니라 **런타임 동작**이다. Codex가 읽고 그대로 수행한다.

## Frontmatter

- `name`, `description` 두 키만 쓴다. `name`은 디렉터리명과 일치시킨다.
- `description`이 **유일한 트리거 메커니즘**이다. 코드 기반 라우팅이 없으므로, 여기에 없는
  표현은 절대 이 Skill을 부르지 못한다. 짧게 줄이는 것이 곧 기능 축소다.
- 트리거는 **한국어와 영어를 함께** 적는다. 실제 사용자 발화 형태(예: `"Didim MCP 설정해줘"`,
  `"구로구 작년 7월 거래"`)와 오류 증상 문구(예: `"No Didim MCP tools are exposed"`)를 포함한다.
- 새 Skill을 추가할 때는 기존 3개의 `description`과 트리거가 겹치지 않는지 확인한다. 겹치면
  어느 Skill이 뜰지 예측할 수 없다. 겹치는 영역이 있으면 본문에 위임 관계를 명시한다
  (`didim-mcp-usage` → `molit-apartment-transactions` 위임이 그 예다).

## 인증 (OAuth-only)

- Skill은 **자격증명을 요구·수집·출력하지 않는다.** API Key 입력, `dv_` 키, 토큰 붙여넣기,
  헤더 설정, MCP URL 직접 입력을 안내하는 문장을 넣지 않는다. 연결은 Codex 내장 MCP OAuth
  (Microsoft 로그인 → Didim 동의)로만 이루어진다.
- **설치된 플러그인 제공 MCP에 Connect/Disconnect 버튼·톱니가 있다고 안내하지 않는다.**
  Human UAT에서 확인한 Codex App UI에는 존재하지 않는다(설치 시점 OAuth 흐름은 실재한다).
  인증 lifecycle은 `codex mcp login/logout didim-mcp`로 안내한다.
- 인증 실패 안내의 종착점은 항상 `didim-mcp-connect` Skill(= OAuth 재로그인)이다. 로그인 계정
  조회·계정 변경·취소된 로그인 재시도도 전부 `didim-mcp-connect` 소관이며, 다른 Skill은 위임만
  한다.
- **재설치를 기본 처방으로 쓰지 않는다.** 취소된 로그인·만료된 세션·미노출 Tool은 재설치 없이
  해결된다(검증됨: 로그인 중단 후에도 등록이 유지되고 재시도가 동작한다). 플러그인 자체가
  없거나 캐시가 손상된 근거가 있을 때만 재설치를 제안한다.
- `codex mcp login` / `codex mcp logout`은 인증 상태를 바꾸므로 실행 전 설명하고 승인받는다.
  조회(`codex mcp list`, 프로필 Tool)는 read-only다.
- Skill이 `~/.codex/config.toml`을 읽거나 쓰도록 지시하지 않는다. 유일한 예외는
  `didim-mcp-connect`가 0.1.x 레거시 블록 정리 스크립트 실행을 **승인받아** 제안하는 경우다.

## MCP Tool 참조

- Tool 이름은 **정확한 문자열 그대로** 적는다. 추측·축약·대체하지 않는다.
  현재 참조되는 것은 `odcloud__get_legal_dong_codes`,
  `molit-apt-trade__get_apt_trade_real_transactions`,
  `molit-apt-rent__get_apt_rent_real_transactions`,
  그리고 신원 조회용 `didim-mcp-auth__get_current_user_profile` ·
  `didim-vault__get_current_user_profile` 다섯이다. 신원 조회는 둘 중 **노출된 쪽**을 쓰고,
  둘 다 없으면 포털 권한 문제로 안내하고 중단한다.
- Didim MCP는 사용자가 포털에서 활성화한 Tool만 노출한다. 사용 전에 `tools/list`로 존재를
  확인하고, 없으면 즉시 중단 + 포털 활성화 안내로 끝낸다. 우회 경로·대체 엔드포인트를
  만들어내지 않는다.
- 응답 필드명을 가정하지 않는다. 실제 응답에 나타난 필드만 사용해 답한다.
- 코드·식별자를 모델 기억에서 생성하지 않는다(법정동코드가 대표 사례). 반드시 Tool 조회 결과에서
  가져온다.

## 애매하면 묻는다

- 후보가 여럿이면 자동 선택하지 않는다(예: 여러 시·도의 "중구"). 거래 유형이 명시되지 않으면
  매매/전월세를 임의로 고르지 않는다.
- 날짜는 **실제 현재 날짜** 기준으로 계산한다. 연도를 하드코딩하지 않는다. 미래 월이 나오면
  확인 후 진행한다.
- 반복 호출에는 상한을 둔다(페이징은 ~20페이지 또는 보고된 total 중 작은 쪽). 같은 페이지를
  두 번 요청하지 않는다. 동일 조건에 대한 선행 조회는 1회만 수행한다.

## 오류 구분

"데이터 없음"과 실패를 절대 섞지 않는다. 최소 다음을 구분해 서로 다른 안내를 낸다.

| 상황 | 안내 방향 |
| --- | --- |
| Tool 미노출 | 포털에서 해당 Tool 활성화 후 Codex 재시작 |
| MCP 인증 실패 | `didim-mcp-connect`로 위임(= `codex mcp login didim-mcp`). 키·토큰은 묻지도 출력하지도 않는다 |
| Provider credential 실패 | 관리자에게 Provider Credential 확인 요청 (`serviceKey`를 사용자에게 묻지 않는다) |
| 상위 API 오류 | HTTP 상태 + MCP가 돌려준 안전한 오류 문구로 설명 |
| 데이터 없음 | 성공 응답 + 빈 배열일 때만. 적용된 조건을 함께 제시 |

## 응답 구조

- 적용 조건(조회 기준)을 먼저 밝히고 결과를 낸다.
- **MCP 실행 결과와 모델의 분석·추론·권고를 명확히 분리**한다. 추론에는 추론이라고 표시한다.
- 쓰기·고위험 작업은 실행 전에 멈추고, 정확한 대상과 예상 효과를 제시해 승인을 받는다.
