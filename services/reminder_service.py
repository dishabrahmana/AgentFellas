from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Reminder
from db.repository import create_reminder, get_due_reminders, mark_reminder_done


class ReminderService:
    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self.session = session
        self.user_id = user_id

    async def set(
        self,
        title: str,
        due_date: datetime,
        description: str | None = None,
        related_type: str | None = None,
        related_id: int | None = None,
    ) -> Reminder:
        return await create_reminder(
            self.session,
            user_id=self.user_id,
            title=title,
            due_date=due_date,
            description=description,
            related_type=related_type,
            related_id=related_id,
        )

    async def get_due(self, within_minutes: int = 5) -> list[Reminder]:
        return await get_due_reminders(self.session, within_minutes=within_minutes)

    async def mark_done(self, reminder_id: int) -> bool:
        return await mark_reminder_done(self.session, reminder_id)
