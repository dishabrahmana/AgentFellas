from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Interaction, Reminder, Session, Stakeholder, WorklogEntry


# ─── Worklog ────────────────────────────────────────────────────────────────

async def create_worklog(
    session: AsyncSession,
    user_id: str,
    title: str,
    description: str | None = None,
    status: str = "in_progress",
    priority: str = "medium",
    tags: list[str] | None = None,
    stakeholder_id: int | None = None,
    estimated_hours: float | None = None,
) -> WorklogEntry:
    entry = WorklogEntry(
        user_id=user_id,
        title=title,
        description=description,
        status=status,
        priority=priority,
        tags=str(tags or []),
        stakeholder_id=stakeholder_id,
        estimated_hours=estimated_hours,
        start_time=datetime.now() if status == "in_progress" else None,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def get_worklog(session: AsyncSession, worklog_id: int) -> WorklogEntry | None:
    result = await session.execute(select(WorklogEntry).where(WorklogEntry.id == worklog_id))
    return result.scalar_one_or_none()


async def list_worklogs(
    session: AsyncSession,
    user_id: str,
    status: str | None = None,
    limit: int = 20,
) -> list[WorklogEntry]:
    query = select(WorklogEntry).where(WorklogEntry.user_id == user_id)
    if status:
        query = query.where(WorklogEntry.status == status)
    query = query.order_by(WorklogEntry.updated_at.desc()).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


async def update_worklog(
    session: AsyncSession,
    worklog_id: int,
    **kwargs: Any,
) -> WorklogEntry | None:
    kwargs["updated_at"] = datetime.now()
    if "status" in kwargs and kwargs["status"] == "done":
        kwargs["end_time"] = kwargs.get("end_time", datetime.now())
    await session.execute(
        update(WorklogEntry).where(WorklogEntry.id == worklog_id).values(**kwargs)
    )
    await session.commit()
    return await get_worklog(session, worklog_id)


async def delete_worklog(session: AsyncSession, worklog_id: int) -> bool:
    result = await session.execute(
        delete(WorklogEntry).where(WorklogEntry.id == worklog_id)
    )
    await session.commit()
    return result.rowcount > 0


async def get_today_logs(session: AsyncSession, user_id: str) -> list[WorklogEntry]:
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    query = (
        select(WorklogEntry)
        .where(
            WorklogEntry.user_id == user_id,
            WorklogEntry.created_at >= today_start,
        )
        .order_by(WorklogEntry.created_at.desc())
    )
    result = await session.execute(query)
    return list(result.scalars().all())


# ─── Stakeholder ────────────────────────────────────────────────────────────

async def create_stakeholder(
    session: AsyncSession,
    user_id: str,
    name: str,
    role: str | None = None,
    company: str | None = None,
    contact_info: dict | None = None,
    notes: str | None = None,
    priority: str = "medium",
) -> Stakeholder:
    stakeholder = Stakeholder(
        user_id=user_id,
        name=name,
        role=role,
        company=company,
        contact_info=str(contact_info or {}),
        notes=notes,
        priority=priority,
    )
    session.add(stakeholder)
    await session.commit()
    await session.refresh(stakeholder)
    return stakeholder


async def get_stakeholder(session: AsyncSession, stakeholder_id: int) -> Stakeholder | None:
    result = await session.execute(
        select(Stakeholder).where(Stakeholder.id == stakeholder_id)
    )
    return result.scalar_one_or_none()


async def find_stakeholder_by_name(
    session: AsyncSession, user_id: str, name: str
) -> Stakeholder | None:
    result = await session.execute(
        select(Stakeholder).where(
            Stakeholder.user_id == user_id,
            Stakeholder.name.ilike(f"%{name}%"),
            Stakeholder.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def list_stakeholders(
    session: AsyncSession,
    user_id: str,
    active_only: bool = True,
) -> list[Stakeholder]:
    query = select(Stakeholder).where(Stakeholder.user_id == user_id)
    if active_only:
        query = query.where(Stakeholder.is_active == True)
    query = query.order_by(Stakeholder.priority.desc(), Stakeholder.name.asc())
    result = await session.execute(query)
    return list(result.scalars().all())


async def update_stakeholder(
    session: AsyncSession,
    stakeholder_id: int,
    **kwargs: Any,
) -> Stakeholder | None:
    kwargs["updated_at"] = datetime.now()
    await session.execute(
        update(Stakeholder).where(Stakeholder.id == stakeholder_id).values(**kwargs)
    )
    await session.commit()
    return await get_stakeholder(session, stakeholder_id)


# ─── Interaction ────────────────────────────────────────────────────────────

async def create_interaction(
    session: AsyncSession,
    stakeholder_id: int,
    typ: str,
    title: str,
    summary: str | None = None,
    outcome: str | None = None,
    action_items: list[str] | None = None,
    date: datetime | None = None,
    next_action_date: datetime | None = None,
) -> Interaction:
    interaction = Interaction(
        stakeholder_id=stakeholder_id,
        type=typ,
        title=title,
        summary=summary,
        outcome=outcome,
        action_items=str(action_items or []),
        date=date or datetime.now(),
        next_action_date=next_action_date,
    )
    session.add(interaction)
    await session.commit()
    await session.refresh(interaction)
    return interaction


async def list_interactions(
    session: AsyncSession,
    stakeholder_id: int,
    limit: int = 10,
) -> list[Interaction]:
    query = (
        select(Interaction)
        .where(Interaction.stakeholder_id == stakeholder_id)
        .order_by(Interaction.date.desc())
        .limit(limit)
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_upcoming_actions(
    session: AsyncSession,
    user_id: str,
    days: int = 7,
) -> list[Interaction]:
    deadline = datetime.now() + timedelta(days=days)
    query = (
        select(Interaction)
        .join(Stakeholder)
        .where(
            Stakeholder.user_id == user_id,
            Interaction.next_action_date <= deadline,
            Interaction.next_action_date >= datetime.now(),
        )
        .order_by(Interaction.next_action_date.asc())
    )
    result = await session.execute(query)
    return list(result.scalars().all())


# ─── Reminder ───────────────────────────────────────────────────────────────

async def create_reminder(
    session: AsyncSession,
    user_id: str,
    title: str,
    due_date: datetime,
    description: str | None = None,
    related_type: str | None = None,
    related_id: int | None = None,
) -> Reminder:
    reminder = Reminder(
        user_id=user_id,
        title=title,
        description=description,
        due_date=due_date,
        related_type=related_type,
        related_id=related_id,
    )
    session.add(reminder)
    await session.commit()
    await session.refresh(reminder)
    return reminder


async def get_due_reminders(session: AsyncSession, within_minutes: int = 5) -> list[Reminder]:
    now = datetime.now()
    deadline = now + timedelta(minutes=within_minutes)
    query = (
        select(Reminder)
        .where(
            Reminder.is_done == False,
            Reminder.due_date <= deadline,
        )
        .order_by(Reminder.due_date.asc())
    )
    result = await session.execute(query)
    return list(result.scalars().all())


async def mark_reminder_done(session: AsyncSession, reminder_id: int) -> bool:
    result = await session.execute(
        update(Reminder).where(Reminder.id == reminder_id).values(is_done=True)
    )
    await session.commit()
    return result.rowcount > 0


# ─── Session ────────────────────────────────────────────────────────────────

async def get_or_create_session(
    session: AsyncSession,
    user_id: str,
    chat_id: str,
) -> Session:
    result = await session.execute(
        select(Session).where(
            Session.user_id == user_id,
            Session.chat_id == chat_id,
        )
    )
    s = result.scalar_one_or_none()
    if s:
        return s
    s = Session(user_id=user_id, chat_id=chat_id)
    session.add(s)
    await session.commit()
    await session.refresh(s)
    return s


async def update_session_context(
    session: AsyncSession,
    session_id: int,
    **kwargs: Any,
) -> None:
    kwargs["updated_at"] = datetime.now()
    await session.execute(
        update(Session).where(Session.id == session_id).values(**kwargs)
    )
    await session.commit()
