---
paths:
  - "app/**"
  - "web/**"
  - "alembic/**"
  - "tests/**"
---

# Skill Registry 규칙

대상: FastAPI backend(`app/`), React Admin(`web/`), migration(`alembic/`), 테스트.

`CLAUDE.md` 의 Invariants 를 여기에 다시 적지 않는다. 여기에는 **이 디렉터리를 건드릴 때만
필요한 상세**만 둔다.

## 계층

```
app/api/v1/*.py      Router. 인가 가드는 router.py 의 include_router 에 붙는다
app/services/*.py    정책(초안/배포/롤백 규칙). flush 만 하고 commit 하지 않는다
app/repositories/*.py 데이터 접근. 정책을 담지 않는다
app/db/models/*.py   ORM. 응답으로 그대로 내보내지 않는다
app/api/dto.py       API 계약. Admin 과 runtime 을 분리한다
app/api/mappers.py   Entity → DTO. 화면마다 다시 조립하지 않는다
```

- 새 endpoint 를 `_admin` router 밖에 붙이지 않는다. 붙이는 순간 가드가 빠진다.
- **새 라우터 파일은 `APIRouter(..., route_class=TransactionalRoute)` 로 만든다.**
  FastAPI 의 `yield` 의존성 teardown(`get_session` 의 commit)은 **응답을 보낸 뒤** 실행
  된다. 그대로 두면 화면이 저장 직후 다시 읽었을 때 방금 만든 행이 없다(실측: 201 직후
  404, 30ms 뒤 200). 부모 라우터의 `route_class` 는 `include_router` 로 넣은 자식에게
  내려가지 않으므로 **파일마다** 지정해야 한다.
  `tests/test_runtime_contract.py::test_every_api_route_commits_before_responding` 가
  누락을 잡는다.
- runtime DTO 에 내부 UUID·감사 필드를 추가하지 않는다. `mappers.runtime_*` 가 유일한
  출구다.
- Repository 에서 사용자 입력을 컬럼 이름으로 해석하지 않는다(`_order` 의 화이트리스트).

## 인가

- `require_admin` 은 **Auth `/me` 를 매 요청 호출한다.** 캐시를 넣지 않는다 — role 정본이
  Auth DB 이고, 강등/비활성이 즉시 반영되어야 한다.
- 위임 토큰(`act` 보유)은 Admin API 에서 거부한다. runtime 에서는 허용한다.
- 세션 쿠키 경로에만 CSRF 를 요구한다. Bearer 경로에는 요구하지 않는다(쿠키가 자동
  전송되는 요청이 아니다).
- `parse_role` 은 모르는 role 을 **USER 로 떨어뜨린다.** Auth 가 새 role 을 추가했을 때
  ADMIN 으로 오인하지 않기 위해서다. 확대 해석하는 방향으로 고치지 않는다.

## DB / migration

- 새 테이블은 반드시 `mcp_skill_registry` 안에. `Base.metadata` 가 schema 를 고정한다.
- `server_default` 에 `text("now()")` 를 쓰지 않는다 — SQLite 단위 테스트에서 죽는다.
  `func.now()` 를 쓴다(PostgreSQL 에서는 똑같이 `now()` 로 렌더된다).
- PostgreSQL 전용 타입은 `with_variant` 로 SQLite 대안을 준다(`JSONB().with_variant(JSON(),
  "sqlite")`). 그러지 않으면 단위 테스트가 통째로 못 돈다.
- **부분 unique index `uq_skill_versions_one_published` 를 지우지 않는다.** 애플리케이션
  잠금은 1차 방어일 뿐이고 이것이 최후 방어선이다.
- data migration 은 **멱등**이어야 한다. 이미 있는 것을 덮어쓰지 않는다 — 운영 중 사람이
  고친 내용을 migration 이 되돌리면 안 된다.
- `downgrade` 에서 사람이 손댄 데이터를 지우지 않는다(`0002` 의 버전 수 확인 참고).

## 화면 (`web/`)

- **frontend 는 authorization boundary 가 아니다.** `is_admin` 은 메뉴를 그릴지만 정한다.
  새 ADMIN 기능을 붙일 때 backend 가드가 실제로 있는지 확인하고, 없으면 화면이 아니라
  backend 를 고친다.
- **토큰을 다루는 코드를 만들지 않는다.** localStorage 저장·Authorization 헤더 조립·
  refresh 로직 전부 금지다. 인증은 backend 가 심은 HttpOnly 쿠키로 성립한다.
- **CSRF 헤더를 붙이는 곳은 `web/src/lib/api.ts` 하나다.** 화면이 `fetch` 를 직접 부르지
  않는다. 403 을 자동 재시도하지 않는다.
- **401 만 로그인으로 보낸다. 403 은 화면에 남긴다.**
- 로그인 시작은 **backend 경로 `/login`** 으로 넘긴다. 화면이 Auth URL 을 직접 조립하지
  않는다 — 자동 SSO 여부의 근거인 loop guard 쿠키가 HttpOnly 라 화면이 판단할 수 없다.
- 표시 매핑의 정본은 `web/src/lib/labels.ts` 하나다. 모르는 값은 감추지 말고 원문을 그대로
  보여준다. **색만으로 구분하지 않는다** — badge 는 항상 label 을 갖는다.
- `web/src/types/api.ts` 는 backend DTO 의 **사본**이다. 모르는 필드를 추측해 추가하지
  않는다.
- 되돌리기 어려운 작업(배포·롤백·초안 삭제) 앞에는 확인 modal 을 둔다. modal 본문은 무엇이
  바뀌는지 **문장으로** 설명한다.
- `Field` 의 hint 는 `<label>` **밖**에 둔다. 안에 두면 접근성 이름이 "라벨 + 설명문" 이
  된다.

## 테스트

- `globals: false` 다 — `describe`/`it`/`expect`/`vi` 를 `"vitest"` 에서 import 하고,
  자동 cleanup 이 없으므로 `afterEach` 에서 `cleanup()` 을 직접 부른다.
- `web/src/lib/api.ts` 의 me/CSRF 는 **모듈 스코프 캐시**다. 케이스마다
  `resetAuthCache()` 로 비우지 않으면 앞 케이스의 로그인 주체가 다음 케이스로 샌다.
- backend 단위 테스트는 in-memory SQLite 다. **`SELECT ... FOR UPDATE` 를 검증하지
  못한다** — 동시성은 `tests/integration` (PostgreSQL) 소관이다.
- conftest 의 SQLite PRAGMA 리스너는 전역이다. **SQLite 커넥션에만** 적용해야 한다
  (PostgreSQL 엔진에 PRAGMA 를 보내면 문법 오류로 죽는다).
- `tsconfig` 의 `include` 에 `src` 전체가 들어 있어 **테스트 파일 타입 오류가 Docker 빌드를
  멈춘다.** 테스트를 추가하면 `npm run build` 까지 돌린다.
