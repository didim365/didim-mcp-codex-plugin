# 배포 · Git 규칙

패키징 파이프라인도 CI도 없다. **`main` push가 곧 배포다.** 사용자는 Codex 앱에서
마켓플레이스를 갱신해 받는다. 되돌릴 방법은 새 커밋뿐이다.

## Git

- 사용자가 명시적으로 요청하지 않으면 `git commit` / `git push` 하지 않는다.
- 브랜치 생성, force push, history 재작성을 하지 않는다.
- 커밋 메시지는 기존 관례인 Conventional Commits를 따른다. 실제 사용된 형태:
  `feat: `, `feat(setup): `, `feat(skill): `, `feat(plugin): `, `fix(scripts): `, `docs: `.

## 버전

- 사용자에게 보이는 변경(스크립트 동작, Skill 내용, 매니페스트)을 커밋할 때는
  `plugins/didim-mcp/.codex-plugin/plugin.json`의 `version`을 함께 올린다. 일반 변경은
  patch 1건씩 올린다(`0.1.0 → 0.1.5`가 그렇게 쌓였다). 버전이 안 오르면 사용자 쪽 업데이트
  판정이 어렵다.
- 사용자 조치가 필요한 동작 변경은 **minor**를 올린다. `0.2.0`이 그 사례다(API Key → OAuth
  전환. 기존 사용자는 레거시 `config.toml` 블록 정리를 1회 수행해야 한다). 1.0 이전이므로
  major는 올리지 않는다.
- `.agents/plugins/marketplace.json`에는 버전이 없다. 여기에 버전 필드를 새로 만들지 않는다.
- 두 매니페스트의 `name`(`didim` / `didim-mcp`)은 사용자의 설치 식별자
  (`codex plugin add didim-mcp@didim`)와 마켓플레이스 URL에 직접 묶여 있다. 바꾸면 기존 설치가
  끊긴다. 변경 요청이 오면 그 파급을 먼저 알린다.
- `marketplace.json`의 `source.path`(`./plugins/didim-mcp`)는 저장소 내 상대 경로다. 플러그인
  디렉터리를 옮기면 반드시 함께 고친다.

## 문서 동기화

동작을 바꾼 커밋은 관련 문서를 같은 커밋에 포함한다.

- 스크립트 옵션·동작 변경 → 루트 `README.md` + `plugins/didim-mcp/README.md`
- Skill 트리거·흐름 변경 → 두 README의 해당 절
- 배포되는 파일 추가/이동 → 루트 README의 저장소 구조 도식
- `plugin.json`의 `mcpServers` URL 변경 → 두 README의 URL 서술 + `CLAUDE.md` Architecture

스크립트는 `plugins/didim-mcp/` 안에 있어야 한다. Codex는 설치 시 플러그인 디렉터리만
배포하므로, 저장소 루트로 옮기면 설치된 사용자가 스크립트를 찾지 못한다.
