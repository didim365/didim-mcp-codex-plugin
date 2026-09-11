# Didim MCP — Codex Plugin + Dynamic Skill Registry

이 저장소는 두 가지를 담습니다.

| | 무엇인가 | 누가 쓰는가 |
| --- | --- | --- |
| **Codex Plugin** (`plugins/didim-mcp/`) | Codex에서 Didim MCP 서버를 Microsoft 계정으로 연결해 쓰는 플러그인 | 모든 직원 |
| **Skill Registry** (`app/`, `web/`) | Skill 업무 절차를 Git/재배포 없이 웹에서 관리·배포하는 애플리케이션 | 운영자(ADMIN) |

**핵심 변화:** 예전에는 업무 절차가 `SKILL.md` 파일 안에 있어서, 한 줄을 고치려면 소스를
수정하고 플러그인을 다시 배포하고 사용자가 재설치해야 했습니다. 이제 절차는 **DB에 있고
Admin Web에서 초안 → 배포**로 바뀝니다. 플러그인에는 "어떤 절차를 어디서 가져올지" 만
남습니다.

- **MCP 서버 URL:** `https://didimmcp-dev.didimservice.com/mcp` (Streamable HTTP)
- **Skill Registry Admin:** 사내 전용 주소 — 운영자용이며 DIDIM SSO + ADMIN 권한이 필요합니다.
  실제 도메인은 배포 저장소(private)에 있습니다. **DNS·nginx 연결 대기**
- **인증:** OAuth 2.1 (Microsoft Entra 로그인 → Didim OAuth 동의) — Codex / 브라우저가 수행
- **사용자가 입력하는 자격증명:** 없음
- **Didim MCP 포털:** <https://didimmcp-dev.didimservice.com/> — 사용할 Tool을 켜고 끄는 곳
- **현재 대상:** dev 환경

> 이 저장소에도, 배포되는 플러그인 파일에도 사용자 자격증명은 존재하지 않습니다.
> 토큰은 Codex(플러그인 경로) 또는 HttpOnly 쿠키(웹 경로)가 보관합니다.

---

## 이 저장소의 책임 범위

| 이 저장소가 소유하는 것 | 소유하지 않는 것 (어디에 있는지) |
| --- | --- |
| 마켓플레이스 · 플러그인 매니페스트 (MCP 서버 URL 선언) | **OAuth 구현** — Codex 내장 MCP OAuth 클라이언트와 Didim Auth 서버 |
| Skill 5개 — 정적 1개(연결) + thin router 3개 + generic fallback 1개 | **Tool 카탈로그와 사용자별 권한** — Didim MCP 서버 / 포털 |
| 0.1.x 레거시 `config.toml` 정리 스크립트 | **Provider credential 주입** — Didim Vault (서버 측) |
| **Skill Registry 애플리케이션** (FastAPI + React Admin) | **Microsoft 계정 · MFA · 계정 선택** — Microsoft Entra |
| **`mcp_skill_registry` schema 와 그 migration** | **사용자 계정 · role 정본** — `didim_mcp_auth.users` (Auth 서비스) |
| Dockerfile · Jenkinsfile | **Kubernetes manifest** — `didim-mcp-codex-plugin-deploy` |

이 저장소에는 OAuth `client_id`·`client_secret`·redirect URI·토큰이 존재하지 않습니다.
Tool 목록도 여기에 없습니다 — 접속할 때마다 MCP 서버가 `tools/list`로 내려줍니다.
사용자 계정도 복제하지 않습니다 — role은 매 요청 Auth `GET /api/v1/me`로 확인합니다.

**설치 시 사용자 PC로 배포되는 범위**(실측): `plugins/didim-mcp/` 아래의
`.codex-plugin/plugin.json` · `README.md` · `scripts/` · `skills/` 뿐입니다.
`CLAUDE.md`와 `.claude/rules/`는 배포되지 않으며 플러그인 동작에 영향을 주지 않습니다.

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
10. 이후 Didim 관련 질문에는 `didim-mcp-usage` / `didim-vault` / `molit-apartment-transactions`
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

### 재로그인이 필요할 때 — 이 순서로 시도하세요

1. **Didim Tool을 호출합니다.** 미인증 상태의 OAuth MCP Tool을 호출하면 호스트가 자기
   인증 흐름을 띄웁니다(OAuth MCP 규격). 이것이 정본 경로입니다.
2. **설정 → MCP 서버**의 **Authenticate** 동작을 사용합니다. Codex 문서가 안내하는
   호스트 측 경로입니다. 다만 플러그인 제공 항목에 항상 노출되지는 않습니다.
3. **최후수단으로 플러그인을 재설치**합니다. 마켓플레이스 정책이 `ON_INSTALL`이므로 설치
   시점 로그인이 다시 실행됩니다. 1·2가 안 될 때만 쓰세요.

### 확인된 것과 확인되지 않은 것

- **확인됨** — 설치 시점의 Microsoft 로그인 화면은 실제로 뜹니다(마켓플레이스 정책이
  `ON_INSTALL`). Tool 호출은 호스트의 인증 흐름을 유발합니다. 로그인 창을 닫아도 등록은
  유지됩니다.
