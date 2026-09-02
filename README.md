# Didim MCP — Codex Plugin

Codex에서 **Didim MCP 서버**를 Microsoft 계정으로 연결해 사용하는 플러그인입니다.

플러그인이 매니페스트에서 Hosted MCP 서버를 직접 선언하고, **로그인은 Codex의 MCP OAuth
기능이 처리**합니다. 사용자가 API Key를 발급받거나, 붙여넣거나, `config.toml`을 손대는 단계는
없습니다.

- **MCP 서버 URL:** `https://didimmcp-dev.didimservice.com/mcp` (Streamable HTTP)
- **인증:** OAuth 2.1 (Microsoft Entra 로그인 → Didim OAuth 동의) — Codex가 수행
- **사용자가 입력하는 자격증명:** 없음

> 이 저장소에도, 배포되는 플러그인 파일에도 사용자 자격증명은 존재하지 않습니다.
> 토큰은 Codex가 자체 자격증명 저장소에 보관합니다.

---

## 설치 · 연결 (Codex 앱)

1. **Codex 앱**을 실행합니다.
2. 왼쪽에서 **플러그인**을 선택합니다.
3. **만들기 → 마켓플레이스 추가**를 선택합니다.
4. **출처**에 다음을 입력합니다.
   ```
   https://github.com/didim365/didim-mcp-codex-plugin.git
   ```
5. **Git ref**와 **Sparse 경로**는 비워 두고 **마켓플레이스 추가**를 클릭합니다.
6. 마켓플레이스 목록에서 **Didim MCP**를 **설치**합니다.
7. 설치 직후 **Microsoft 로그인 화면이 자동으로 열립니다.** 로그인하고 **Didim 동의 화면**을
   승인합니다.
8. 창이 닫혔거나 취소했다면 그냥 다음 항목으로 넘어가세요 — 등록은 유지되며, Didim Tool을
   호출할 때 Codex가 로그인을 다시 요구합니다.
9. Codex를 새로 시작하고 **새 채팅**에서 `/mcp`로 `didim-mcp` 연결을 확인합니다.
10. 이후 Didim 관련 질문에는 `didim-mcp-usage` / `molit-apartment-transactions`
    Skill이 자동 적용됩니다.

연결이 안 보이거나 실패하면 새 채팅에서 `Didim MCP 연결해줘` 라고 요청하세요.
`didim-mcp-connect` Skill이 원인별 조치를 안내합니다.

### (선택) Codex CLI 사용자

`codex` CLI를 **별도로 설치**한 경우에만 사용합니다.

```bash
codex plugin marketplace add https://github.com/didim365/didim-mcp-codex-plugin.git
codex plugin add didim-mcp@didim
codex mcp login didim-mcp     # 브라우저가 열리고 Microsoft 로그인 진행
codex mcp list                # Auth 열이 "Logged in" 인지 확인
```

> **Windows Store로 설치한 Codex 앱 내부의 `codex.exe`를 직접 실행하지 마세요.**

---

## 연결 · 계정 관리 (자연어로 요청)

아래는 **새 채팅에서 자연어로** 요청하면 `didim-mcp-connect` Skill이 상태를 확인하고 처리합니다.
플러그인을 지우고 다시 설치할 필요가 없습니다.

| 하고 싶은 것 | 이렇게 말하면 됩니다 |
| --- | --- |
| 설치할 때 뜬 로그인 창을 닫았음 | `아까 로그인 창 닫았는데 다시 로그인해줘` |
| 연결이 안 된 것 같음 | `Didim MCP 연결해줘` |
| 지금 로그인된 계정 확인 | `지금 Didim MCP 누구로 로그인돼있어?` |
| 다른 Microsoft 계정으로 변경 | `Didim MCP 다른 Microsoft 계정으로 로그인해줘` |
| 인증 만료 · 401 오류 | `Didim MCP 다시 인증해줘` |

**설치 중 로그인 창을 닫아도 플러그인은 정상 설치된 상태입니다.** 등록(registration)과
로그인(sign-in)은 별개이므로 삭제·재설치가 필요 없습니다.

Skill은 **현재 채팅에 노출된 Didim MCP Tool**을 기준으로 상태를 판단합니다. 계정 조회는
프로필 Tool을 바로 호출하고, 인증이 필요하면 Tool 호출이 Codex 자체의 인증 흐름을
띄웁니다(OAuth MCP 서버는 Tool을 처음 호출할 때 로그인을 요구하도록 규격에 정의되어
있습니다).

