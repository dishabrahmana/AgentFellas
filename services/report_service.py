from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from db.models import Interaction, WorklogEntry
from db.repository import get_upcoming_actions, list_worklogs, get_due_reminders
from utils.date_utils import now, today_end, today_start, week_start


class ReportService:
    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self.session = session
        self.user_id = user_id

    async def daily(self) -> dict:
        start = today_start()
        end = today_end()

        done = await list_worklogs(
            self.session,
            user_id=self.user_id,
            status="done",
            limit=50,
        )
        done_today = [w for w in done if w.updated_at and start <= w.updated_at <= end]

        in_progress = await list_worklogs(
            self.session,
            user_id=self.user_id,
            status="in_progress",
        )

        reminders = await get_due_reminders(self.session, within_minutes=1440)
        reminders_today = [r for r in reminders if r.due_date and start <= r.due_date <= end]

        upcoming = [{"title": r.title, "due": r.due_date} for r in reminders_today]

        return {
            "done": done_today,
            "in_progress": in_progress,
            "upcoming": upcoming,
            "date": now().strftime("%Y-%m-%d"),
        }

    async def weekly(self) -> dict:
        start = week_start()
        end = today_end()

        logs = await list_worklogs(self.session, user_id=self.user_id, limit=100)
        this_week = [w for w in logs if w.created_at and start <= w.created_at <= end]

        done = [w for w in this_week if w.status == "done"]
        in_progress = [w for w in this_week if w.status == "in_progress"]

        return {
            "done": done,
            "in_progress": in_progress,
            "total": len(this_week),
            "week_start": start.strftime("%d %b"),
            "week_end": end.strftime("%d %b"),
        }

    async def upcoming_actions(self, days: int = 7) -> list[Interaction]:
        return await get_upcoming_actions(self.session, self.user_id, days=days)
