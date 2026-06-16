from __future__ import annotations

import csv
import io
from datetime import datetime

from sqlalchemy import or_, select
from telegram import Update
from telegram.ext import ContextTypes

from bot.ai.classifier import classify_and_extract
from db.connection import async_session_factory
from db.models import Interaction, Stakeholder, WorklogEntry
from services.interaction_service import InteractionService
from services.reminder_service import ReminderService
from services.report_service import ReportService
from services.stakeholder_service import StakeholderService
from services.worklog_service import WorklogService
from utils.date_utils import format_datetime, parse_relative_date
from utils.formatters import (
    format_daily_report,
    format_interaction,
    format_stakeholder,
    format_stakeholder_list,
    format_worklog,
    format_worklog_list,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"Halo {user.first_name}! Saya WorkTracker AI Agent.\n\n"
        "Saya bisa membantu mencatat:\n"
        "📝 Pekerjaan (worklog)\n"
        "👤 Stakeholder\n"
        "📅 Interaksi & Meeting\n"
        "⏰ Reminder\n\n"
        "Cukup chat natural language, contoh:\n"
        "• \"lagi ngerjain fitur login\"\n"
        "• \"tambah stakeholder Budi dari PT Maju\"\n"
        "• \"tadi meeting dengan client\"\n"
        "• \"report hari ini\"\n\n"
        "Atau gunakan command:\n"
        "/work - Catat pekerjaan baru\n"
        "/stakeholder - Kelola stakeholder\n"
        "/report - Lihat report\n"
        "/help - Bantuan lengkap"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "*WorkTracker Commands:*\n\n"
        "*Worklog:*\n"
        "/work <judul> - Catat pekerjaan baru\n"
        "/work_done <id> - Tandai selesai\n"
        "/work_list - Lihat daftar aktif\n"
        "/work_status - Status hari ini\n"
        "/work_edit <id> <field=value> - Edit field worklog\n"
        "/work_delete <id> - Hapus worklog\n\n"
        "*Stakeholder:*\n"
        "/stakeholder_add <nama> - Tambah stakeholder\n"
        "/stakeholder_list - Lihat semua\n"
        "/stakeholder <id> - Lihat detail\n\n"
        "*Interaksi:*\n"
        "/meet <id> <topik> - Catat meeting\n"
        "/actions - Lihat upcoming actions\n\n"
        "*Report:*\n"
        "/report - Report hari ini\n"
        "/report_weekly - Report minggu ini\n"
        "/export - Export worklog ke CSV\n\n"
        "*Lainnya:*\n"
        "/remind <teks> in <waktu> - Set reminder\n"
        "/search <kata kunci> - Cari worklog & stakeholder\n"
        "/ask <pertanyaan> - Tanya AI\n"
        "/health - Cek status bot",
        parse_mode="Markdown",
    )


async def health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"✅ Bot aktif\n🕐 Server time: {format_datetime(datetime.now())}"
    )


async def work_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text(
            "Gunakan: /work <judul pekerjaan>\n"
            "Contoh: /work buat fitur login"
        )
        return

    user_id = str(update.effective_user.id)
    async with async_session_factory() as session:
        svc = WorklogService(session, user_id)
        entry = await svc.create(title=text)
        await update.message.reply_text(
            f"📝 Worklog dibuat:\n{format_worklog(entry)}",
            parse_mode="Markdown",
        )


