# Didim MCP — Codex Plugin

Codex CLI에서 **Didim MCP 서버**를 쉽게 설정하고 안전하게 사용하기 위한 플러그인입니다.
플러그인은 **MCP 서버를 직접 등록하지 않습니다.** 대신 두 개의 Skill과 설정 스크립트를 배포하고,
사용자가 "Didim MCP 설정해줘"라고 요청하면 Skill이 스크립트 실행을 제안해
개인 API Key를 사용자의 `~/.codex/config.toml`에 안전하게 기록합니다.

- **MCP 서버 URL:** `http://49.50.138.22:31083/mcp/`
- **인증 헤더:** `X-Didim-Vault-Api-Key`
- **개인 API Key 형식:** `dv_...`
- **키 저장 위치:** 사용자 PC의 `~/.codex/config.toml` (평문, 수동 등록과 동일한 보안 수준)

> 실제 `dv_` API Key는 이 저장소나 플러그인 파일에 절대 포함되지 않습니다.
> 키는 각 사용자의 로컬 `config.toml`에만 저장됩니다.

---

## 왜 설정 요청이 필요한가

Codex Plugin에는 설치 직후 자동으로 API Key를 입력받는 범용 post-install Hook이 없습니다.
따라서 **플러그인 설치만으로는 API Key가 등록되지 않습니다.** 설치 후 새 채팅에서
`Didim MCP 설정해줘` 라고 명시적으로 요청하면, `didim-mcp-setup` Skill이 감지하여
설정 스크립트 실행을 **사용자 승인 후** 진행합니다.

---

## 사용자 설치 · 설정 흐름 (Codex Windows 앱)

Codex Windows 앱의 화면 UI만으로 설치합니다. (별도 명령어 입력이 필요 없습니다.)

1. **Codex 앱**을 실행합니다.
2. 왼쪽에서 **플러그인**을 선택합니다.
3. **만들기**를 클릭합니다.
4. **마켓플레이스 추가**를 선택합니다.
5. **출처**에 다음을 입력합니다.
   ```
   https://github.com/didim365/didim-mcp-codex-plugin.git
   ```
6. **Git ref**와 **Sparse 경로**는 비워 둡니다.
7. **마켓플레이스 추가**를 클릭합니다.
8. 마켓플레이스 목록에서 **Didim MCP**를 **설치**합니다.
9. **새 채팅**에서 다음과 같이 요청합니다.
   ```
   Didim MCP 설정해줘
   ```
   `didim-mcp-setup` Skill이 다음을 안내합니다: 개인 API Key 입력 필요 · `config.toml` 자동 백업 및 수정 ·
   키는 이 PC의 `config.toml`에 평문 저장(수동 등록과 동일 수준).
10. **스크립트 실행 승인** — Skill이 제안하는 설정 스크립트 실행을 승인합니다.
11. **개인 `dv_...` Key 입력** — 별도 PowerShell 창에서 **숨김 입력**으로 키를 입력합니다.
    (채팅창에 붙여넣지 않습니다.)
12. **Codex 완전 종료 후 재실행** — 설정은 이미 저장되었지만, 반영하려면 Codex를 완전히 종료 후 다시 실행해야 합니다.
    (일부 환경은 즉시 재시작 시 설정이 반영되지 않습니다. 프로세스 종료 동작은 아래 "프로세스 종료" 참고.)
13. **`/mcp` 확인** — `didim-mcp` 서버와 노출된 도구를 확인합니다.
14. **일반 질문 시 자동 적용** — 이후 Didim 관련 질문에서 `didim-mcp-usage` Skill이 자동 적용됩니다.

### (선택) Codex CLI 사용자

Codex CLI를 **별도로 설치**한 사용자만 터미널에서 아래 명령을 사용합니다.

```bash
codex plugin marketplace add https://github.com/didim365/didim-mcp-codex-plugin.git
codex plugin add didim-mcp@didim
```

이후 새 채팅에서 `Didim MCP 설정해줘` 로 위 9번 이후 흐름과 동일하게 진행합니다.

> 위 CLI 절차는 `codex` CLI를 직접 설치한 경우에만 사용합니다.
> **Windows Store로 설치한 Codex 앱 내부의 `codex.exe`를 직접 실행하지 마세요.**

### 수동 실행 (대체 절차)

Skill이 스크립트를 실행하지 못하는 경우, 설치된 플러그인 폴더의 스크립트를 직접 실행합니다.

- 더블클릭: `%USERPROFILE%\.codex\plugins\cache\didim\didim-mcp\<version>\scripts\setup-didim-mcp.cmd`
- 또는 PowerShell:
  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.codex\plugins\cache\didim\didim-mcp\<version>\scripts\setup-didim-mcp.ps1"
  ```
- 저장소를 clone 한 경우 리포 안에서 직접:
  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File ".\plugins\didim-mcp\scripts\setup-didim-mcp.ps1"
  ```

