from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Interaction
from db.repository import (
    create_interaction,
    get_upcoming_actions,
    list_interactions,
)


class InteractionService:
    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self.session = session
        self.user_id = user_id

    async def log(
        self,
        stakeholder_id: int,
        typ: str,
        title: str,
        summary: str | None = None,
        outcome: str | None = None,
        action_items: list[str] | None = None,
        date: datetime | None = None,
        next_action_date: datetime | None = None,
    ) -> Interaction:
        return await create_interaction(
            self.session,
            stakeholder_id=stakeholder_id,
            typ=typ,
            title=title,
            summary=summary,
            outcome=outcome,
            action_items=action_items,
            date=date,
            next_action_date=next_action_date,
        )

    async def list(self, stakeholder_id: int, limit: int = 10) -> list[Interaction]:
        return await list_interactions(self.session, stakeholder_id, limit=limit)

    async def get_upcoming(self, days: int = 7) -> list[Interaction]:
        return await get_upcoming_actions(self.session, self.user_id, days=days)
