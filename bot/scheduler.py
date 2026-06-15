from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from config.settings import settings
from db.connection import async_session_factory
from services.reminder_service import ReminderService

logger = logging.getLogger(__name__)


async def check_reminders(app: Application) -> None:
    async with async_session_factory() as session:
        svc = ReminderService(session, settings.telegram_user_id)
        reminders = await svc.get_due(within_minutes=5)

        for reminder in reminders:
            text = (
                f"⏰ *Reminder:* {reminder.title}\n"
                f"📅 Due: {reminder.due_date.strftime('%d %b %Y, %H:%M')}"
            )
            try:
                await app.bot.send_message(
                    chat_id=int(settings.telegram_user_id) if settings.telegram_user_id.isdigit() else settings.telegram_user_id,
                    text=text,
                    parse_mode="Markdown",
                )
                await svc.mark_done(reminder.id)
            except Exception as e:
                logger.error("Failed to send reminder notification: %s", e)


async def poll_gmail(app: Application) -> None:
    from integrations.gmail_client import gmail_client

    if not gmail_client._initialized:
        ok = await gmail_client.initialize()
        if not ok:
            return

    emails = await gmail_client.fetch_unread(max_results=5)
    for email in emails:
        text = (
            f"📧 *Email dari:* {email['from']}\n"
            f"*Subjek:* {email['subject']}\n"
            f"{email['body'][:500]}"
        )
        try:
            await app.bot.send_message(
                chat_id=int(settings.telegram_user_id) if settings.telegram_user_id.isdigit() else settings.telegram_user_id,
                text=text,
                parse_mode="Markdown",
            )
            await gmail_client.mark_read(email["id"])
        except Exception as e:
            logger.error("Failed to send email notification: %s", e)


def create_scheduler(app: Application) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_reminders,
        "interval",
        seconds=60,
        args=[app],
        id="check_reminders",
        replace_existing=True,
    )
    if settings.gmail_credentials_file:
        scheduler.add_job(
            poll_gmail,
            "interval",
            seconds=120,
            args=[app],
            id="poll_gmail",
            replace_existing=True,
        )
    return scheduler
