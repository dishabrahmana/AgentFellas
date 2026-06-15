from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import WorklogEntry
from db.repository import (
    create_worklog,
    delete_worklog,
    get_worklog,
    get_today_logs,
    list_worklogs,
    update_worklog,
)


class WorklogService:
    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self.session = session
        self.user_id = user_id

    async def create(
        self,
        title: str,
        description: str | None = None,
        status: str = "in_progress",
        priority: str = "medium",
        tags: list[str] | None = None,
        stakeholder_id: int | None = None,
        estimated_hours: float | None = None,
    ) -> WorklogEntry:
        return await create_worklog(
            self.session,
            user_id=self.user_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            tags=tags,
            stakeholder_id=stakeholder_id,
            estimated_hours=estimated_hours,
        )

    async def get(self, worklog_id: int) -> WorklogEntry | None:
        return await get_worklog(self.session, worklog_id)

    async def list(self, status: str | None = None, limit: int = 20) -> list[WorklogEntry]:
        return await list_worklogs(
            self.session, user_id=self.user_id, status=status, limit=limit
        )

    async def update(
        self, worklog_id: int, **kwargs
    ) -> WorklogEntry | None:
        return await update_worklog(self.session, worklog_id, **kwargs)

    async def delete(self, worklog_id: int) -> bool:
        return await delete_worklog(self.session, worklog_id)

    async def get_today(self) -> list[WorklogEntry]:
        return await get_today_logs(self.session, self.user_id)

    async def complete(self, worklog_id: int) -> WorklogEntry | None:
        return await update_worklog(self.session, worklog_id, status="done")
