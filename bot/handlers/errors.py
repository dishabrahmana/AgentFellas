from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def error_handler(update: Update | None, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception(
        "Unhandled error in update %s: %s", update, context.error
    )
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Maaf, terjadi error internal. Silakan coba lagi."
        )
