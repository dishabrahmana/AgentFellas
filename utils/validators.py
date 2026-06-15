from __future__ import annotations

from typing import Any


def validate_status(status: str) -> str:
    valid = {"todo", "in_progress", "done", "blocked", "cancelled"}
    if status.lower() not in valid:
        return "in_progress"
    return status.lower()


def validate_priority(priority: str) -> str:
    valid = {"low", "medium", "high", "critical"}
    if priority.lower() not in valid:
        return "medium"
    return priority.lower()


def validate_role(role: str) -> str:
    valid = {"client", "manager", "partner", "vendor", "internal", "other"}
    if role and role.lower() not in valid:
        return "other"
    return role.lower() if role else "other"


def validate_interaction_type(typ: str) -> str:
    valid = {"meeting", "call", "email", "chat", "briefing", "other"}
    if typ.lower() not in valid:
        return "other"
    return typ.lower()


def sanitize_text(text: str | None, max_length: int = 500) -> str:
    if not text:
        return ""
    return text.strip()[:max_length]
