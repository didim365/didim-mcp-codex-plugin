# Secret 취급 규칙

Didim MCP는 **OAuth-only**다. 사용자가 입력하는 자격증명은 없고, 토큰은 Codex가 보관한다.
이 규칙은 그 전제 위에서 스크립트·Skill·문서·커밋 전부에 적용된다.

## 대상 비밀값

| 값 | 형식 / 위치 |
| --- | --- |
| OAuth access / refresh token | Codex 자격증명 저장소. 이 저장소와 Skill은 접근하지 않는다 |
| 레거시 Didim Vault API Key | `dv_[A-Za-z0-9_-]{8,}` — 0.1.x 사용자 `~/.codex/config.toml`에만 잔존. **폐기됨** |
| 레거시 인증 헤더 | `X-Didim-Vault-Api-Key` — 헤더명은 공개, 값은 비밀. 더 이상 사용하지 않는다 |
| 공공데이터 `serviceKey` | MCP 서버가 주입. 사용자·Codex는 절대 보유하지 않는다 |
| SSH · 외부 API resource credential | Vault 보관, 서버가 주입. **폐지 대상 아님** — 로그인용 `dv_` 키와 다른 개념이다 |
| Vault resource ID | 일반 응답에 노출하지 않는다 |

## 금지

- 자격증명 값을 저장소 파일, 예제, 픽스처, 커밋 메시지, 응답, 로그에 넣지 않는다.
  문서에 필요하면 `<사용자가 입력했던 dv_ API Key>` 같은 플레이스홀더만 쓴다.
- **사용자 자격증명 입력 UX를 되살리지 않는다.** API Key 입력 프롬프트, 숨김 입력, 형식 검증,
  환경변수 등록, 헤더 생성, rotate/revoke 안내를 다시 추가하지 않는다. 서버가 더 이상 받지 않는다.
- 플러그인이 OAuth를 직접 구현하지 않는다: client_id 하드코딩, client_secret 보관, 고정 redirect
  포트, callback 서버, 토큰 저장/갱신, Authorization 헤더 조립, Entra endpoint 직접 호출 금지.
- 사용자에게 채팅·이슈·PR에 키나 토큰을 붙여넣게 요청하지 않는다.
- 기존에 설정된 값을 읽어서 출력·비교·검증하지 않는다. migrate 스크립트도 하지 않는다.
- MCP Tool 응답에 credential이 섞여 있으면 원문을 그대로 옮기지 않는다.

## 필수

- `migrate-didim-mcp.ps1`은 레거시 블록을 **통째로 삭제**할 뿐, 값을 파싱하거나 비교하지 않는다.
  출력은 `legacy credential removed` 수준으로만 남긴다.
- 쓰기 전 `config.toml.backup-yyyyMMdd-HHmmss` 백업을 만든다. 백업에는 예전 키가 남으므로,
  사용자에게 필요 없으면 삭제하라고 안내한다(파일 내용을 열어보지 않는다).
- `.gitignore`의 secret 차단 패턴(`config.toml`, `*.backup-*`, `*api*key*`, `*.key`, `.env*` 등)은
  제거하지 않는다. 새 산출물이 자격증명을 품을 수 있으면 패턴을 추가한다.
- 커밋 전 `git diff`에 `dv_`로 시작하는 실제 값이나 토큰이 없는지 확인한다.

## 알려진 한계 (숨기지 않는다)

- 0.1.x 시절 사용자 PC에 생성된 `config.toml.backup-*` 파일에는 예전 `dv_` 키가 **평문**으로
  남아 있다. 플러그인은 백업을 삭제하지 않는다. 문서와 Skill은 이 사실을 그대로 알린다.
- MCP 엔드포인트는 HTTPS(`https://didimmcp-dev.didimservice.com/mcp`)다. NCP host nginx가
  Wildcard 인증서 `*.didimservice.com`으로 TLS를 종단한다. NodePort/IP 직접 접근은 쓰지 않는다.
- 현재 대상은 **dev 환경**이다. 운영 도메인 전환 시 `plugin.json`의 URL 한 곳만 바꾸면 된다.