- **확인되지 않음** — 검증에 사용한 Codex 앱 UI에서는 플러그인 제공 `didim-mcp` 항목에
  Connect / Disconnect 버튼이나 톱니 아이콘이 **없었습니다.** 앱에 저장된 Didim 로그인을
  Skill이 직접 지우는 방법도 확인되지 않았습니다. 따라서 같은 계정으로 **강제** 재로그인은
  보장할 수 없고, 계정 변경은 위 3단계를 순서대로 시도해야 합니다. 이후 Codex 릴리스에서
  UI가 추가될 수 있습니다.

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
- 기본 실행은 **어떤 프로세스도 건드리지 않습니다.** Codex 프로세스를 스크립트가 닫게 하려면
  `-KillCodexProcesses`를 붙이세요(확인 프롬프트 기본값은 No, `-KillWithoutConfirmation`으로
  생략 가능). 레거시 블록이 없으면 아무것도 바꾸지 않고 끝나며, 여러 번 실행해도 안전합니다.
- 정리 후: Codex 완전 종료 → 재실행 → Didim Tool 호출 → Microsoft 로그인.
  (`codex mcp login didim-mcp`은 **별도로 설치한 `codex` CLI 전용**입니다. Codex 앱의 로그인
  경로가 아닙니다.)
- 이전에 생성된 `config.toml.backup-*` 파일에는 예전 키가 그대로 남아 있습니다. 필요 없으면
  삭제하세요.

---

## 사용 예

연결이 끝나면 자연어로 요청합니다. Tool 목록은 플러그인에 박혀 있지 않고, 접속할 때마다
MCP 서버가 `tools/list`로 **로그인한 사용자에게 허용된 것만** 내려줍니다. 따라서 사람마다,
포털 설정 변경 시점마다 보이는 Tool이 다를 수 있습니다.

```
지금 Didim MCP 누구로 로그인돼있어?
내가 쓸 수 있는 Didim MCP 도구를 보여줘
구로구 지난달 아파트 매매 실거래가 알려줘
구로구 지난달 아파트 전월세 실거래가 알려줘
```

> 위 예시 중 앞의 세 개는 플러그인이 Codex 화면에 노출하는 기본 예시 발화입니다
> (`plugin.json`의 `interface.defaultPrompt`). 그 밖에 무엇을 물을 수 있는지는 포털에서
> 어떤 Tool을 켰는지에 따라 달라집니다.

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