계정을 바꿀 때 브라우저에 기존 Microsoft SSO 세션이 남아 있으면 같은 계정으로 자동
로그인될 수 있습니다. 그럴 때는 Microsoft 로그인 화면에서 **"다른 계정으로 로그인"** 을
선택하세요.

### 확인된 것과 확인되지 않은 것

- **확인됨** — 설치 시점의 Microsoft 로그인 화면은 실제로 뜹니다(마켓플레이스 정책이
  `ON_INSTALL`). Tool 호출은 호스트의 인증 흐름을 유발합니다. Codex 문서는 설정 →
  MCP 서버 목록의 **Authenticate** 동작을 안내합니다.
- **확인되지 않음** — 검증에 사용한 Codex 앱 UI에서는 플러그인 제공 `didim-mcp` 항목에
  Connect / Disconnect 버튼이나 톱니 아이콘이 **없었습니다.** 그리고 앱에 저장된 Didim
  로그인을 Skill이 직접 지우는 방법은 확인되지 않았습니다. 같은 계정으로 강제 재로그인
  하거나 계정을 완전히 바꾸는 확실한 경로는 현재 **플러그인 재설치**(설치 시점 로그인이
  다시 실행됨)뿐입니다.

> **`codex mcp list` 는 Codex 앱의 상태가 아닙니다.** Codex 앱은 셸 명령을 별도의
> 샌드박스 OS 계정으로 실행하므로, 그 안에서 실행한 `codex` 는 앱과 **다른 Codex 홈**을
> 읽습니다. 실제로 플러그인이 정상 동작 중인 채팅에서도 `codex mcp list` 와
> `codex plugin list` 가 "0개"로 나옵니다. 앱 상태 판정에 쓰지 마세요.
>
> Skill 자동 선택은 표현에 따라 달라질 수 있으며 100% 보장되지 않습니다.

아래 명령은 **별도로 설치한 `codex` CLI 전용**입니다. 앱의 플러그인 로그인과는 별개의
저장소를 사용합니다.

```bash
codex mcp list --json        # 이 CLI 컨텍스트의 registry / auth_status
codex mcp login  didim-mcp   # 이 CLI의 Microsoft 로그인
codex mcp logout didim-mcp   # 이 CLI에 저장된 로그인 삭제
```

---

## 0.1.x에서 업그레이드하는 기존 사용자 (필수)

0.1.x 플러그인은 사용자의 `~/.codex/config.toml`에 다음과 같은 블록을 기록했습니다.

```toml
[mcp_servers.didim-mcp]
url = "..."
startup_timeout_sec = 120

[mcp_servers.didim-mcp.http_headers]
X-Didim-Vault-Api-Key = "<사용자가 입력했던 dv_ API Key>"
```

**이 블록이 남아 있으면 플러그인이 제공하는 OAuth 서버를 가립니다.** Codex는 계속 예전
설정으로 접속하고, OAuth 로그인이 시작되지 않으며, Didim 서버는 더 이상 사용자 API Key를 받지 않으므로
인증이 실패합니다. 업그레이드 후에는 반드시 아래 정리 스크립트를 한 번 실행하세요.

- 더블클릭: `%USERPROFILE%\.codex\plugins\cache\didim\didim-mcp\<version>\scripts\migrate-didim-mcp.cmd`
- 또는 PowerShell:
  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\plugins\cache\didim\didim-mcp\<version>\scripts\migrate-didim-mcp.ps1"
  ```
- CLI 사용자: `codex mcp remove didim-mcp`

스크립트가 하는 일:

```
config.toml 읽기 → 예전 didim-mcp 블록 탐지 → 없으면 그대로 종료
→ 타임스탬프 백업 → [mcp_servers.didim-mcp] 및 하위 테이블만 제거
   (다른 MCP 서버·설정은 내용과 순서 그대로 보존) → UTF-8(BOM 없음)으로 저장
