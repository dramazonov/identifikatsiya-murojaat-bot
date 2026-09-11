from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from sqlalchemy import String, cast, func, or_, select

from app.database import async_session
from app.models import Appeal, Suggestion, User
from app.services.datetime_utils import utcnow

PAGE_SIZE = 25


@dataclass(frozen=True)
class AppealView:
    appeal: Appeal
    user: User
    effective_status: str


@dataclass(frozen=True)
class SuggestionView:
    suggestion: Suggestion
    user: User


@dataclass(frozen=True)
class Page:
    items: list
    page: int
    total_pages: int
    total: int


def effective_appeal_status(appeal: Appeal) -> str:
    if (
        appeal.status == "IN_PROGRESS"
        and appeal.claim_expires_at is not None
        and appeal.claim_expires_at <= utcnow()
        and not appeal.admin_answer
    ):
        return "NEW"
    return appeal.status


def _appeal_status_predicate(status: str):
    now = utcnow()
    if status == "NEW":
        return or_(
            Appeal.status == "NEW",
            (Appeal.status == "IN_PROGRESS")
            & (Appeal.claim_expires_at.is_not(None))
            & (Appeal.claim_expires_at <= now)
            & (Appeal.admin_answer.is_(None)),
        )
    if status == "IN_PROGRESS":
        return (Appeal.status == "IN_PROGRESS") & or_(
            Appeal.claim_expires_at.is_(None), Appeal.claim_expires_at > now
        )
    return Appeal.status == status


async def dashboard_counts() -> dict[str, int]:
    async with async_session() as session:
        users = int((await session.execute(select(func.count(User.id)))).scalar_one())
        total_appeals = int((await session.execute(select(func.count(Appeal.id)))).scalar_one())
        total_suggestions = int((await session.execute(select(func.count(Suggestion.id)))).scalar_one())
        status_rows = (
            await session.execute(select(Appeal.status, func.count(Appeal.id)).group_by(Appeal.status))
        ).all()
        suggestion_rows = (
            await session.execute(
                select(Suggestion.status, func.count(Suggestion.id)).group_by(Suggestion.status)
            )
        ).all()
    counts = {f"appeal_{status.lower()}": int(count) for status, count in status_rows}
    async with async_session() as session:
        expired = int(
            (
                await session.execute(
                    select(func.count(Appeal.id)).where(
                        Appeal.status == "IN_PROGRESS",
                        Appeal.claim_expires_at.is_not(None),
                        Appeal.claim_expires_at <= utcnow(),
                        Appeal.admin_answer.is_(None),
                    )
                )
            ).scalar_one()
        )
    if expired:
        counts["appeal_new"] = counts.get("appeal_new", 0) + expired
        counts["appeal_in_progress"] = max(0, counts.get("appeal_in_progress", 0) - expired)
    counts.update({f"suggestion_{status.lower()}": int(count) for status, count in suggestion_rows})
    counts.update(users=users, appeals=total_appeals, suggestions=total_suggestions)
    return counts


async def list_appeals(
    *,
    page: int = 1,
    q: str = "",
    status: str = "",
    category: str = "",
    region: str = "",
    district: str = "",
) -> Page:
    page = max(1, page)
    async with async_session() as session:
        stmt = select(Appeal, User).join(User, Appeal.user_id == User.id)
        count_stmt = select(func.count(Appeal.id)).join(User, Appeal.user_id == User.id)
        predicates = []
        q = q.strip()
        if q:
            token = f"%{q.lower()}%"
            predicates.append(
                or_(
                    func.lower(Appeal.appeal_number).like(token),
                    func.lower(func.coalesce(User.full_name, "")).like(token),
                    func.lower(func.coalesce(User.phone, "")).like(token),
                    cast(User.telegram_id, String).like(f"%{q}%"),
                )
            )
        if status:
            predicates.append(_appeal_status_predicate(status))
        if category:
            predicates.append(Appeal.category_code == category)
        if region:
            predicates.append(User.region == region)
        if district:
            predicates.append(User.district == district)
        for predicate in predicates:
            stmt = stmt.where(predicate)
            count_stmt = count_stmt.where(predicate)
        total = int((await session.execute(count_stmt)).scalar_one())
        total_pages = max(1, ceil(total / PAGE_SIZE))
        page = min(page, total_pages)
        rows = (
            await session.execute(
                stmt.order_by(Appeal.id.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
            )
        ).all()
    return Page(
        items=[AppealView(a, u, effective_appeal_status(a)) for a, u in rows],
        page=page,
        total_pages=total_pages,
        total=total,
    )


async def get_appeal_view(appeal_id: int) -> AppealView | None:
    async with async_session() as session:
        row = (
            await session.execute(
                select(Appeal, User)
                .join(User, Appeal.user_id == User.id)
                .where(Appeal.id == appeal_id)
            )
        ).one_or_none()
    if row is None:
        return None
    appeal, user = row
    return AppealView(appeal, user, effective_appeal_status(appeal))


async def list_users(*, page: int = 1, q: str = "") -> Page:
    page = max(1, page)
    async with async_session() as session:
        stmt = select(User)
        count_stmt = select(func.count(User.id))
        q = q.strip()
        if q:
            token = f"%{q.lower()}%"
            predicate = or_(
                func.lower(func.coalesce(User.full_name, "")).like(token),
                func.lower(func.coalesce(User.phone, "")).like(token),
                cast(User.telegram_id, String).like(f"%{q}%"),
                func.lower(func.coalesce(User.region, "")).like(token),
                func.lower(func.coalesce(User.district, "")).like(token),
            )
            stmt = stmt.where(predicate)
            count_stmt = count_stmt.where(predicate)
        total = int((await session.execute(count_stmt)).scalar_one())
        total_pages = max(1, ceil(total / PAGE_SIZE))
        page = min(page, total_pages)
        items = list(
            (
                await session.scalars(
                    stmt.order_by(User.id.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
                )
            ).all()
        )
    return Page(items=items, page=page, total_pages=total_pages, total=total)


async def list_suggestions(*, page: int = 1, status: str = "") -> Page:
    page = max(1, page)
    async with async_session() as session:
        stmt = select(Suggestion, User).join(User, Suggestion.user_id == User.id)
        count_stmt = select(func.count(Suggestion.id)).join(User, Suggestion.user_id == User.id)
        if status:
            stmt = stmt.where(Suggestion.status == status)
            count_stmt = count_stmt.where(Suggestion.status == status)
        total = int((await session.execute(count_stmt)).scalar_one())
        total_pages = max(1, ceil(total / PAGE_SIZE))
        page = min(page, total_pages)
        rows = (
            await session.execute(
                stmt.order_by(Suggestion.id.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
            )
        ).all()
    return Page(
        items=[SuggestionView(s, u) for s, u in rows],
        page=page,
        total_pages=total_pages,
        total=total,
    )


async def category_counts() -> list[tuple[str | None, int]]:
    async with async_session() as session:
        rows = (
            await session.execute(
                select(Appeal.category_code, func.count(Appeal.id))
                .group_by(Appeal.category_code)
                .order_by(func.count(Appeal.id).desc())
            )
        ).all()
    return [(code, int(count)) for code, count in rows]


async def region_counts(limit: int = 20) -> list[tuple[str | None, int]]:
    async with async_session() as session:
        rows = (
            await session.execute(
                select(User.region, func.count(Appeal.id))
                .join(Appeal, Appeal.user_id == User.id)
                .group_by(User.region)
                .order_by(func.count(Appeal.id).desc())
                .limit(limit)
            )
        ).all()
    return [(region, int(count)) for region, count in rows]