async def work_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("Gunakan: /work_done <id>")
        return

    try:
        worklog_id = int(args[0])
    except ValueError:
        await update.message.reply_text("ID harus angka.")
        return

    user_id = str(update.effective_user.id)
    async with async_session_factory() as session:
        svc = WorklogService(session, user_id)
        entry = await svc.complete(worklog_id)
        if entry:
            await update.message.reply_text(
                f"✅ Worklog selesai:\n{format_worklog(entry)}",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text("Worklog tidak ditemukan.")


async def work_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    async with async_session_factory() as session:
        svc = WorklogService(session, user_id)
        entries = await svc.list()
        await update.message.reply_text(
            format_worklog_list(entries),
            parse_mode="Markdown",
        )


async def report_daily(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    async with async_session_factory() as session:
        svc = ReportService(session, user_id)
        report = await svc.daily()
        await update.message.reply_text(
            format_daily_report(
                done=report["done"],
                in_progress=report["in_progress"],
                upcoming=report["upcoming"],
            ),
            parse_mode="Markdown",
        )


async def report_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    async with async_session_factory() as session:
        svc = ReportService(session, user_id)
        report = await svc.weekly()
        done_count = len(report["done"])
        ip_count = len(report["in_progress"])
        total = report["total"]

        text = (
            f"📊 *Weekly Report*\n"
            f"Periode: {report['week_start']} - {report['week_end']}\n\n"
            f"✅ Completed: {done_count}\n"
            f"🔄 In Progress: {ip_count}\n"
            f"📝 Total: {total}\n\n"
        )
        if report["done"]:
            text += "*Completed:*\n"
            for w in report["done"]:
                text += f"  • #{w.id} {w.title}\n"

        await update.message.reply_text(text, parse_mode="Markdown")


async def stakeholder_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text(
            "Gunakan: /stakeholder_add <nama> [role] [company]\n"
            "Contoh: /stakeholder_add Budi Santoso client \"PT Maju\""
        )
        return

    user_id = str(update.effective_user.id)
    parts = text.split()
    name = parts[0]
    role = parts[1] if len(parts) > 1 else None
    company = " ".join(parts[2:]) if len(parts) > 2 else None

    async with async_session_factory() as session:
        svc = StakeholderService(session, user_id)
        existing = await svc.find_by_name(name)
        if existing:
            await update.message.reply_text(
                f"Stakeholder dengan nama '{name}' sudah ada:\n"
                f"{format_stakeholder(existing)}",
                parse_mode="Markdown",
            )
            return

        sh = await svc.create(name=name, role=role, company=company)
        await update.message.reply_text(
            f"👤 Stakeholder baru:\n{format_stakeholder(sh)}",
            parse_mode="Markdown",
        )


async def stakeholder_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    async with async_session_factory() as session:
        svc = StakeholderService(session, user_id)
        stakeholders = await svc.list()
        await update.message.reply_text(
            format_stakeholder_list(stakeholders),
            parse_mode="Markdown",
        )


async def meeting_log(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Gunakan: /meet <stakeholder_id> <topik meeting>\n"
            "Contoh: /meet 1 Progress Review"
        )
        return

    try:
        sh_id = int(args[0])
    except ValueError:
        await update.message.reply_text("ID stakeholder harus angka.")
        return

    title = " ".join(args[1:])
    user_id = str(update.effective_user.id)

    async with async_session_factory() as session:
        svc = InteractionService(session, user_id)
        ix = await svc.log(
            stakeholder_id=sh_id,
            typ="meeting",
            title=title,
        )
        await update.message.reply_text(
            f"📅 Meeting dicatat:\n{format_interaction(ix)}",
            parse_mode="Markdown",
        )


async def list_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    async with async_session_factory() as session:
        svc = InteractionService(session, user_id)
        actions = await svc.get_upcoming()

        if not actions:
            await update.message.reply_text("Tidak ada upcoming actions.")
            return

        text = "⏰ *Upcoming Actions:*\n"
        for a in actions:
            text += f"  • {a.title} (due: {a.next_action_date.strftime('%d %b')})\n"

        await update.message.reply_text(text, parse_mode="Markdown")


async def work_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    async with async_session_factory() as session:
        svc = WorklogService(session, user_id)
        entries = await svc.get_today()
        await update.message.reply_text(
            format_worklog_list(entries),
            parse_mode="Markdown",
        )


async def stakeholder_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text(
            "Gunakan: /stakeholder <id>\n"
            "Contoh: /stakeholder 1"
        )
        return

    try:
        sh_id = int(args[0])
    except ValueError:
        await update.message.reply_text("ID stakeholder harus angka.")
        return

    user_id = str(update.effective_user.id)
    async with async_session_factory() as session:
        svc = StakeholderService(session, user_id)
        sh = await svc.get(sh_id)
        if sh:
            await update.message.reply_text(
                format_stakeholder(sh),
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text("Stakeholder tidak ditemukan.")


async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text(
            "Gunakan: /remind <pesan> in <waktu>\n"
            "Contoh: /remind Follow up client in 3 hari"
        )
        return

    parts = text.split(" in ")
    title = parts[0].strip()
    due_text = parts[1].strip() if len(parts) > 1 else "besok"

    due_date = parse_relative_date(due_text)
    if not due_date:
        await update.message.reply_text(
            "Format waktu tidak dikenal. Contoh: 'besok', '3 hari lagi', 'minggu depan'"
        )
        return

    user_id = str(update.effective_user.id)
    async with async_session_factory() as session:
        svc = ReminderService(session, user_id)
        reminder = await svc.set(title=title, due_date=due_date)
        await update.message.reply_text(
            f"⏰ Reminder diset:\n"
            f"   {reminder.title}\n"
            f"   📅 Due: {format_datetime(reminder.due_date)}"
        )


async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = " ".join(context.args)
    if not question:
        await update.message.reply_text(
            "Gunakan: /ask <pertanyaan>\n"
            "Contoh: /ask Siapa stakeholder paling sering ditemui?"
        )
        return

    result = await classify_and_extract(question, None)
    response = result.get("response", "Maaf, saya kurang paham.")
    await update.message.reply_text(response)


async def export_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    async with async_session_factory() as session:
        svc = WorklogService(session, user_id)
        entries = await svc.list(limit=500)

        if not entries:
            await update.message.reply_text("📭 Belum ada worklog untuk di-export.")
            return

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "Title", "Description", "Status", "Priority",
            "Start Time", "End Time", "Estimated Hours", "Actual Hours",
            "Tags", "Created At",
        ])
        for w in entries:
            writer.writerow([
                w.id, w.title, w.description, w.status, w.priority,
                str(w.start_time or ""), str(w.end_time or ""),
                w.estimated_hours, w.actual_hours, w.tags,
                str(w.created_at or ""),
            ])

        csv_bytes = output.getvalue().encode("utf-8")
        await update.message.reply_document(
            document=io.BytesIO(csv_bytes),
            filename=f"worktracker_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            caption="📊 Export worklog berhasil",
        )


async def work_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Gunakan: /work_edit <id> <field=value>\n"
            "Contoh: /work_edit 1 status=done\n"
            "        /work_edit 1 title=\"fitur baru\" priority=high\n\n"
            "Field: title, description, status, priority, estimated_hours"
        )
        return

    try:
        worklog_id = int(args[0])
    except ValueError:
        await update.message.reply_text("ID worklog harus angka.")
        return

    updates = {}
    for arg in args[1:]:
        if "=" in arg:
            key, val = arg.split("=", 1)
            key = key.strip().lower()
            val = val.strip().strip('"')
            if key == "estimated_hours":
                try:
                    val = float(val)
                except ValueError:
                    continue
            updates[key] = val

    if not updates:
        await update.message.reply_text("Tidak ada field yang diupdate.")
        return

    user_id = str(update.effective_user.id)
    async with async_session_factory() as session:
        svc = WorklogService(session, user_id)
        entry = await svc.update(worklog_id, **updates)
        if entry:
            await update.message.reply_text(
                f"✅ Worklog diupdate:\n{format_worklog(entry)}",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text("Worklog tidak ditemukan.")


async def work_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("Gunakan: /work_delete <id>")
        return

    try:
        worklog_id = int(args[0])
    except ValueError:
        await update.message.reply_text("ID harus angka.")
        return

    user_id = str(update.effective_user.id)
    async with async_session_factory() as session:
        svc = WorklogService(session, user_id)
        entry = await svc.get(worklog_id)
        if not entry:
            await update.message.reply_text("Worklog tidak ditemukan.")
            return
        await svc.delete(worklog_id)
        await update.message.reply_text(
            f"🗑 Worklog #{worklog_id} **{entry.title}** dihapus.",
            parse_mode="Markdown",
        )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyword = " ".join(context.args)
    if not keyword:
        await update.message.reply_text("Gunakan: /search <kata kunci>")
        return

    user_id = str(update.effective_user.id)
    async with async_session_factory() as session:
        wl_query = (
            select(WorklogEntry)
            .where(
                WorklogEntry.user_id == user_id,
                or_(
                    WorklogEntry.title.ilike(f"%{keyword}%"),
                    WorklogEntry.description.ilike(f"%{keyword}%"),
                ),
            )
            .limit(10)
        )
        wl_result = await session.execute(wl_query)
        worklogs = list(wl_result.scalars().all())

        sh_query = (
            select(Stakeholder)
            .where(
                Stakeholder.user_id == user_id,
                or_(
                    Stakeholder.name.ilike(f"%{keyword}%"),
                    Stakeholder.company.ilike(f"%{keyword}%"),
                ),
            )
            .limit(10)
        )
        sh_result = await session.execute(sh_query)
        stakeholders = list(sh_result.scalars().all())

        text = f"🔍 *Hasil pencarian:* `{keyword}`\n"
        if worklogs:
            text += f"\n📝 *Worklog ({len(worklogs)}):*\n"
            for w in worklogs:
                text += f"  • #{w.id} {w.title}\n"
        if stakeholders:
            text += f"\n👤 *Stakeholder ({len(stakeholders)}):*\n"
            for s in stakeholders:
                text += f"  • #{s.id} {s.name} ({s.company or '-'})\n"
        if not worklogs and not stakeholders:
            text += "\n(tidak ada hasil)"

        await update.message.reply_text(text, parse_mode="Markdown")
