from __future__ import annotations

import json
import re

from telegram import Update
from telegram.ext import ContextTypes

from bot.ai.classifier import classify_and_extract
from db.connection import async_session_factory
from db.repository import get_or_create_session, update_session_context
from services.interaction_service import InteractionService
from services.report_service import ReportService
from services.stakeholder_service import StakeholderService
from services.worklog_service import WorklogService
from utils.formatters import (
    format_daily_report,
    format_interaction,
    format_stakeholder,
    format_stakeholder_list,
    format_worklog,
    format_worklog_list,
)
from utils.date_utils import format_date


GOOGLE_URL_PATTERNS = re.compile(
    r"(https?://(?:docs|sheets|drive|docs)\.google\.com/(?:spreadsheets/d|document/d|file/d)/([a-zA-Z0-9_-]+))"
)


async def handle_google_url(url: str) -> str | None:
    from integrations.google_drive_client import google_drive_client

    info = google_drive_client.extract_id_from_url(url)
    if not info["id"]:
        return None

    if not google_drive_client._initialized:
        ok = await google_drive_client.initialize()
        if not ok:
            return "Google Drive belum terhubung. Pastikan GMAIL_CREDENTIALS_FILE sudah diatur."

    file_name = await google_drive_client.get_file_name(info["id"])
    name_str = f"**{file_name}**\n\n" if file_name else ""

    if info["type"] == "sheet":
        values = await google_drive_client.read_sheet(info["id"])
        if not values:
            return f"{name_str}Spreadsheet kosong atau tidak bisa dibaca."
        text = f"📊 {name_str}"
        for i, row in enumerate(values[:20]):
            text += " | ".join(str(c) for c in row) + "\n"
        if len(values) > 20:
            text += f"... dan {len(values) - 20} baris lagi"
        return text

    if info["type"] == "doc":
        text = await google_drive_client.read_doc(info["id"])
        if not text:
            return f"{name_str}Dokumen kosong atau tidak bisa dibaca."
        return f"📄 {name_str}{text[:2000]}"

    return f"{name_str}Tipe file Google belum didukung."


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.message.text
    user_id = str(user.id)
    chat_id = str(update.effective_chat.id)

    google_match = re.search(GOOGLE_URL_PATTERNS, message)
    if google_match:
        result = await handle_google_url(google_match.group(1))
        if result:
            await update.message.reply_text(result, parse_mode="Markdown")
            return

    async with async_session_factory() as session:
        user_session = await get_or_create_session(session, user_id, chat_id)
        conv_history = json.loads(user_session.conversation_history or "[]")

        ai_result = await classify_and_extract(message, {"conversation_history": conv_history})
        intent = ai_result["intent"]
        entities = ai_result.get("entities", {})

        conv_history.append({"role": "user", "content": message})
        conv_history.append({"role": "assistant", "content": ai_result.get("response", "")})
        if len(conv_history) > 20:
            conv_history = conv_history[-20:]

        await update_session_context(
            session,
            user_session.id,
            last_intent=intent,
            last_entity=json.dumps(entities),
            conversation_history=json.dumps(conv_history),
        )

        wl_svc = WorklogService(session, user_id)
        sh_svc = StakeholderService(session, user_id)
        ix_svc = InteractionService(session, user_id)
        rp_svc = ReportService(session, user_id)

        if intent == "WORK_CREATE":
            title = entities.get("title", message)
            entry = await wl_svc.create(
                title=title,
                description=entities.get("description"),
                status=entities.get("status", "in_progress"),
                priority=entities.get("priority", "medium"),
            )
            await update.message.reply_text(
                f"📝 Worklog dicatat:\n{format_worklog(entry)}",
                parse_mode="Markdown",
            )

        elif intent == "WORK_UPDATE":
            worklog_id = entities.get("id")
            status = entities.get("status", "done")
            if worklog_id:
                entry = await wl_svc.update(int(worklog_id), status=status)
                if entry:
                    await update.message.reply_text(
                        f"✅ Worklog diupdate:\n{format_worklog(entry)}",
                        parse_mode="Markdown",
                    )
                else:
                    await update.message.reply_text("Worklog tidak ditemukan.")
            else:
                await update.message.reply_text(
                    "Worklog mana yang mau diupdate? Saya butuh ID-nya."
                )

        elif intent == "WORK_STATUS":
            entries = await wl_svc.get_today()
            await update.message.reply_text(
                format_worklog_list(entries),
                parse_mode="Markdown",
            )

        elif intent == "WORK_LIST":
            status = entities.get("status")
            entries = await wl_svc.list(status=status)
            await update.message.reply_text(
                format_worklog_list(entries),
                parse_mode="Markdown",
            )

        elif intent == "STAKEHOLDER_ADD":
            name = entities.get("name", message)
            existing = await sh_svc.find_by_name(name)
            if existing:
                await update.message.reply_text(
                    f"Stakeholder '{name}' sudah ada di database."
                )
                return
            sh = await sh_svc.create(
                name=name,
                role=entities.get("role"),
                company=entities.get("company"),
                priority=entities.get("priority", "medium"),
            )
            await update.message.reply_text(
                f"👤 Stakeholder ditambahkan: {sh.name}"
                + (f" ({sh.role})" if sh.role else "")
                + (f" — {sh.company}" if sh.company else "")
            )

        elif intent == "STAKEHOLDER_LIST":
            stakeholders = await sh_svc.list()
            await update.message.reply_text(
                format_stakeholder_list(stakeholders),
                parse_mode="Markdown",
            )

        elif intent in ("REPORT_DAILY", "REPORT_WEEKLY"):
            if intent == "REPORT_WEEKLY":
                report = await rp_svc.weekly()
                text = (
                    f"📊 *Weekly Report*\n"
                    f"Periode: {report['week_start']} - {report['week_end']}\n\n"
                    f"✅ Completed: {len(report['done'])}\n"
                    f"🔄 In Progress: {len(report['in_progress'])}\n"
                    f"📝 Total: {report['total']}"
                )
                await update.message.reply_text(text, parse_mode="Markdown")
            else:
                report = await rp_svc.daily()
                await update.message.reply_text(
                    format_daily_report(
                        done=report["done"],
                        in_progress=report["in_progress"],
                        upcoming=report["upcoming"],
                    ),
                    parse_mode="Markdown",
                )

        elif intent == "INTERACTION_LOG":
            sh_name = entities.get("stakeholder_name")
            if sh_name:
                sh = await sh_svc.find_by_name(sh_name)
                if sh:
                    ix = await ix_svc.log(
                        stakeholder_id=sh.id,
                        typ=entities.get("type", "meeting"),
                        title=entities.get("title", sh_name),
                        summary=entities.get("summary"),
                        action_items=entities.get("action_items"),
                    )
                    await update.message.reply_text(
                        f"📅 Interaksi dicatat:\n{format_interaction(ix)}",
                        parse_mode="Markdown",
                    )
                else:
                    await update.message.reply_text(
                        f"Stakeholder '{sh_name}' tidak ditemukan. "
                        "Tambahkan dulu dengan /stakeholder_add"
                    )
            else:
                await update.message.reply_text(
                    "Siapa stakeholdernya? Saya perlu tahu nama stakeholder."
                )

        elif intent == "REMINDER_SET":
            from utils.date_utils import parse_relative_date

            title = entities.get("title", message)
            due_text = entities.get("due_date", "")
            due_date = parse_relative_date(due_text)
            if due_date:
                from db.repository import create_reminder

                reminder = await create_reminder(
                    session, user_id=user_id, title=title, due_date=due_date
                )
                await update.message.reply_text(
                    f"⏰ Reminder set: {title}\n"
                    f"📅 Due: {due_date.strftime('%d %b %Y, %H:%M')}"
                )
            else:
                await update.message.reply_text(
                    "Kapan deadline-nya? Contoh: 'besok', '3 hari lagi'"
                )

        elif intent == "STAKEHOLDER_INFO":
            name = entities.get("name")
            if name:
                sh = await sh_svc.find_by_name(name)
                if sh:
                    await update.message.reply_text(
                        format_stakeholder(sh),
                        parse_mode="Markdown",
                    )
                else:
                    await update.message.reply_text(
                        f"Stakeholder '{name}' tidak ditemukan."
                    )
            else:
                await update.message.reply_text(
                    "Siapa stakeholder yang mau dilihat? Saya butuh namanya."
                )

        elif intent == "INTERACTION_SUM":
            sh_name = entities.get("stakeholder_name")
            if sh_name:
                sh = await sh_svc.find_by_name(sh_name)
                if sh:
                    interactions = await ix_svc.list(stakeholder_id=sh.id, limit=5)
                    if interactions:
                        text = f"📅 *Interaksi dengan {sh.name}*\n"
                        for ix in interactions:
                            text += (
                                f"\n• {format_date(ix.date)} — {ix.title}"
                                f" ({ix.type})"
                            )
                            if ix.summary:
                                text += f"\n  {ix.summary[:100]}"
                        await update.message.reply_text(text, parse_mode="Markdown")
                    else:
                        await update.message.reply_text(
                            f"Belum ada interaksi dengan {sh_name}."
                        )
                else:
                    await update.message.reply_text(
                        f"Stakeholder '{sh_name}' tidak ditemukan."
                    )
            else:
                await update.message.reply_text(
                    "Interaksi dengan stakeholder siapa? Saya butuh namanya."
                )

        elif intent == "ASK_QUERY":
            response = ai_result.get("response", "Maaf, saya kurang paham.")
            await update.message.reply_text(response)

        else:
            response = ai_result.get("response", "Maaf, saya kurang paham. Bisa dijelaskan lagi?")
            await update.message.reply_text(response)
