from __future__ import annotations

import asyncio
import logging
import sys

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot.handlers.commands import (
    ask,
    export_csv,
    health,
    help_command,
    list_actions,
    meeting_log,
    remind,
    report_daily,
    report_weekly,
    search,
    stakeholder_add,
    stakeholder_info,
    stakeholder_list,
    start,
    work_create,
    work_delete,
    work_done,
    work_edit,
    work_list,
    work_status,
)
from bot.handlers.errors import error_handler
from bot.handlers.messages import handle_message
from bot.scheduler import create_scheduler
from config.settings import settings
from db.connection import close_db, init_db

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    log_dir = settings.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "bot.log", encoding="utf-8"),
        ],
    )


def build_application() -> Application:
    app = Application.builder().token(settings.telegram_bot_token).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("health", health))

    app.add_handler(CommandHandler("work", work_create))
    app.add_handler(CommandHandler("work_done", work_done))
    app.add_handler(CommandHandler("work_list", work_list))
    app.add_handler(CommandHandler("work_status", work_status))

    app.add_handler(CommandHandler("report", report_daily))
    app.add_handler(CommandHandler("report_weekly", report_weekly))

    app.add_handler(CommandHandler("stakeholder_add", stakeholder_add))
    app.add_handler(CommandHandler("stakeholder_list", stakeholder_list))
    app.add_handler(CommandHandler("stakeholder", stakeholder_info))

    app.add_handler(CommandHandler("meet", meeting_log))
    app.add_handler(CommandHandler("actions", list_actions))

    app.add_handler(CommandHandler("work_edit", work_edit))
    app.add_handler(CommandHandler("work_delete", work_delete))

    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(CommandHandler("ask", ask))

    app.add_handler(CommandHandler("export", export_csv))
    app.add_handler(CommandHandler("search", search))

    # Message handler (natural language → AI)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Error handler
    app.add_error_handler(error_handler)

    return app


async def main() -> None:
    setup_logging()
    logger.info("Starting WorkTracker AI Agent...")

    await init_db()
    logger.info("Database initialized.")

    app = build_application()
    scheduler = create_scheduler(app)

    async with app:
        await app.start()
        logger.info("Bot started. Polling for updates...")
        await app.updater.start_polling()

        scheduler.start()
        logger.info("Scheduler started (reminders every 60s, Gmail every 120s).")

        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("Shutting down...")
            scheduler.shutdown(wait=False)
            await app.updater.stop()
            await app.stop()
            await close_db()


if __name__ == "__main__":
    asyncio.run(main())
