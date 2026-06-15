from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from db.models import Interaction, Stakeholder, WorklogEntry
from utils.date_utils import format_date, format_datetime, format_duration

STATUS_EMOJI = {
    "todo": "📋",
    "in_progress": "🔄",
    "done": "✅",
    "blocked": "🚫",
    "cancelled": "❌",
}

PRIORITY_MARKER = {
    "low": "🟢",
    "medium": "🟡",
    "high": "🔴",
    "critical": "💀",
}


def format_worklog(entry: WorklogEntry) -> str:
    status_emoji = STATUS_EMOJI.get(entry.status, "📋")
    priority_marker = PRIORITY_MARKER.get(entry.priority, "⚪")
    tags_list = _parse_json_list(entry.tags)
    tags_str = f" `{' '.join(tags_list)}`" if tags_list else ""

    lines = [
        f"{status_emoji} *{entry.title}*{tags_str}",
        f"   Prioritas: {priority_marker} {entry.priority}",
        f"   Status: {entry.status.replace('_', ' ')}",
    ]

    if entry.description:
        lines.append(f"   📝 {entry.description}")

    if entry.estimated_hours:
        actual = format_duration(entry.actual_hours)
        estimated = format_duration(entry.estimated_hours)
        lines.append(f"   ⏱ Estimasi: {estimated} | Realisasi: {actual}")

    if entry.start_time:
        lines.append(f"   🕐 Mulai: {format_datetime(entry.start_time)}")

    if entry.stakeholder:
        lines.append(f"   👤 Stakeholder: {entry.stakeholder.name}")

    lines.append(f"   🆔 #{entry.id}")
    return "\n".join(lines)


def format_worklog_list(entries: list[WorklogEntry]) -> str:
    if not entries:
        return "📭 Belum ada worklog."

    grouped: dict[str, list[WorklogEntry]] = {}
    for e in entries:
        grouped.setdefault(e.status, []).append(e)

    parts = []
    status_order = ["in_progress", "todo", "done", "blocked", "cancelled"]
    for status in status_order:
        if status not in grouped:
            continue
        emoji = STATUS_EMOJI.get(status, "📋")
        label = status.replace("_", " ").title()
        parts.append(f"\n{emoji} *{label}* ({len(grouped[status])})")
        for e in grouped[status]:
            parts.append(f"  • #{e.id} {e.title}")

    return "\n".join(parts)


def format_stakeholder(sh: Stakeholder) -> str:
    contact = _parse_json_dict(sh.contact_info)
    contact_lines = []
    if contact.get("telegram"):
        contact_lines.append(f"   📱 Telegram: {contact['telegram']}")
    if contact.get("email"):
        contact_lines.append(f"   📧 Email: {contact['email']}")
    if contact.get("phone"):
        contact_lines.append(f"   📞 Phone: {contact['phone']}")

    lines = [
        f"👤 *{sh.name}*",
    ]
    if sh.role:
        lines.append(f"   🏷 Role: {sh.role}")
    if sh.company:
        lines.append(f"   🏢 Perusahaan: {sh.company}")
    if contact_lines:
        lines.extend(contact_lines)
    if sh.notes:
        lines.append(f"   📝 {sh.notes}")
    lines.append(f"   🆔 #{sh.id}")
    return "\n".join(lines)


def format_stakeholder_list(stakeholders: list[Stakeholder]) -> str:
    if not stakeholders:
        return "📭 Belum ada stakeholder."

    parts = ["📋 *Daftar Stakeholder:*"]
    for sh in stakeholders:
        marker = PRIORITY_MARKER.get(sh.priority, "⚪")
        role_str = f" ({sh.role})" if sh.role else ""
        company_str = f" — {sh.company}" if sh.company else ""
        parts.append(f"  {marker} #{sh.id} {sh.name}{role_str}{company_str}")

    return "\n".join(parts)


def format_interaction(ix: Interaction) -> str:
    action_items = _parse_json_list(ix.action_items)
    actions_str = ""
    if action_items:
        items = "\n".join(f"     • {a}" for a in action_items)
        actions_str = f"\n   📋 Action Items:\n{items}"

    lines = [
        f"📅 *{ix.title}*",
        f"   Tipe: {ix.type}",
        f"   Tanggal: {format_date(ix.date)}",
    ]
    if ix.summary:
        lines.append(f"   📝 {ix.summary}")
    if ix.outcome:
        lines.append(f"   ✅ Outcome: {ix.outcome}")
    if ix.next_action_date:
        lines.append(f"   ⏰ Next action: {format_date(ix.next_action_date)}")
    if actions_str:
        lines.append(actions_str)

    return "\n".join(lines)


def format_daily_report(
    done: list[WorklogEntry],
    in_progress: list[WorklogEntry],
    upcoming: list[dict[str, Any]],
) -> str:
    parts = ["📋 *Daily Report*\n"]

    parts.append("✅ *Completed:*")
    if done:
        for w in done:
            dur = format_duration(w.actual_hours) if w.actual_hours else ""
            parts.append(f"  • {w.title} {dur}")
    else:
        parts.append("  (none)")

    parts.append("\n🔄 *In Progress:*")
    if in_progress:
        for w in in_progress:
            parts.append(f"  • {w.title}")
    else:
        parts.append("  (none)")

    parts.append("\n⏰ *Upcoming / Reminders:*")
    if upcoming:
        for u in upcoming:
            parts.append(f"  • {u.get('title', '')}")
    else:
        parts.append("  (none)")

    return "\n".join(parts)


def _parse_json_list(data: str | None) -> list[str]:
    if not data:
        return []
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return []


def _parse_json_dict(data: str | None) -> dict[str, str]:
    if not data:
        return {}
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return {}
