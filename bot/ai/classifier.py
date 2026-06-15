from __future__ import annotations

from typing import Any

from bot.ai.llm_client import llm_client

KNOWN_INTENTS = frozenset({
    "WORK_CREATE",
    "WORK_UPDATE",
    "WORK_STATUS",
    "WORK_LIST",
    "STAKEHOLDER_ADD",
    "STAKEHOLDER_INFO",
    "STAKEHOLDER_LIST",
    "INTERACTION_LOG",
    "INTERACTION_SUM",
    "REPORT_DAILY",
    "REPORT_WEEKLY",
    "REMINDER_SET",
    "ASK_QUERY",
    "GENERAL_CHAT",
})


async def classify_and_extract(
    message: str,
    context: dict | None = None,
) -> dict[str, Any]:
    result = await llm_client.chat(message, context)

    intent = result.get("intent", "GENERAL_CHAT")
    if intent not in KNOWN_INTENTS:
        intent = "GENERAL_CHAT"

    return {
        "intent": intent,
        "entities": result.get("entities", {}),
        "response": result.get("response", ""),
    }
