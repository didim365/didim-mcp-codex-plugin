"""응답을 보내기 **전에** commit 하는 라우트 클래스.

FastAPI 의 `yield` 의존성 teardown(`app/api/deps.py:get_session` 의 `commit`)은 **응답을
보낸 뒤** 실행된다. 그래서 클라이언트가 `201` 을 받은 시점에는 아직 커밋 전이고, 화면이
곧바로 방금 만든 것을 다시 읽으면 없다.

dev 컨테이너 + 실제 PostgreSQL 로 실측한 값이다.

    create  201  at  29.9ms
    t+ 34.3ms  GET /admin/skills/{id} -> 404      ← 아직 커밋 전
    t+ 62.1ms  GET /admin/skills/{id} -> 200

Admin Web 이 정확히 "저장 → 목록/상세 다시 읽기" 패턴이라 눈에 보이는 버그가 된다.
단위 테스트는 이걸 잡지 못한다 — httpx `ASGITransport` 는 exit stack 까지 끝난 뒤에
응답을 돌려주기 때문에 경합 자체가 생기지 않는다.

그래서 트랜잭션 종료를 **route handler 안쪽**으로 끌어온다. 여기는 Response 객체를 만든
직후이고 ASGI send 이전이다. 예외로 빠지면 commit 하지 않고 그대로 올려보내
`get_session` 이 rollback 한다.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, Response
from fastapi.routing import APIRoute


class TransactionalRoute(APIRoute):
    """정상 응답이면 send 전에 commit 한다. 쓰기 endpoint 를 가진 라우터에 붙인다."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def handler(request: Request) -> Response:
            response = await original(request)
            session = getattr(request.state, "session", None)
            if session is not None and session.in_transaction():
                await session.commit()
            return response

        return handler


__all__ = ["TransactionalRoute"]