스크립트가 자동으로 하는 일: `~/.codex` 및 `config.toml` 생성(없으면) → 변경 전 타임스탬프 백업 →
`dv_` 형식 검증 → `[mcp_servers.didim-mcp]` 블록만 추가/교체(다른 설정 보존) → UTF-8 저장.
여러 번 실행해도 `didim-mcp` 블록은 하나만 유지됩니다(멱등). **설정 저장은 프로세스 종료 성공 여부와 무관하게 먼저 완료됩니다.**

> **프로세스 종료 (setup):** 기본 매칭은 **정확히 일치하는 ProcessName `codex`뿐**입니다(부분 문자열 매칭 없음).
> - **별도 `.cmd` 창에서 실행한 경우:** 종료 대상 목록을 보여주고 `[y/N]`(기본 **N**) 확인 후에만 종료합니다.
> - **Codex 내부(Skill)에서 실행한 경우:** 현재 Codex 앱은 자동 종료할 수 없습니다. 스크립트는 종료를 시도하지 않고
>   "모든 Codex 창을 직접 종료 후 재실행"을 안내합니다.
> - 스크립트 자신의 프로세스와 모든 조상 PID는 **절대 종료하지 않습니다.**
> - 옵션: `-SkipProcessKill`(프롬프트 생략), `-KillWithoutConfirmation`(확인 없이 종료 — 위험, 신뢰 환경에서만),
>   `-ProcessNames @('codex')`(정확한 이름 커스터마이즈).
>
> **어떤 경우든 새 설정 반영에는 Codex 완전 재시작이 필요합니다.**

최종적으로 `config.toml`에 작성되는 형태:
```toml
[mcp_servers.didim-mcp]
url = "http://49.50.138.22:31083/mcp/"
startup_timeout_sec = 120

[mcp_servers.didim-mcp.http_headers]
X-Didim-Vault-Api-Key = "<사용자가 입력한 dv_ API Key>"
```

---

## API Key 변경 (교체 · 재발급 · 만료)

이미 Didim MCP를 등록한 사용자가 키를 바꿀 때도 **같은 setup 스크립트**를 다시 실행하면 됩니다.
플러그인 재설치·기존 설정 제거는 필요 없습니다.

1. Codex 새 채팅에서 `Didim MCP API Key 변경해줘` 입력
2. `didim-mcp-setup` Skill 안내 확인
3. 설정 스크립트 실행 승인
4. 별도 PowerShell 창에서 **새 `dv_` API Key 숨김 입력**
5. 기존 `config.toml`은 timestamp 백업
6. 기존 `didim-mcp` 블록이 새 키가 포함된 블록으로 **교체**(하나만 유지)
7. Codex 완전 종료 후 재실행
8. `/mcp`에서 연결 상태 확인

**명시:**
- 기존 키도, 새 키도 **채팅에 입력하지 않습니다**(새 키는 PowerShell 숨김 입력).
- 플러그인 재설치 불필요, 기존 MCP 설정 제거 불필요 — setup 재실행이 곧 교체입니다.
- 다른 MCP 서버 설정은 보존됩니다.
- 새 키 입력을 취소하거나(빈 값), `dv_` 형식이 아니면 **기존 설정은 그대로 유지**됩니다
  (검증 성공 후에만 백업·교체 수행).

---

## 아파트 실거래가 조회 (국토교통부)

지역명과 자연어 날짜만으로 국토교통부 아파트 **매매/전월세** 실거래가를 조회합니다.
`LAWD_CD`, `DEAL_YMD`, 10자리 법정동코드, serviceKey를 직접 입력할 필요가 없습니다
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

---

## 저장소 구조

```
.
├── .agents/plugins/marketplace.json          # Marketplace 매니페스트 (name: didim)
├── plugins/didim-mcp/
│   ├── .codex-plugin/plugin.json             # 플러그인 매니페스트 (v0.1.0, MCP 서버 미등록)
│   ├── README.md
│   ├── scripts/
│   │   ├── setup-didim-mcp.ps1               # config.toml에 didim-mcp 설정 작성 (멱등)
│   │   ├── setup-didim-mcp.cmd               # 더블클릭 실행 런처
│   │   ├── remove-didim-mcp.ps1              # didim-mcp 블록만 제거
│   │   └── remove-didim-mcp.cmd
│   └── skills/
│       ├── didim-mcp-setup/SKILL.md          # 최초 설정 · 문제 해결 (자동 선택)
│       ├── didim-mcp-usage/SKILL.md          # 안전 사용 (자동 선택)
│       └── molit-apartment-transactions/SKILL.md  # 국토교통부 아파트 실거래가 조회 (자동 선택)
├── .gitignore
└── README.md
```

> 참고: 설정 스크립트는 **플러그인 내부**(`plugins/didim-mcp/scripts/`)에 위치합니다.
> Codex는 플러그인 설치 시 플러그인 디렉터리만 배포하므로, Skill이 설치 후에도
> 스크립트를 찾을 수 있으려면 스크립트가 플러그인 안에 있어야 합니다.

---

