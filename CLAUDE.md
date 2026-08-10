# CLAUDE.md

## Project

Codex(OpenAI) 플러그인 배포 저장소. 애플리케이션이 아니다. 빌드 산출물, 의존성 매니페스트,
테스트 러너, CI, DB, 서버 코드가 **없다**. 추적 파일은 12개뿐이다.

배포물은 세 가지다.
- 매니페스트 2개 — `.agents/plugins/marketplace.json`(마켓플레이스) → `plugins/didim-mcp/.codex-plugin/plugin.json`(플러그인)
- Windows 스크립트 4개 — `plugins/didim-mcp/scripts/` (PowerShell 5.1 + `.cmd` 런처)
- Skill 3개 — `plugins/didim-mcp/skills/*/SKILL.md`

플러그인은 **MCP 서버를 스스로 등록하지 않는다.** `plugin.json`에 `mcp_servers`가 없다.
setup 스크립트가 사용자의 `~/.codex/config.toml`에 `[mcp_servers.didim-mcp]` 블록을 쓰는 것이
유일한 등록 경로다.

## Source of Truth

```
scripts/*.ps1 · SKILL.md · *.json 매니페스트   ← 실제 동작. 최우선.
        > README.md (루트, plugins/didim-mcp/) ← 사람 대상 안내. 이미 드리프트 있음.
```

README는 근거가 아니다. 루트 README의 저장소 구조 도식은 `plugin.json`을 `v0.1.0`으로
적고 있으나 실제 버전은 `0.1.4`다. 충돌 시 소스를 따르고 사용자에게 알린다.

## Architecture

레이어드 아키텍처가 아니다. 두 개의 독립된 흐름만 있다.

**설정 시점** — 사용자 발화 → `didim-mcp-setup` Skill이 description 매칭으로 선택 →
사용자 승인 → `setup-didim-mcp.cmd`/`.ps1` → 키 검증 성공 이후에만 백업 → `config.toml` 병합 쓰기

**런타임** — Codex 기동 → `config.toml`의 URL + `X-Didim-Vault-Api-Key` 헤더로 HTTP MCP 연결 →
서버가 사용자별 활성 Tool만 노출 → Skill이 노출된 Tool만 사용

Skill 선택은 코드가 아니라 **SKILL.md frontmatter의 `description`** 이 결정한다. 이 프로젝트에
라우터·디스패처는 없다.

## Core Development Principles

- 이 저장소를 일반 애플리케이션처럼 다루지 않는다. 프레임워크·패키지 매니저·테스트 하네스·
  린터 설정을 새로 도입하지 않는다. 지금 없는 것은 의도된 것이다.
- 스크립트 상단의 고정 접속 상수(`$ServerUrl`, `$StartupTimeout`, `$HeaderName`)와 인증 구조는
  변경하지 않는다. 소스 주석에 명시된 제약이다.
- 사용자의 `~/.codex/config.toml`은 남의 파일이다. 이 저장소 작업 중 읽거나 쓰지 않는다.
- 스크립트 동작을 바꾸면 두 README(루트·플러그인)의 해당 서술을 같이 고친다. 안내 문서가
  곧 사용자 인터페이스다.

## Safety / Constraints

- `dv_` API Key, `serviceKey`, 인증 헤더 값의 **원문을 출력·기록·커밋하지 않는다.** 상세는
  `.claude/rules/secrets.md`.
- setup/remove 스크립트를 이 환경에서 **실행하지 않는다.** 실행하면 사용자 실제
  `~/.codex/config.toml`이 바뀐다. 분석은 소스 독해로만 한다.
- 이 환경(Linux/WSL2)에 PowerShell 런타임이 없다(`pwsh` 부재). `.ps1` 변경을 "실행 검증했다"고
  보고하지 않는다. 정적 검토임을 명시한다.
- 사용자가 명시적으로 요청하지 않으면 `git commit` / `git push` 하지 않는다. 상세는
  `.claude/rules/release.md`.

## Verification

이 저장소에서 실제로 돌릴 수 있는 검증은 이게 전부다. 없는 테스트를 만들어내지 않는다.

```bash
python3 -m json.tool .agents/plugins/marketplace.json > /dev/null
python3 -m json.tool plugins/didim-mcp/.codex-plugin/plugin.json > /dev/null

# .ps1 2개는 BOM(efbbbf)이 있어야 하고, 그 외 파일에는 없어야 한다
for f in $(git ls-files); do printf '%s: ' "$f"; head -c3 "$f" | od -An -tx1; done

git diff --stat
```

`.ps1` 변경 시에는 위에 더해 `.claude/rules/powershell-scripts.md`의 체크 항목을 눈으로 확인한다.