```

- 예전 키 값은 **읽어서 비교하거나 출력하지 않습니다.** `legacy credential removed` 만 알립니다.
- 정리 후: Codex 완전 종료 → 재실행 → `codex mcp login didim-mcp` → Microsoft 로그인.
- 이전에 생성된 `config.toml.backup-*` 파일에는 예전 키가 그대로 남아 있습니다. 필요 없으면
  삭제하세요.

---

## 사용 예

연결이 끝나면 자연어로 요청합니다. Tool 목록은 플러그인에 박혀 있지 않고, 접속할 때마다
MCP 서버가 `tools/list`로 **로그인한 사용자에게 허용된 것만** 내려줍니다. 따라서 사람마다,
포털 설정 변경 시점마다 보이는 Tool이 다를 수 있습니다.

```
내 Didim 사용자 정보 보여줘
사용 가능한 Didim 서버 목록 보여줘
RAG로 사내 문서에서 휴가 규정 검색해줘
구로구 지난달 아파트 매매 실거래가 알려줘
구로구 지난달 아파트 전월세 실거래가 알려줘
```

---

## 아파트 실거래가 조회 (국토교통부)

지역명과 자연어 날짜만으로 국토교통부 아파트 **매매/전월세** 실거래가를 조회합니다.
`LAWD_CD`, `DEAL_YMD`, 10자리 법정동코드, `serviceKey`를 직접 입력할 필요가 없습니다
(`molit-apartment-transactions` Skill이 자동 적용).

예시 요청:
```
구로구 작년 7월 아파트 매매 실거래가 알려줘
구로구 작년 7월 아파트 전월세 실거래가 알려줘
서울 중구 2025년 7월 전세 거래 조회해줘
마포구 지난달 월세 거래 알려줘
종로구 작년 12월 매매와 전월세를 모두 비교해줘
```

내부 처리 흐름:
```
지역명 → 법정동코드 Tool 조회 → 활성 시군구 대표 코드 선택
       → 앞 5자리 LAWD_CD 추출 → 날짜를 DEAL_YMD(YYYYMM)로 변환
       → 매매 Tool 또는 전월세 Tool 호출