필요한 MCP Tool (조회하려는 거래 유형에 맞게 **[Didim MCP 포털](https://didimmcp-dev.didimservice.com/)에서
활성화** 후 Codex 재시작):
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
│       ├── didim-mcp-connect/SKILL.md        # 연결·재연결·문제 해결  ← **정적 유지**
│       ├── didim-mcp-usage/SKILL.md          # thin router → mcp.usage
│       ├── didim-vault/SKILL.md              # thin router → vault.resource
│       ├── molit-apartment-transactions/SKILL.md  # thin router → molit.apartment-transactions
│       └── didim-dynamic-skill/SKILL.md        # generic fallback → 목록 조회 후 선택
│
├── app/                                      # ← Skill Registry (FastAPI). 설치본에 포함되지 않음
│   ├── api/          deps(인가 가드) · dto · mappers · health · v1/{admin_skills,admin_audit,runtime_skills,me}
│   ├── auth/         JWT 검증(RS256/JWKS) · Auth client · Principal
│   ├── core/         config · logging · errors
│   ├── db/           base · schema · session · models/{skill,audit}
│   ├── domain/       enums · validators
│   ├── repositories/ skill · audit
│   ├── services/     skill_service(초안/배포/롤백) · audit_service
│   ├── seed/         정적 SKILL.md → DB 초기 이관 스냅샷(1회용)
│   ├── web/          session(HttpOnly 쿠키·CSRF) · sso · routes(/login,/logout) · spa
│   └── main.py
├── web/                                      # ← React Admin (Vite + React 19 + TS + Tailwind v4)
│   ├── src/{components,lib,pages,types}
│   └── package.json
├── alembic/                                  # mcp_skill_registry migration (이 저장소가 owner)
├── tests/                                    # pytest (단위 + PostgreSQL 통합)
├── certs/                                    # 사내망 FortiGate CA (빌드용, 비밀 아님)
├── Dockerfile                                # React 빌드 + FastAPI 런타임 = 단일 image
├── Jenkinsfile                               # Harbor build/push (deploy 자동 push 없음)
├── pyproject.toml · uv.lock · alembic.ini
├── CLAUDE.md                                 # 리포 작업용 에이전트 지시문 (배포 안 됨)
├── .claude/rules/                            # 경로 스코프 작업 규칙 (배포 안 됨)
└── README.md
```

> 현재 플러그인 버전은 `plugins/didim-mcp/.codex-plugin/plugin.json`의 `version` 필드가
> 기준입니다. (이 도식에 버전을 중복 표기하지 않습니다.)

> **설치본에 들어가는 것은 여전히 `plugins/didim-mcp/` 뿐입니다.** Codex는 설치 시 플러그인
> 디렉터리만 배포하므로 `app/`·`web/`·`alembic/`·`tests/`는 사용자 PC로 가지 않습니다.
> 같은 이유로 스크립트는 반드시 `plugins/didim-mcp/scripts/` 안에 있어야 합니다.

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
| 예전 `X-Didim-Vault-Api-Key` 헤더나 예전 평문 HTTP URL로 붙어 있음 | 같은 원인입니다. 위 정리 스크립트를 실행하세요 |
| 다른 Microsoft 계정으로 바꾸고 싶음 | 위 **재로그인 순서**를 그대로 따르세요(Tool 호출 → 설정의 Authenticate → 최후수단 재설치). Microsoft 화면이 뜨면 **"다른 계정으로 로그인"** 을 선택하세요 — SSO 세션이 남아 있으면 같은 계정으로 자동 로그인됩니다 |
| **Didim Tool이 하나도 안 보임** (`/mcp`에는 `사용함 / 인증됨(OAuth)`) | **포털 권한 문제가 아닙니다.** Codex가 저장해 둔 로그인을 갱신하려다 서버에서 거부되면 MCP 서버가 아예 기동하지 않고, 그래도 `/mcp` 배지는 `인증됨`으로 남습니다. Codex를 완전히 재시작한 뒤 Didim Tool을 호출해 로그인 창이 뜨는지 확인하세요. 그다음 설정 → MCP 서버의 **Authenticate**, 그래도 안 되면 최후수단으로 플러그인 재설치(설치 시점 로그인 재실행) |
| 연결은 됐는데 **특정** Tool만 없음 (다른 Didim Tool은 정상) | 인증 문제가 아닙니다. **Didim 사용자 포털에서 해당 Tool을 활성화**한 뒤 Codex 재시작 |
| 한동안 쓰다가 갑자기 인증 실패 | Codex가 먼저 refresh를 시도하고, 서버가 그 refresh를 거부하면 재로그인이 필요합니다. Didim Tool을 다시 호출해 로그인 요구가 뜨는지 확인하세요 |
| 설치가 안 됨 | 플러그인 화면에 **Didim** 마켓플레이스가 추가됐는지 확인 (CLI 사용자는 `codex plugin marketplace list`) |
| 스크립트 출력에 경로의 한글이 `??`로 깨져 나옴 | Windows PowerShell 5.1의 UTF-8 처리 문제입니다. 스크립트가 UTF-8 BOM + `chcp 65001` + 콘솔 인코딩을 적용하지만, 콘솔 폰트·코드페이지에 따라 사용자 이름 등 비ASCII 경로가 깨질 수 있습니다. 표시만 깨지는 것이고 정리 결과는 정상입니다 |
| **Skill이 예전 절차대로 동작함** | 절차는 이제 DB에 있습니다. Admin Web에서 **배포**까지 했는지 확인하세요 — 초안 저장만으로는 반영되지 않습니다 |
| Registry Tool(`didim-skill__*`)이 안 보임 | 다른 Didim Tool이 보이면 포털 권한 문제입니다. 포털에서 Didim Skill Registry Tool을 활성화하고 Codex 재시작. 하나도 안 보이면 연결 문제입니다 |
| Admin Web에서 "접근 권한이 없습니다" | 스킬 관리는 ADMIN 전용입니다. 중앙 사용자 role(`didim_mcp_auth.users.role`)을 담당자에게 요청하세요 |
| Admin Web에서 배포 버튼이 409를 냄 | 다른 관리자가 방금 배포했습니다. 새로고침 후 다시 시도하세요(동시 배포는 DB가 막습니다) |

---

## Dynamic Skill Registry (운영자 · 개발자)

여기부터는 **운영자와 개발자** 대상입니다. 일반 사용자는 위 절까지만 읽으면 됩니다.

### 왜 만들었나

| 예전 (정적 SKILL.md) | 지금 (Skill Registry) |
| --- | --- |
| 업무 절차 한 줄 수정 → 소스 수정 | Admin Web에서 초안 편집 |
| → 커밋 → 플러그인 버전 올림 → push | → 배포 버튼 |
| → 사용자가 마켓플레이스 갱신 + 재설치 | → 즉시 반영(재설치 없음) |
| 버전·롤백 개념 없음 | 버전 이력 + 롤백 |
| 운영자가 Git을 알아야 함 | 웹 화면 |

### 구조

```
                Microsoft Entra
                       │
                       ▼
                  DIDIM Auth  (didim-mcp-auth-backend)
                  신원 · role 정본 · 토큰 발급 · 위임
                       │
        ┌──────────────┴───────────────┐
        │ 브라우저 SSO                  │ 위임 토큰(act.sub=mcp)
        ▼                              ▼
┌─────────────────────────┐   ┌──────────────────────┐
│ didim-mcp-codex-plugin  │◀──│ didim-mcp-service-   │
│  FastAPI                │   │ backend (MCP Gateway)│
│  ├ /api/v1/admin/**     │   │  didim-skill__*      │
│  ├ /api/v1/runtime/**   │   │  Tool 인가 정본      │
│  ├ /login · /logout     │   └──────────▲───────────┘
│  └ React Admin SPA      │              │ Streamable HTTP
└───────────┬─────────────┘              │
            ▼                         Codex + Plugin
      PostgreSQL                   (thin router SKILL.md)
    mcp_skill_registry
```

### Codex → Dynamic Skill runtime flow

```
1. 사용자 발화
2. Codex가 SKILL.md frontmatter description 으로 Skill 선택   ← 여전히 정적이다
3. thin router SKILL.md 실행: "didim-skill__get_skill(skill_key) 를 불러라"
4. MCP gateway 가 Tool 실행
     → Auth /token/delegate 로 이 서비스 audience 토큰 발급
     → GET /api/v1/runtime/skills/{skill_key}
5. Registry 가 PUBLISHED + enabled 버전의 instructions 반환
6. Codex 가 그 절차를 수행하며 다른 Didim Tool 호출
7. 그 Tool 호출의 인가는 MCP gateway 가 판단          ← Registry 는 관여하지 않는다
```

**Skill 선택(2단계)은 여전히 정적 frontmatter가 결정합니다.** Codex의 Skill selector가
DB를 읽지 않기 때문입니다 — 그래서 트리거 문구는 SKILL.md에 남고, **본문(절차)만** DB로
갔습니다.

#### 그럼 새로 등록한 Skill은 어떻게 발견되나 — `didim-dynamic-skill`

전용 라우터가 없는 새 Skill(예: 운영자가 오늘 Admin Web에서 만든 `hr.leave-status`)을
위해 **generic fallback router** 하나를 둡니다.

```
사용자: "디딤 연차 신청 절차 알려줘"
  → Codex 가 didim-dynamic-skill 선택 (전용 router 가 없으므로)
  → didim-skill__list_skills            현재 배포된 목록을 가져온다
  → name / description / aliases / category 로 Codex 가 skill_key 선택
  → didim-skill__get_skill("hr.leave-status")
  → 그 instructions 수행
```

**이 경로에는 플러그인 릴리스가 필요 없습니다.** Publish 즉시 목록에 나타나고, 그
순간부터 발견 가능합니다.

Backend에 semantic search·embedding·vector DB를 넣지 않았습니다. 선택은 Codex가 목록의
`name`/`description`/`aliases`를 읽고 합니다 — 새 인프라 없이 되는 일입니다.

| | 전용 thin router (3개) | `didim-dynamic-skill` |
| --- | --- | --- |
| 트리거 정확도 | 높음(문구를 직접 씀) | 보통(Didim을 명시해야 함) |
| 왕복 | 1회(`get_skill`) | 2회(`list_skills` → `get_skill`) |
| 새 Skill 발견 | 불가(릴리스 필요) | **가능** |

전용 라우터 3개를 없애지 않았습니다. 트리거 정확도가 높고 왕복이 한 번 적기 때문입니다.
generic router는 **Didim을 명시했는데 전용 router가 없을 때만** 걸리도록 description을
좁게 썼습니다 — 일반 프로그래밍·일반 지식 질문을 잡으면 안 됩니다.

여전히 정적인 것은 하나입니다: **트리거 문구 자체를 바꾸려면** 플러그인 릴리스가
필요합니다(`didim-dynamic-skill`의 description을 고치는 경우).

### Skill 분류 (이관 결과)

| Skill | 분류 | 결과 |
| --- | --- | --- |
| `didim-mcp-connect` | **A. bootstrap / safety invariant** | 정적 유지(339줄 그대로) |
| `didim-mcp-usage` | B. 업무 workflow | DB `mcp.usage` + thin router 82줄 |
| `didim-vault` | B. 업무 workflow (+ secret 규칙) | DB `vault.resource` + thin router 72줄 |
| `molit-apartment-transactions` | B. 업무 workflow | DB `molit.apartment-transactions` + thin router 86줄 |
| `didim-dynamic-skill` | **신규 · generic fallback router** | 본문 없음. 목록 조회 → 선택 → 조회 |

`didim-mcp-connect`를 DB로 옮기지 않은 이유는 단순합니다 — **연결이 끊긴 상태를 다루는
Skill인데, 연결이 끊기면 Registry Tool도 부를 수 없습니다.** 자기 자신을 못 가져오는
절차가 됩니다.

router에 남긴 것은 셋뿐입니다: **언제 Registry를 조회할지 · 어떤 `skill_key`인지 ·
Registry가 없을 때 무엇을 하지 말지(안전 invariant)**.

### Microsoft SSO

새 로그인 시스템을 만들지 않았습니다. 기존 DIDIM Auth를 그대로 재사용합니다.

```
브라우저 → GET /login                    (서버가 자동 SSO 여부 판정 — loop guard 쿠키가 HttpOnly)
        → GET /login/microsoft           (flow state 쿠키 생성 + Auth로 302)
        → Auth /api/v1/auth/microsoft/login?service=skill&service_flow_state=…
        → Microsoft Entra 로그인 · MFA
        → Auth callback (ID Token 검증)
        → GET /login/microsoft/callback?code=<1회용>&state=<flow state>
        → 쿠키와 state를 constant-time 대조 (login CSRF 차단)
        → Auth POST /api/v1/auth/microsoft/exchange (server-to-server)
        → Access/Refresh 를 HttpOnly 쿠키로 저장 → /admin/skills
```

- 이 서비스는 **Microsoft/Azure와 직접 통신하지 않습니다.** Entra ID Token 검증도 Graph
  조회도 Auth만 합니다.
- 토큰은 URL·history·HTML 어디에도 실리지 않습니다.
- 통합 로그아웃(SLO)은 Auth가 각 서비스의 front-channel 경로를 순회시킵니다
  (`/logout/frontchannel`).

### ADMIN authorization

| 호출자 | `/api/v1/admin/**` | `/api/v1/runtime/**` |
| --- | --- | --- |
| 미인증 | **401** | **401** |
| 인증된 USER / DEVELOPER | **403** | 200 |
| 인증된 ADMIN | 200 | 200 |
| MCP 위임 토큰(`act` 보유) | **403** | 200 |

- **role 정본은 Auth `GET /api/v1/me`의 `role`** 입니다. JWT에 role claim이 없습니다.
  매 요청 Auth에 물으므로 계정을 강등/비활성하면 토큰 TTL과 무관하게 즉시 막힙니다.
- 가드는 개별 endpoint가 아니라 `app/api/v1/router.py`의
  `include_router(..., dependencies=[Depends(require_admin)])`에 붙습니다 — 새 관리
  endpoint를 추가하면서 가드를 빠뜨릴 수 없는 구조입니다.
- **화면에서 메뉴를 감추는 것은 인가가 아닙니다.** React는 `is_admin`으로 메뉴를 그릴지만
  정하고, 차단은 backend가 합니다.
- 위임 토큰으로는 관리 API를 쓸 수 없습니다 — 관리 작업은 사람이 브라우저/Swagger에서 합니다.

### DB

기존 DIDIM PostgreSQL(사내 호스트, DB `didim_api`)을 **그대로 씁니다.** 새 인스턴스도
새 database도 만들지 않습니다. 이 프로젝트가 소유하는 것은 **schema 하나**입니다.

```
didim_api
├── didim_mcp_auth     (didim-mcp-auth-backend — 사용자 정본)
├── didim_vault        (didim-vault-backend)
├── didim_mcp          (didim-mcp-service-backend)
├── didim_rag          (didim-rag-backend)
└── mcp_skill_registry ← 이 프로젝트가 migration owner
```

| 테이블 | 역할 |
| --- | --- |
| `skills` | Skill identity. `skill_key` unique, `enabled`, `published_version_id` |
| `skill_versions` | 버전별 실제 workflow. `(skill_id, version)` unique, status DRAFT/PUBLISHED/SUPERSEDED |
| `skill_version_aliases` | **버전 종속** 라우팅 alias |
| `skill_version_tools` | **버전 종속** Tool 목록 — orchestration 정보이지 권한이 아니다 |
| `audit_logs` | 변경 이력(조회는 기록하지 않음) |

alias/tool을 skill-level이 아니라 **version-level**에 둔 이유: 롤백하면 본문만이 아니라
그 버전의 라우팅과 Tool 목록도 함께 돌아가야 하기 때문입니다.

핵심 제약:

- `uq_skills_skill_key`
- `uq_skill_versions_skill_id_version`
- **`uq_skill_versions_one_published`** — `WHERE status = 'PUBLISHED'` 부분 unique index.
  한 Skill에 배포본은 하나뿐이라는 사실을 애플리케이션이 아니라 **DB가** 강제합니다.

Migration head: **`0002_seed_initial_skills`**

### Skill lifecycle (Draft / Publish / Rollback)

```
생성           → v1 DRAFT                    (등록만으로는 배포되지 않음)
배포           → v1 PUBLISHED
수정           → v2 DRAFT (배포본 복사)
배포           → v2 PUBLISHED, v1 SUPERSEDED
롤백(v1 지정)  → v1 내용으로 **새 v3** 생성 → v3 PUBLISHED, v2 SUPERSEDED
```

- **과거 행을 되살리지 않습니다.** 롤백은 새 버전을 만들고 `rolled_back_from`에 원본 번호를
  남깁니다 — 그래야 "언제 무엇으로 되돌렸는가"가 이력에 남습니다.
- 배포된 버전은 **불변**입니다. 수정하려면 새 초안을 만듭니다.
- 초안은 한 Skill에 **하나**입니다. 두 관리자가 동시에 편집해 서로를 덮는 상황을 만들지
  않습니다(두 번째 요청은 409).
- 배포는 원자적입니다: `SELECT ... FOR UPDATE`로 직렬화하고, DB의 부분 unique index가
  최후 방어선입니다.

### Backend API

| Method | Path | 인가 |
| --- | --- | --- |
| GET | `/api/v1/admin/skills` | ADMIN. `search` `category` `enabled` `status` `sort` `page` `page_size` |
| GET | `/api/v1/admin/skills/categories` | ADMIN |
| POST | `/api/v1/admin/skills` | ADMIN. identity + v1 초안 |
| GET / PATCH | `/api/v1/admin/skills/{id}` | ADMIN. `skill_key`는 변경 불가 |
| PATCH | `/api/v1/admin/skills/{id}/enabled` | ADMIN |
| GET | `/api/v1/admin/skills/{id}/versions` | ADMIN |
| GET | `/api/v1/admin/skills/{id}/versions/{version}` | ADMIN |
| POST | `/api/v1/admin/skills/{id}/versions` | ADMIN. 본문 생략 시 배포본 복사 |
| PUT / DELETE | `/api/v1/admin/skills/{id}/versions/{version}` | ADMIN. **초안만** |
| POST | `/api/v1/admin/skills/{id}/publish` | ADMIN |
| POST | `/api/v1/admin/skills/{id}/rollback` | ADMIN |
| GET | `/api/v1/admin/audit-logs` | ADMIN |
| GET | `/api/v1/runtime/skills` | 인증(role 무관). 본문 없음 |
| GET | `/api/v1/runtime/skills/{skill_key}` | 인증(role 무관). 본문 포함 |
| GET | `/api/v1/runtime/openapi.json` | MCP gateway 등록용 **읽기 전용** 문서 |
| GET | `/api/v1/me` | 없음(미인증도 200) |
| GET | `/health` `/ready` | 없음 |

오류 본문은 `{"error": {"code": "...", "message": "..."}}`입니다. 요청 스키마 검증 실패(422)만
FastAPI 기본 형식입니다.

### React Admin 화면

| 화면 | 내용 |
| --- | --- |
| 로그인 | Microsoft 버튼 하나. USER는 로그인 후 "접근 권한이 없습니다" |
| 스킬 목록 | 검색 · 카테고리/상태/사용여부 필터 · 정렬 · 20/50/100 페이징. 열: 스킬·카테고리·배포 버전·상태·사용 여부·최근 수정·관리 |
| 스킬 상세 | 현재 배포본(초록) / 초안(주황)이 **시각적으로 구분** |
| 새 스킬 등록 | identity + v1 초안 |
| 초안 편집 | 이름·설명·별칭·사용할 도구 + Markdown 편집/미리보기 |
| 버전 이력 | 버전·상태·작성자·배포자, 지난 배포에만 롤백 버튼 |
| 배포 / 롤백 | **확인 modal** — 무엇이 바뀌는지 문장으로 설명 |
| 변경 이력 | 작업자·작업·대상·결과 |

용어는 한국어로, 기술 용어를 노출하지 않습니다(`PUBLISHED` → "배포됨",
`SUPERSEDED` → "지난 배포"). 표시 매핑의 정본은 `web/src/lib/labels.ts` 하나입니다.

### 보안 경계

- **Tool 인가 정본은 MCP gateway입니다.** `skill_version_tools`에 ADMIN이
  `some_admin_delete_tool`을 적어도 일반 USER가 그 Tool을 부를 수 있게 되지 않습니다.
  Registry는 이 경계를 우회할 수 없습니다(테스트로 고정).
- MCP gateway에 등록할 OpenAPI는 **`/api/v1/runtime/openapi.json`** 입니다. 전체
  `/openapi.json`을 등록하면 `publish`·`rollback`이 Tool 후보로 올라옵니다.
- 감사에 raw token·Authorization 헤더·세션 쿠키·본문을 넣지 않습니다(키 기준 필터 + 테스트).
- Frontend 번들에 DB credential·OAuth client secret·Vault token이 없습니다. 토큰을 다루는
  코드 자체가 없습니다 — 인증은 HttpOnly 쿠키로 성립합니다.
- CSRF는 세션 쿠키 경로에만 더블 서브밋으로 적용합니다(Bearer 경로는 불요).

### 장애 시 동작 (fail-closed)

| 상황 | 동작 |
| --- | --- |
| DB 연결 불가 | `/ready` 503, API 503. **빈 목록이나 오래된 캐시로 위장하지 않는다** |
| Auth 연결 불가 | 401(신원 확인 불가). 통과시키지 않는다 |
| JWKS 조회 불가 | 503(검증 불가). "토큰이 나쁘다"로 오해하게 하지 않는다 |
| Registry Tool 미노출 | thin router가 **절차를 지어내지 않고** 중단 + 원인별 안내 |
| skill_key 미배포 | runtime 404. "있지만 배포 전"이라는 사실도 알리지 않는다 |
| Skill disabled | runtime 404 |

### 로컬 개발

```bash
# 1) PostgreSQL (테스트용 일회성)
docker run -d --name pgtest-skill -e POSTGRES_USER=pgtest -e POSTGRES_PASSWORD=pgtest \
  -e POSTGRES_DB=pgtest -p 55433:5432 postgres:16-alpine

# 2) migration + seed
export DIDIM_SKILL_DB_HOST=127.0.0.1 DIDIM_SKILL_DB_PORT=55433 \
       DIDIM_SKILL_DB_USER=pgtest DIDIM_SKILL_DB_PASSWORD=pgtest DIDIM_SKILL_DB_NAME=pgtest
uv sync --dev
uv run alembic upgrade head

# 3) backend (인증 끄고)
export DIDIM_SKILL_AUTH_ENABLED=false DIDIM_SKILL_RUNTIME_AUTH_REQUIRED=false
uv run uvicorn app.main:app --host 127.0.0.1 --port 8080     # Swagger: /docs

# 4) frontend (별도 터미널). /api 는 vite proxy 가 8080 으로 넘긴다
cd web && npm install && npm run dev                          # http://127.0.0.1:5173
```

`DIDIM_SKILL_AUTH_ENABLED=false`는 **로컬 전용**입니다. 이때 화면은 가짜 ADMIN으로 동작합니다.

### 환경변수

전부 prefix `DIDIM_SKILL_`. 정본은 `app/core/config.py`이고, dev 값은 deploy 저장소의
ConfigMap입니다. 앱이 `extra="ignore"`라 **오타 키는 조용히 무시됩니다.**

| 키 | 기본 | 설명 |
| --- | --- | --- |
| `ENV` | `local` | `local` / `dev` / `prod` |
| `LOG_LEVEL` `HOST` `PORT` | `INFO` `0.0.0.0` `8080` | |
| `DB_HOST` `DB_PORT` `DB_USER` `DB_PASSWORD` `DB_NAME` | — | 미설정 시 bootstrap 모드 |
| `DATABASE_SCHEMA` | `mcp_skill_registry` | **바꾸지 않는다** |
| `AUTH_ENABLED` | `false` | 운영 `true`. false면 무인증 |
| `AUTH_BASE_URL` | — | Auth 내부 주소(server-to-server) |
| `AUTH_PUBLIC_BASE_URL` | — | Auth 공개 주소(브라우저). 비면 로그인 버튼 미노출 |
| `AUTH_PROFILE_PATH` | `/api/v1/me` | role 정본 조회 경로 |
| `JWT_RS256_ENABLED` `JWT_JWKS_URL` | `true` / 유도 | 비우면 `{AUTH_BASE_URL}/.well-known/jwks.json` |
| `JWT_ISSUER` `JWT_AUDIENCE` | `didim-vault` `didim-services` | 발급자와 일치해야 함 |
| `JWT_SERVICE_AUDIENCE` | — | Auth `JWT_SERVICE_AUDIENCES`와 글자 단위 일치 |
| `JWT_LEGACY_HS256_ACCEPTED` | `false` | 대칭키 허용(전환기 전용) |
| `SESSION_SECRET` | — | **AUTH_ENABLED=true면 필수**(없으면 기동 실패) |
| `SESSION_TTL_SECONDS` `COOKIE_SECURE` `COOKIE_SAMESITE` | `3600` `false` `lax` | HTTPS면 secure=true |
| `RUNTIME_AUTH_REQUIRED` | `true` | false면 workflow 전문이 익명 공개 |
| `SPA_DIR` | `web/dist` | 없으면 API만 서비스 |
| `DEFAULT_PAGE_SIZE` `MAX_PAGE_SIZE` | `20` `100` | |

### Migration

**앱 기동 시 자동 실행되지 않습니다**(의도적). 별도 Job입니다.

```bash
uv run alembic upgrade head      # 로컬
# 운영: deploy 저장소의 apps/didim-mcp-codex-plugin/migration-job.yaml 을 1회 apply
```

`0002_seed_initial_skills`가 기존 정적 SKILL.md 본문을 초기 배포본 v1로 넣습니다.
**멱등**이라 이미 있는 `skill_key`는 건너뜁니다 — 운영 중 Admin Web에서 고친 내용을
되돌리지 않습니다. seed 이후 runtime은 DB만 읽고, 운영 수정은 소스가 아니라 Admin Web에서
합니다.

### 테스트 · 검증

```bash
# backend
uv run ruff format --check .
uv run ruff check .
uv run mypy app
uv run pytest                                   # 단위 (PostgreSQL 통합은 skip)

# PostgreSQL 통합(동시 publish · 부분 unique index) — skip 수를 반드시 확인한다
docker run -d --name pgtest-skill -e POSTGRES_USER=pgtest -e POSTGRES_PASSWORD=pgtest \
  -e POSTGRES_DB=pgtest -p 55433:5432 postgres:16-alpine
DIDIM_SKILL_TEST_DATABASE_URL="postgresql+asyncpg://pgtest:pgtest@127.0.0.1:55433/pgtest?ssl=disable" \
  uv run pytest tests/integration -m integration

# frontend
cd web && npm run typecheck && npm run lint && npm run test && npm run build

# 플러그인 매니페스트
python3 -m json.tool .agents/plugins/marketplace.json > /dev/null
python3 -m json.tool plugins/didim-mcp/.codex-plugin/plugin.json > /dev/null

git diff --check
```

⚠ **"N skipped"를 성공으로 오해하지 않습니다.** PostgreSQL 통합 테스트는 DSN이 없으면
조용히 skip되고 전체가 green으로 보입니다.

### Docker

```bash
docker build -t didim-mcp-codex-plugin:local .
```

4-stage: `web-deps`(npm ci) → `web-build`(tsc + vite) → `api-builder`(uv sync) →
`runtime`. 최종 image에 node도 node_modules도 devDependencies도 없습니다.
비루트(uid/gid 999), `/health` stdlib healthcheck, port 8080.

`certs/`의 FortiGate CA는 사내망 빌드·런타임 TLS 검사 대응입니다(공개 CA 인증서, 비밀 아님).

### Jenkins / Harbor

| 항목 | 값 |
| --- | --- |
| Jenkins job | `didim-mcp-codex-plugin-dev` (신규 생성 필요) |
| Harbor project | `didim-mcp-codex-plugin` (신규 생성 필요) |
| Image | `<harbor-host>/didim-mcp-codex-plugin/app:sha-<7hex>` (+ `:dev`) |

Pipeline: checkout → Init → **Plugin manifests**(매니페스트·thin router 무결성) →
**Prepare CA** → Build → **Smoke**(컨테이너 기동 + `/health`) → Push Harbor →
**Report image tag**.

> **이 저장소는 public입니다.** 사내 Harbor 주소를 소스에 적지 않았습니다. Jenkins의
> 전역 환경변수(또는 job 파라미터) `HARBOR_REGISTRY`에서 읽고, 비어 있으면 Init에서
> 명시적으로 실패합니다. 실제 값은 deploy 저장소(private)의 `kustomization.yaml`에
> 있는 것과 같습니다.
>
> 사내망 TLS 검사 CA(`certs/*.crt`)도 커밋하지 않습니다. Jenkins Secret file 자격증명
> `didim-fortigate-ca`가 Prepare CA stage에서 넣습니다 — 자세한 내용은
> [`certs/README.md`](certs/README.md).

> **deploy 저장소 자동 commit/push 단계를 두지 않았습니다.** 다른 DIDIM 파이프라인은 image
> tag를 자동 push하지만, 이 프로젝트는 "commit/push는 사람이 한다"는 정책이라 그 동작을
> 의도적으로 복사하지 않았습니다. 마지막 stage가 태그와 다음 할 일을 출력합니다.

### Kubernetes / ArgoCD

배포 선언은 [`didim-mcp-codex-plugin-deploy`](https://github.com/didim365/didim-mcp-codex-plugin-deploy)에
있습니다.

| 항목 | 값 |
| --- | --- |
| Namespace | `didim-mcp-codex-plugin` |
| Deployment | `didim-mcp-codex-plugin` (**1개** — frontend/edge Pod 없음) |
| Service | NodePort `31085` |
| Migration Job | `didim-mcp-codex-plugin-migration` (수동 1회) |
| ArgoCD Application | `didim-mcp-codex-plugin-dev`, `targetRevision: develop`, `path: environments/dev` |

### 초기 배포 순서 (빈 namespace 기준)

**의존성이 있는 순서입니다.** 건너뛰면 다음 단계가 실패하도록 되어 있습니다 — 특히 3번을
빼면 4번 Pod이 영원히 NotReady로 남습니다(`/ready`가 schema 없음을 503으로 보고합니다).
명령은 사람이 NCP 서버에서 직접 실행합니다.

| # | 단계 | 무엇에 막히나 | 검증 |
| --- | --- | --- | --- |
| 0 | Auth에 `skill` 서비스 등록 (ConfigMap 4개 키) + Auth rollout | 여기가 없으면 7·8이 실패한다. **DNS 이름을 먼저 정해야** callback URL을 등록할 수 있다 | Auth Pod 재기동 후 `/auth/microsoft/login?service=skill` 이 400이 아니어야 한다 |
| 1 | Admin 도메인 DNS → NCP 서버 (이름은 배포 저장소에 있음) | 0번의 callback URL과 글자 단위로 같아야 한다 | `nslookup` |
| 2 | Harbor project 생성 → Jenkins job 생성(`HARBOR_REGISTRY`, `didim-fortigate-ca` 자격증명 포함) → 빌드 1회 | image가 없으면 3·4가 `ImagePullBackOff` | Harbor에 `sha-<7hex>` 태그 |
| 3 | namespace + Secret 2개(`didim-mcp-codex-plugin-secret`, `harbor-registry-secret`) | Secret 없으면 Pod이 뜨지 못한다 | `kubectl get secret` |
| 4 | **migration Job 1회** (`0001`+`0002`) | 앱은 기동 시 migration을 실행하지 않는다. 여기를 건너뛰면 5번이 NotReady | Job `complete`, 로그에 `0002_seed_initial_skills` |
| 5 | ArgoCD Application 적용 → Deployment rollout | 4번이 끝나야 Ready가 된다 | `Synced` / `Healthy` |
| 6 | host nginx server block(443 → 31085) + 재적재 | 외부 진입 | `curl -s https://<admin-도메인>/health` |
| 7 | `/ready` 확인 | DB·schema·SPA·JWKS 상태가 한 번에 나온다 | `schema_exists: true`, `status: ready` |
| 8 | ADMIN 계정으로 브라우저 로그인 (Microsoft SSO) | 0·1번이 정확해야 성공 | Admin 목록 화면에 seed 3건 |
| 9 | USER 계정으로 403 확인 | 인가 경계 실증 | 관리 API 403 |
| 10 | MCP 관리 화면에서 Provider `didim-skill` 등록 (runtime OpenAPI import) | 5·6번 이후. Tool 2개가 생성된다 | `didim-skill__get_skill`, `didim-skill__list_skills` |
| 11 | 포털에서 사용자별로 그 Tool 활성화 | 안 켜면 라우터가 멈춘다 | `tools/list`에 노출 |
| 12 | 플러그인 설치/갱신 (`codex plugin add didim-mcp@didim`) | 10·11 이후여야 의미가 있다 | `codex plugin list` 에 0.3.0 |
| 13 | **Human UAT** | 아래 참조 | — |

UAT에서 반드시 보는 것 두 가지:

1. 전용 라우터 — "내 Vault 리소스 보여줘" → `didim-skill__get_skill("vault.resource")` 가
   실제로 호출되는가.
2. **동적 발견** — Admin Web에서 새 Skill을 하나 만들어 Publish한 뒤, **플러그인을 다시
   설치하지 않고** 그 주제를 물었을 때 `didim-dynamic-skill` 이 `list_skills` → `get_skill`
   로 찾아내는가. 이것이 이 프로젝트의 핵심 주장이고, 소스 레벨 테스트로는 증명되지
   않습니다(Codex의 selector는 외부 런타임입니다).

0번이 왜 맨 앞인가: Auth ConfigMap 변경은 Auth Pod 재기동을 수반하고, callback URL에는
1번의 DNS 이름이 들어갑니다. 도메인을 먼저 확정하지 않으면 0번을 두 번 하게 됩니다.

### MCP gateway 연결

`didim-mcp-service-backend`에 **OpenAPI Provider로 등록**합니다. MCP backend 코드는
고치지 않습니다.

| 항목 | 값 |
| --- | --- |
| Provider slug | `didim-skill` |
| base_url | `http://didim-mcp-codex-plugin.didim-mcp-codex-plugin.svc.cluster.local:8080` |
| OpenAPI | `<base_url>/api/v1/runtime/openapi.json` |
| auth_type | `REQUEST_HEADER_PASSTHROUGH` |
| auth_config | `{"target_header":"Authorization","target_scheme":"Bearer","oauth_upstream":"DELEGATED_TOKEN","oauth_delegation_service":"skill"}` |

생성되는 Tool: `didim-skill__get_skill`, `didim-skill__list_skills`
(`<provider_slug>__<operationId>` 규칙). thin router SKILL.md가 이 이름을 참조하므로
**slug를 바꾸면 SKILL.md도 함께 고쳐야 합니다.**

사용자는 Didim 포털에서 이 Tool을 활성화해야 합니다 — 다른 Didim Tool과 같은 규칙입니다.

---

## 참고

- 플러그인 문서: [`plugins/didim-mcp/README.md`](plugins/didim-mcp/README.md)
- 연결 Skill(정적): [`plugins/didim-mcp/skills/didim-mcp-connect/SKILL.md`](plugins/didim-mcp/skills/didim-mcp-connect/SKILL.md)
- 안전 사용 router: [`plugins/didim-mcp/skills/didim-mcp-usage/SKILL.md`](plugins/didim-mcp/skills/didim-mcp-usage/SKILL.md) → `mcp.usage`
- Vault 리소스 router: [`plugins/didim-mcp/skills/didim-vault/SKILL.md`](plugins/didim-mcp/skills/didim-vault/SKILL.md) → `vault.resource`
- 아파트 실거래가 router: [`plugins/didim-mcp/skills/molit-apartment-transactions/SKILL.md`](plugins/didim-mcp/skills/molit-apartment-transactions/SKILL.md) → `molit.apartment-transactions`
- **generic fallback router**: [`plugins/didim-mcp/skills/didim-dynamic-skill/SKILL.md`](plugins/didim-mcp/skills/didim-dynamic-skill/SKILL.md) → 배포된 Skill 중에서 고른다
- 배포 저장소: <https://github.com/didim365/didim-mcp-codex-plugin-deploy>
- 에이전트 지시문: [`CLAUDE.md`](CLAUDE.md) · [`.claude/rules/`](.claude/rules/)