## 업데이트 방법 (운영자 · 사용자)

운영자가 새 버전을 push 하면 사용자는 **Codex 앱의 플러그인 화면**에서 마켓플레이스를 갱신한 뒤
**Didim MCP**를 다시 설치(업데이트)합니다.

- **플러그인 업데이트는 사용자의 기존 키를 덮어쓰지 않습니다.** 키는 `config.toml`에 있고,
  플러그인 업데이트는 스크립트/스킬만 갱신합니다.
- MCP URL이나 인증 방식이 바뀐 경우에만 `Didim MCP 재설정` 요청(또는 setup 스크립트 재실행)이 필요합니다.

**(선택) Codex CLI 사용자** — 별도로 설치한 `codex` CLI를 쓰는 경우에만:
```bash
codex plugin marketplace upgrade
codex plugin add didim-mcp@didim
```

---

## 제거 방법

**Codex 앱의 플러그인 화면**에서 **Didim MCP**를 제거합니다.

**(선택) Codex CLI 사용자** — 별도로 설치한 `codex` CLI를 쓰는 경우에만:
```bash
codex plugin remove didim-mcp@didim
# (선택) codex plugin marketplace remove didim
```

`config.toml`의 Didim MCP 설정 제거(다른 설정은 보존, 제거 전 백업 생성):
- 더블클릭: `...\scripts\remove-didim-mcp.cmd`
- 또는:
  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File ".\plugins\didim-mcp\scripts\remove-didim-mcp.ps1"
  ```

> remove는 **기본적으로 프로세스를 종료하지 않습니다**(y/N 프롬프트도 없음). 제거 후 Codex를 직접 완전 종료·재실행하세요.
> 종료까지 원하면 `-KillCodexProcesses`(정확한 이름 `codex` 대상, `[y/N]` 기본 N)를 명시적으로 전달합니다.

### 백업 복원

setup/remove 실행 시 `config.toml.backup-YYYYMMDD-HHmmss` 백업이 생성됩니다. 복원하려면:
```powershell
Copy-Item "$env:USERPROFILE\.codex\config.toml.backup-YYYYMMDD-HHmmss" "$env:USERPROFILE\.codex\config.toml" -Force
```

---

## 보안 주의사항

- 실제 `dv_` API Key를 **저장소/플러그인 파일에 커밋하지 마세요.** 이 저장소에는 키가 없습니다.
- 키는 사용자 PC의 `~/.codex/config.toml`에 **평문**으로 저장됩니다(수동 MCP 헤더 등록과 동일 수준).
  공용 PC에서는 사용에 주의하세요.
- 키는 **PowerShell 숨김 입력**으로만 받으며, 채팅창/명령행 인자/로그에 노출하지 않습니다.
- Skill 규칙상 API Key·토큰·인증 헤더 등 비밀값은 응답에 그대로 노출하지 않습니다.
- 읽기 전용 작업을 우선하고, 데이터 변경·고위험 작업은 사용자 승인 후 진행합니다.
- `config.toml` 수정 전 항상 타임스탬프 백업이 생성됩니다.

---

## 문제 해결

| 증상 | 확인 / 조치 |
| --- | --- |
| 설치했는데 `/mcp`에 없음 | 설치만으로는 등록되지 않습니다. `Didim MCP 설정해줘` 요청 후 설정 스크립트 실행 |
| 설정했는데 안 보임 | Codex를 **완전히 재시작**했는지 확인 |
| `No Didim MCP tools are exposed` | `Didim MCP 재설정` 요청으로 setup 재실행, `dv_` 키가 유효/최신인지 확인 |
| 인증 실패 | `config.toml`의 `X-Didim-Vault-Api-Key` 값이 올바른 개인 `dv_` 키인지 확인 |
| 설치가 안 됨 | 플러그인 화면에 **Didim** 마켓플레이스가 추가됐는지 확인 (CLI 사용자는 `codex plugin marketplace list`) |
| 스크립트 실행 시 한글이 `??`/깨져서 나옴 | Windows PowerShell 5.1의 UTF-8 처리 문제입니다. **플러그인을 최신 버전(0.1.3 이상)으로 업데이트**하세요. 스크립트가 UTF-8 BOM + `chcp 65001` + 콘솔 인코딩을 적용해 한글을 정상 출력합니다. |

---

## 참고

- 플러그인 문서: [`plugins/didim-mcp/README.md`](plugins/didim-mcp/README.md)
- 최초 설정 Skill: [`plugins/didim-mcp/skills/didim-mcp-setup/SKILL.md`](plugins/didim-mcp/skills/didim-mcp-setup/SKILL.md)
- 안전 사용 Skill: [`plugins/didim-mcp/skills/didim-mcp-usage/SKILL.md`](plugins/didim-mcp/skills/didim-mcp-usage/SKILL.md)
- 아파트 실거래가 Skill: [`plugins/didim-mcp/skills/molit-apartment-transactions/SKILL.md`](plugins/didim-mcp/skills/molit-apartment-transactions/SKILL.md)