```

필요한 MCP Tool (조회하려는 거래 유형에 맞게 **Didim 사용자 포털에서 활성화** 후 Codex 재시작):
- 국토교통부 법정동코드 조회 (`odcloud__get_legal_dong_codes`) — 항상 필요
- 국토교통부 아파트 매매 실거래가 조회 (`molit-apt-trade__get_apt_trade_real_transactions`) — 매매
- 국토교통부 아파트 전월세 실거래가 조회 (`molit-apt-rent__get_apt_rent_real_transactions`) — 전월세

공공데이터 `serviceKey`는 Didim MCP 서버가 서버 측에서 주입합니다. 사용자와 Codex는 보유하지
않습니다.

---

## 외부 Provider Credential (로그인 인증과 다릅니다)

두 가지를 혼동하지 마세요.

| | 사용자 로그인 인증 | 외부 Provider resource credential |
| --- | --- | --- |
| 예 | (구) `dv_` API Key | 공공데이터 `serviceKey`, SSH 계정, 외부 API 자격증명 |
| 현재 상태 | **폐지됨.** Microsoft OAuth로 대체 | **유지됨.** 정상 기능 |
| 누가 보관 | 토큰은 Codex | Didim Vault (서버 측) |
| 사용자가 입력? | 아니오 | 아니오 — 서버가 주입 |

즉 "API Key가 없어졌다"는 말은 **Didim 로그인용 개인 API Key**에만 해당합니다. Vault에
저장된 외부 연동 credential은 그대로 쓰이며, Tool 실행 시 서버가 로그인 사용자 권한을 확인한
뒤 주입합니다. 사용자·Codex·Skill은 그 값을 보유하지도, 요구하지도 않습니다.

---

## (개발 · UAT 전용) Direct MCP 등록

일반 사용자는 이 경로를 쓰지 않습니다. 아래는 서버 개발/검증용 보조 경로입니다.

```
https://didimmcp-dev.didimservice.com/mcp
```

Codex에 이 URL을 MCP 서버로 직접 등록해도 동일한 OAuth 로그인이 동작합니다. 다만
**플러그인 최종 검증 시에는 Direct MCP 등록을 반드시 비활성화**하세요. 같은 서버가 두 경로로
동시에 붙어 있으면 어느 쪽이 동작한 것인지 판별할 수 없습니다.

---

## 저장소 구조

```
.
├── .agents/plugins/marketplace.json          # Marketplace 매니페스트 (name: didim)
├── plugins/didim-mcp/                        # ← 사용자에게 설치되는 범위
│   ├── .codex-plugin/plugin.json             # 플러그인 매니페스트 (mcpServers 로 Hosted MCP 선언)
│   ├── README.md
│   ├── scripts/
│   │   ├── migrate-didim-mcp.ps1             # 0.1.x 레거시 config.toml 블록 정리
│   │   └── migrate-didim-mcp.cmd             # 더블클릭 실행 런처
│   └── skills/
│       ├── didim-mcp-connect/SKILL.md        # 연결 · 재연결 · 업그레이드 · 문제 해결 (자동 선택)
│       ├── didim-mcp-usage/SKILL.md          # 안전 사용 (자동 선택)
│       └── molit-apartment-transactions/SKILL.md  # 국토교통부 아파트 실거래가 조회 (자동 선택)
├── CLAUDE.md                                 # 리포 작업용 에이전트 지시문 (배포 안 됨)
├── .claude/rules/                            # 경로 스코프 작업 규칙 (배포 안 됨)
├── .gitignore
└── README.md
```

> 현재 플러그인 버전은 `plugins/didim-mcp/.codex-plugin/plugin.json`의 `version` 필드가
> 기준입니다. (이 도식에 버전을 중복 표기하지 않습니다.)

> 참고: 스크립트는 **플러그인 내부**(`plugins/didim-mcp/scripts/`)에 위치합니다.
> Codex는 설치 시 플러그인 디렉터리만 배포하므로, 설치 후에도 스크립트를 찾을 수 있으려면
> 스크립트가 플러그인 안에 있어야 합니다. 같은 이유로 `CLAUDE.md`와 `.claude/rules/`는
> 설치본에 포함되지 않으며, 플러그인 동작에 영향을 주지 않습니다.

---

## 업데이트 방법

운영자가 새 버전을 push 하면 사용자는 **Codex 앱의 플러그인 화면**에서 마켓플레이스를 갱신한 뒤
**Didim MCP**를 다시 설치(업데이트)합니다.

- MCP URL은 플러그인 매니페스트에 있으므로, URL이 바뀌어도 **플러그인 업데이트만으로 반영**됩니다.
- OAuth 연결(토큰)은 업데이트로 지워지지 않습니다. 만료되면 Codex가 refresh 하고, 실패하면
  Didim Tool을 다시 호출할 때 Codex가 로그인을 요구합니다.
- 0.1.x → 0.2.x 업그레이드는 위의 **레거시 정리**를 한 번 수행해야 합니다.

**(선택) Codex CLI 사용자**
```bash
codex plugin marketplace upgrade
codex plugin add didim-mcp@didim
```

---

## 제거 방법

**Codex 앱의 플러그인 화면**에서 **Didim MCP**를 제거합니다. 플러그인이 제공하던 MCP 서버는
플러그인과 함께 사라지므로 `config.toml`을 따로 정리할 필요가 없습니다.

**(선택) Codex CLI 사용자**
```bash
codex plugin remove didim-mcp@didim
# (선택) codex plugin marketplace remove didim
```

별도로 설치한 `codex` CLI에 저장된 자격증명은 `codex mcp logout didim-mcp` 로 지웁니다.
이는 CLI 컨텍스트에만 적용되며, Codex 앱이 보관하는 플러그인 로그인과는 별개입니다.

---

## 보안 주의사항

- 사용자 API Key는 더 이상 존재하지 않습니다. **API Key를 요구하는 화면·안내를 만나면
  구버전 플러그인입니다.**
- 이 저장소, 플러그인 파일, Skill 어디에도 자격증명이 들어 있지 않습니다.
- MCP 엔드포인트는 **HTTPS**입니다(`*.didimservice.com` Wildcard 인증서로 TLS 종단).
  NodePort/IP 직접 접근(평문 HTTP)은 사용하지 않습니다.
- OAuth 토큰은 Codex가 관리합니다. Skill과 모델은 토큰을 읽거나 출력하지 않습니다.
- 0.1.x 시절 생성된 `config.toml.backup-*` 파일에는 예전 평문 키가 남아 있을 수 있습니다.
  필요 없으면 삭제하세요.
- 읽기 전용 작업을 우선하고, 데이터 변경·고위험 작업은 사용자 승인 후 진행합니다.

---

## 문제 해결

| 증상 | 확인 / 조치 |
| --- | --- |
| 설치했는데 `/mcp`에 `didim-mcp`가 없음 | Codex를 **완전히 재시작**하고 **새 채팅**을 여세요. 플러그인 제공 MCP는 기동 시점에 반영됩니다 |
| 설치 중 로그인 창을 닫았음 | **바로 재설치하지 마세요.** 등록은 유지됩니다. 새 채팅에서 `Didim MCP 연결해줘` 라고 하면 Tool 호출로 로그인이 다시 요구됩니다 |
| 지금 로그인된 계정을 모르겠음 | `지금 Didim MCP 누구로 로그인돼있어?` — 로그인 상태면 계정·role·상태를 알려줍니다 |
| 플러그인 화면에 Connect 버튼이 없음 | 검증한 Codex 앱 UI에서는 플러그인 제공 MCP에 Connect/Disconnect가 노출되지 않았습니다. Didim Tool을 호출하면 필요할 때 Codex가 로그인을 요구합니다 |
| `codex mcp list` 에 `didim-mcp` 가 안 나옴 | 앱 안에서 실행한 `codex` 는 **별도 샌드박스 계정의 Codex 홈**을 읽습니다. 앱 상태의 근거가 아닙니다. `/mcp` 로 확인하세요 |
| 업그레이드 후 인증이 계속 실패함 | 0.1.x가 남긴 `[mcp_servers.didim-mcp]`가 플러그인 설정을 가리고 있습니다. `migrate-didim-mcp.cmd` 실행 후 Codex 재시작 |
| 예전 `X-Didim-Vault-Api-Key` / `http://49.50.138.22:31083/mcp/` 로 붙어 있음 | 같은 원인입니다. 위 정리 스크립트를 실행하세요 |
| 다른 Microsoft 계정으로 바꾸고 싶음 | 현재 앱에서 확인된 확실한 경로는 **플러그인 재설치**(설치 시점 로그인이 다시 실행됨)입니다. Microsoft 화면이 뜨면 **"다른 계정으로 로그인"** 을 선택하세요 |
| **Didim Tool이 하나도 안 보임** (`/mcp`에는 `사용함 / 인증됨(OAuth)`) | **포털 권한 문제가 아닙니다.** Codex가 저장해 둔 로그인을 갱신하려다 서버에서 거부되면 MCP 서버가 아예 기동하지 않고, 그래도 `/mcp` 배지는 `인증됨`으로 남습니다. Codex를 완전히 재시작한 뒤 Didim Tool을 호출해 로그인 창이 뜨는지 확인하세요. 그래도 안 되면 플러그인 재설치(설치 시점 로그인 재실행) |
| 연결은 됐는데 **특정** Tool만 없음 (다른 Didim Tool은 정상) | 인증 문제가 아닙니다. **Didim 사용자 포털에서 해당 Tool을 활성화**한 뒤 Codex 재시작 |
| 한동안 쓰다가 갑자기 인증 실패 | Codex가 먼저 refresh를 시도하고, 서버가 그 refresh를 거부하면 재로그인이 필요합니다. Didim Tool을 다시 호출해 로그인 요구가 뜨는지 확인하세요 |
| 설치가 안 됨 | 플러그인 화면에 **Didim** 마켓플레이스가 추가됐는지 확인 (CLI 사용자는 `codex plugin marketplace list`) |
| 스크립트 실행 시 한글이 `??`/깨져서 나옴 | Windows PowerShell 5.1의 UTF-8 처리 문제입니다. 최신 버전으로 업데이트하세요. 스크립트가 UTF-8 BOM + `chcp 65001` + 콘솔 인코딩을 적용합니다 |

---

## 참고

- 플러그인 문서: [`plugins/didim-mcp/README.md`](plugins/didim-mcp/README.md)
- 연결 Skill: [`plugins/didim-mcp/skills/didim-mcp-connect/SKILL.md`](plugins/didim-mcp/skills/didim-mcp-connect/SKILL.md)
- 안전 사용 Skill: [`plugins/didim-mcp/skills/didim-mcp-usage/SKILL.md`](plugins/didim-mcp/skills/didim-mcp-usage/SKILL.md)
- 아파트 실거래가 Skill: [`plugins/didim-mcp/skills/molit-apartment-transactions/SKILL.md`](plugins/didim-mcp/skills/molit-apartment-transactions/SKILL.md)
