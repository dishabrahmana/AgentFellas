from __future__ import annotations

from typing import Any

import httpx

from config.settings import settings

SYSTEM_PROMPT = """Kamu adalah asisten AI untuk mencatat pekerjaan dan stakeholder.
Tugasmu adalah membantu user mencatat:
1. Worklog (pekerjaan) — judul, deskripsi, status, prioritas
2. Stakeholder — nama, role, perusahaan, kontak
3. Interaction — meeting, call, email dengan stakeholder

Database schema:
- worklog_entries: id, user_id, title, description, status, priority, start_time, end_time, estimated_hours, actual_hours, tags, stakeholder_id
- stakeholders: id, user_id, name, role, company, contact_info, notes, priority
- interactions: id, stakeholder_id, type, title, summary, outcome, action_items, date, next_action_date
- reminders: id, user_id, title, description, due_date, related_type, related_id

Intent yang bisa kamu deteksi:
- WORK_CREATE: user mau catat pekerjaan baru
- WORK_UPDATE: user mau update status pekerjaan
- WORK_STATUS: user mau lihat progress
- WORK_LIST: user mau lihat daftar pekerjaan
- STAKEHOLDER_ADD: user mau tambah stakeholder baru
- STAKEHOLDER_INFO: user mau lihat info stakeholder
- STAKEHOLDER_LIST: user mau lihat daftar stakeholder
- INTERACTION_LOG: user mau catat interaksi
- INTERACTION_SUM: user mau ringkasan interaksi
- REPORT_DAILY: user mau report harian
- REPORT_WEEKLY: user mau report mingguan
- REMINDER_SET: user mau set reminder
- ASK_QUERY: user mau tanya tentang data
- GENERAL_CHAT: percakapan umum / greeting / unclear

Balas dalam Bahasa Indonesia.
Format: JSON dengan key "intent", "entities", "response".
entities harus berisi field yang relevan dengan intent."""


class DeepSeekClient:
    def __init__(self) -> None:
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_api_url
        self.model = "deepseek-chat"

    async def chat(self, message: str, context: dict | None = None) -> dict[str, Any]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if context and context.get("conversation_history"):
            for msg in context["conversation_history"][-6:]:
                messages.append(msg)

        messages.append({"role": "user", "content": message})

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        result = self._parse_response(content)
        return result

    def _parse_response(self, content: str) -> dict[str, Any]:
        import json
        import re

        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return {
            "intent": "GENERAL_CHAT",
            "entities": {},
            "response": content.strip(),
        }


llm_client = DeepSeekClient()
