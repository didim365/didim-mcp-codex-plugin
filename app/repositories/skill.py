"""Skill / SkillVersion 데이터 접근. 정책은 담지 않는다(Service 의 일이다).

``commit`` 하지 않는다 — 트랜잭션 경계는 ``app/api/deps.py:get_session`` 이 소유한다.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, UnaryExpression, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.strategy_options import _AbstractLoad

from app.db.models.skill import Skill, SkillVersion
from app.domain.enums import SkillVersionStatus


def _with_children() -> tuple[_AbstractLoad, ...]:
    """버전의 alias/tool 을 eager-load(async lazy-load 금지)."""
    return (selectinload(SkillVersion.aliases), selectinload(SkillVersion.tools))


class SkillRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── 조회 ──────────────────────────────────────────────

    async def get(self, skill_id: uuid.UUID) -> Skill | None:
        stmt = (
            select(Skill)
            .where(Skill.id == skill_id)
            .options(selectinload(Skill.versions).options(*_with_children()))
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_by_key(self, skill_key: str) -> Skill | None:
        stmt = (
            select(Skill)
            .where(Skill.skill_key == skill_key)
            .options(selectinload(Skill.versions).options(*_with_children()))
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def lock(self, skill_id: uuid.UUID) -> Skill | None:
        """publish/rollback 직렬화용 행 잠금.

        `SELECT ... FOR UPDATE` 로 같은 Skill 에 대한 동시 publish 를 순서대로 세운다.
        DB 의 부분 unique index 가 최후 방어선이고, 이 잠금은 그 충돌을 애초에 만들지 않기
        위한 1차 방어다. eager-load 와 함께 쓰지 않는다(FOR UPDATE 와 outer join 충돌).
        """
        stmt = select(Skill).where(Skill.id == skill_id).with_for_update()
        return (await self.session.execute(stmt)).scalars().first()

    async def list_page(
        self,
        *,
        search: str | None,
        category: str | None,
        enabled: bool | None,
        status: SkillVersionStatus | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> tuple[Sequence[Skill], int]:
        base = self._filtered(search=search, category=category, enabled=enabled, status=status)
        total = (
            await self.session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = (
            base.options(selectinload(Skill.versions).options(*_with_children()))
            .order_by(*self._order(sort))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        rows = (await self.session.execute(stmt)).scalars().unique().all()
        return rows, int(total)

    def _filtered(
        self,
        *,
        search: str | None,
        category: str | None,
        enabled: bool | None,
        status: SkillVersionStatus | None,
    ) -> Select[tuple[Skill]]:
        stmt = select(Skill)
        if search:
            like = f"%{search.strip().lower()}%"
            # skill_key 와 **현재 배포 버전의 이름** 으로 찾는다. DRAFT 이름으로는 찾지 않는다
            # (목록의 '스킬' 열이 배포본 이름이라 눈에 보이는 것과 일치시킨다).
            name_match = (
                select(SkillVersion.skill_id)
                .where(
                    SkillVersion.status == SkillVersionStatus.PUBLISHED,
                    func.lower(SkillVersion.name).like(like),
                )
                .scalar_subquery()
            )
            stmt = stmt.where(func.lower(Skill.skill_key).like(like) | Skill.id.in_(name_match))
        if category:
            stmt = stmt.where(Skill.category == category)
        if enabled is not None:
            stmt = stmt.where(Skill.enabled.is_(enabled))
        if status is not None:
            has_status = (
                select(SkillVersion.skill_id).where(SkillVersion.status == status).scalar_subquery()
            )
            stmt = stmt.where(Skill.id.in_(has_status))
        return stmt

    @staticmethod
    def _order(sort: str) -> tuple[UnaryExpression[Any], ...]:
        """정렬 키 화이트리스트. 사용자 입력을 컬럼으로 해석하지 않는다."""
        mapping: dict[str, tuple[UnaryExpression[Any], ...]] = {
            "skill_key": (Skill.skill_key.asc(), Skill.id.asc()),
            "-skill_key": (Skill.skill_key.desc(), Skill.id.asc()),
            "updated_at": (Skill.updated_at.asc(), Skill.id.asc()),
            "-updated_at": (Skill.updated_at.desc(), Skill.id.asc()),
            "category": (Skill.category.asc(), Skill.skill_key.asc()),
        }
        return mapping.get(sort, mapping["-updated_at"])

    async def categories(self) -> list[str]:
        stmt = (
            select(Skill.category)
            .where(Skill.category.is_not(None))
            .distinct()
            .order_by(Skill.category)
        )
        return [c for c in (await self.session.execute(stmt)).scalars().all() if c]

    # ── 쓰기 ──────────────────────────────────────────────

    def add(self, skill: Skill) -> None:
        self.session.add(skill)


class SkillVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, version_id: uuid.UUID) -> SkillVersion | None:
        stmt = select(SkillVersion).where(SkillVersion.id == version_id).options(*_with_children())
        return (await self.session.execute(stmt)).scalars().first()

    async def get_by_number(self, skill_id: uuid.UUID, version: int) -> SkillVersion | None:
        stmt = (
            select(SkillVersion)
            .where(SkillVersion.skill_id == skill_id, SkillVersion.version == version)
            .options(*_with_children())
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_by_status(
        self, skill_id: uuid.UUID, status: SkillVersionStatus
    ) -> SkillVersion | None:
        stmt = (
            select(SkillVersion)
            .where(SkillVersion.skill_id == skill_id, SkillVersion.status == status)
            .options(*_with_children())
            .order_by(SkillVersion.version.desc())
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def next_version(self, skill_id: uuid.UUID) -> int:
        stmt = select(func.coalesce(func.max(SkillVersion.version), 0)).where(
            SkillVersion.skill_id == skill_id
        )
        return int((await self.session.execute(stmt)).scalar_one()) + 1

    async def list_for_skill(self, skill_id: uuid.UUID) -> Sequence[SkillVersion]:
        stmt = (
            select(SkillVersion)
            .where(SkillVersion.skill_id == skill_id)
            .options(*_with_children())
            .order_by(SkillVersion.version.desc())
        )
        return (await self.session.execute(stmt)).scalars().all()

    def add(self, version: SkillVersion) -> None:
        self.session.add(version)


class RuntimeSkillRepository:
    """runtime 전용 조회 — **PUBLISHED + enabled 만** SQL 레벨에서 고른다.

    DRAFT 가 새어 나가지 못하게 하는 지점이 여기 하나다. 애플리케이션 필터로 거르지 않는다.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _base(self) -> Select[tuple[SkillVersion, Skill]]:
        return (
            select(SkillVersion, Skill)
            .join(Skill, Skill.id == SkillVersion.skill_id)
            .where(
                SkillVersion.status == SkillVersionStatus.PUBLISHED,
                Skill.enabled.is_(True),
            )
        )

    async def get_published(self, skill_key: str) -> tuple[SkillVersion, Skill] | None:
        stmt = self._base().where(Skill.skill_key == skill_key).options(*_with_children())
        row = (await self.session.execute(stmt)).first()
        return (row[0], row[1]) if row else None

    async def list_published(
        self, *, page: int, page_size: int, category: str | None = None
    ) -> tuple[list[tuple[SkillVersion, Skill]], int]:
        base = self._base()
        if category:
            base = base.where(Skill.category == category)
        total = (
            await self.session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        stmt = (
            base.options(*_with_children())
            .order_by(Skill.skill_key.asc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        rows = (await self.session.execute(stmt)).all()
        return [(r[0], r[1]) for r in rows], int(total)


__all__ = ["RuntimeSkillRepository", "SkillRepository", "SkillVersionRepository"]
