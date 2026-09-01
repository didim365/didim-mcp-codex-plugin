---
paths:
  - "plugins/didim-mcp/scripts/**"
---

# PowerShell / CMD 스크립트 규칙

대상: `migrate-didim-mcp.ps1`, `migrate-didim-mcp.cmd`.
이 스크립트는 사용자의 실제 `~/.codex/config.toml`을 수정한다. 되돌리기 어려운 코드다.

## 이 스크립트의 유일한 역할

0.1.x가 남긴 레거시 `[mcp_servers.didim-mcp]` / `[mcp_servers.didim-mcp.*]` 블록 제거.
그 블록이 남아 있으면 `plugin.json`이 선언한 OAuth MCP 서버를 **가려서**(shadow) Connect가
동작하지 않는다(검증됨: 블록이 있으면 `codex mcp list`에 플러그인 서버가 아예 나오지 않는다).

여기에 **MCP 서버 등록 기능을 다시 넣지 않는다.** 등록은 `plugin.json`의 `mcpServers`가 한다.
**자격증명 입력 기능도 다시 넣지 않는다.** 인증은 Codex OAuth가 한다.

## 실행 환경

- **Windows PowerShell 5.1** 이 하한선이다(`#requires -Version 5.1`). PowerShell 7 전용 문법을
  쓰지 않는다: 삼항 연산자 `? :`, `??`, `-Parallel`, `ForEach-Object -Parallel`, `Get-Error`.
- 관리자 권한을 요구하는 코드를 넣지 않는다. `.cmd` 런처는
  `-NoProfile -ExecutionPolicy Bypass -File "%~dp0..."` 형태를 유지한다(프로세스 한정 우회).
- 이 개발 환경에는 `pwsh`가 없다. 변경을 실행으로 검증할 수 없으므로 정적 검토로만 판단하고,
  보고할 때 실행 검증이 아님을 명시한다.

## 인코딩 (회귀 이력 있음 — commit a88f99e)

- `.ps1`은 **UTF-8 BOM(`ef bb bf`)으로 저장**한다. BOM이 없으면 PS 5.1이 파일을 ANSI로 읽어
  스크립트 안의 한글 문자열이 깨진다. 편집 후 `head -c3 <file> | od -An -tx1`로 확인한다.
- `.cmd`에는 BOM을 넣지 않는다. 대신 첫 줄들에 `chcp 65001 >nul`을 유지한다.
- `.ps1` 선두의 `[Console]::InputEncoding/OutputEncoding/$OutputEncoding` 설정 블록과 이를 감싼
  `try { } catch { }`를 제거하지 않는다. 인코딩 설정 실패가 스크립트를 중단시키면 안 된다.
- 사용자 `config.toml`은 **BOM 없는 UTF-8**로 쓴다(`New-Object System.Text.UTF8Encoding($false)`).
  스크립트 자신의 BOM 규칙과 반대다. 혼동하지 않는다.

## config.toml 수정 순서 (불변)

```
읽기 → 레거시 블록 탐지 → 없으면 변경 없이 exit 0
  ──── 여기까지 파일시스템 미변경 ────
→ 타임스탬프 백업 → 블록 제거한 내용 쓰기 → 메모리 정리
```

- 쓰기 전 `config.toml.backup-yyyyMMdd-HHmmss` 백업을 항상 만든다.
- `Remove-DidimBlock`은 `[mcp_servers.didim-mcp]` 및 `[mcp_servers.didim-mcp.*]` 테이블만
  제거하고 다른 줄의 내용과 순서를 보존한다. TOML 파서를 도입하지 말고 이 라인 스캔 방식을
  유지한다(의존성 없음이 요구사항이다). 하위 테이블을 통째로 지우므로 `http_headers`,
  `env_http_headers`, `bearer_token_env_var` 가 함께 사라진다 — 개별 키를 골라 지우지 않는다.
- 멱등성: 여러 번 실행해도 결과가 같아야 하고, 두 번째 실행은 아무것도 바꾸지 않아야 한다.
- 남은 내용은 CRLF(`` "`r`n" ``)로 조립한다.
- 레거시 키 값을 파싱·비교·출력하지 않는다. `legacy credential removed` 수준만 알린다.

## 프로세스 종료

- **정확한 `ProcessName` 일치만** 대상으로 한다. 부분 문자열 매칭(`*codex*`, `gpt` 등)을
  도입하지 않는다. 기본값은 `@('codex')`.
- 자기 자신의 `$PID`와 모든 조상 PID는 절대 종료하지 않는다. 조상 체인 탐색 루프의 상한(20)을
  제거하지 않는다.
- Codex 내부에서 실행된 경우(조상에 대상 프로세스 존재)에는 종료를 **시도하지 않고** 수동 종료를
  안내한다.
- 기본은 **아무 프로세스도 건드리지 않는다**(`-KillCodexProcesses`로 옵트인). 옵트인했을 때의
  확인 프롬프트는 `[y/N]`이며 기본값은 **No**다.
- 프로세스 종료 단계의 예외는 `try/catch`로 삼킨다. 이미 저장된 결과를 실패로 만들지 않는다.

## 출력

- 성공 메시지는 `[OK]`로 시작한다. 자격증명 값은 어떤 경로로도 출력하지 않는다.
- 마지막에 "Codex 완전 종료 → 재시작 → **Connect** → `/mcp` 확인" 안내를 유지한다.
