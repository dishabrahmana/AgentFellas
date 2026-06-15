from __future__ import annotations

from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from bot.ai.classifier import classify_and_extract
from db.connection import async_session_factory
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
        "/work_status - Status hari ini\n\n"
        "*Stakeholder:*\n"
        "/stakeholder_add <nama> - Tambah stakeholder\n"
        "/stakeholder_list - Lihat semua\n"
        "/stakeholder <id> - Lihat detail\n\n"
        "*Interaksi:*\n"
        "/meet <id> <topik> - Catat meeting\n"
        "/actions - Lihat upcoming actions\n\n"
        "*Report:*\n"
        "/report - Report hari ini\n"
        "/report_weekly - Report minggu ini\n\n"
        "*Lainnya:*\n"
        "/remind <teks> in <waktu> - Set reminder\n"
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
