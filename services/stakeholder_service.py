from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Stakeholder
from db.repository import (
    create_stakeholder,
    find_stakeholder_by_name,
    get_stakeholder,
    list_stakeholders,
    update_stakeholder,
)


class StakeholderService:
    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self.session = session
        self.user_id = user_id

    async def create(
        self,
        name: str,
        role: str | None = None,
        company: str | None = None,
        contact_info: dict | None = None,
        notes: str | None = None,
        priority: str = "medium",
    ) -> Stakeholder:
        return await create_stakeholder(
            self.session,
            user_id=self.user_id,
            name=name,
            role=role,
            company=company,
            contact_info=contact_info,
            notes=notes,
            priority=priority,
        )

    async def get(self, stakeholder_id: int) -> Stakeholder | None:
        return await get_stakeholder(self.session, stakeholder_id)

    async def find_by_name(self, name: str) -> Stakeholder | None:
        return await find_stakeholder_by_name(self.session, self.user_id, name)

    async def list(self, active_only: bool = True) -> list[Stakeholder]:
        return await list_stakeholders(self.session, self.user_id, active_only=active_only)

    async def update(
        self, stakeholder_id: int, **kwargs
    ) -> Stakeholder | None:
        return await update_stakeholder(self.session, stakeholder_id, **kwargs)

    async def deactivate(self, stakeholder_id: int) -> Stakeholder | None:
        return await update_stakeholder(self.session, stakeholder_id, is_active=False)
