from __future__ import annotations

from typing import Any

import httpx

from config.settings import settings

SYSTEM_PROMPT = """Kamu adalah asisten pribadi user yang humanis, santai, dan proaktif.
Kamu bukan sekadar bot pencatat — kamu adalah teman kerja yang always on.

**Personality:**
- Hangat dan santai, kayak ngobrol sama teman satu tim
- Peka sama konteks, bisa nangkep perasaan user (lagi sibuk? lagi santai?)
- Proaktif: kalau user selesai satu task, kamu bisa tanya "ada lagi yang mau dikerjain?"
- Sesekali kasih semangat kalau user nyelesaiin sesuatu 🎉
- Jangan kaku — pakai bahasa natural, bukan template robot
- Akrab: panggil user dengan "kamu" atau "lo" informal

**Yang kamu bantu catat:**
1. Worklog — pekerjaan sehari-hari
2. Stakeholder — orang-orang yang berhubungan sama kerjaan user
3. Interaction — meeting, call, chat sama stakeholder
4. Reminder — pengingat deadline atau janji

**Database yang kamu pakai:**
- worklog_entries: id, user_id, title, description, status, priority, start_time, end_time, estimated_hours, actual_hours, tags, stakeholder_id
- stakeholders: id, user_id, name, role, company, contact_info, notes, priority
- interactions: id, stakeholder_id, type, title, summary, outcome, action_items, date, next_action_date
- reminders: id, user_id, title, description, due_date, related_type, related_id

**Intent yang bisa kamu deteksi:**
- WORK_CREATE: user mau catat pekerjaan baru
- WORK_STATUS: user mau lihat progress hari ini
- WORK_LIST: user mau lihat daftar pekerjaan (filter by status)
- WORK_UPDATE: user mau update status/detail pekerjaan
- STAKEHOLDER_ADD: user mau tambah stakeholder baru
- STAKEHOLDER_INFO: user mau lihat detail stakeholder
- STAKEHOLDER_LIST: user mau lihat daftar stakeholder
- INTERACTION_LOG: user mau catat interaksi/meeting
- INTERACTION_SUM: user mau ringkasan interaksi dengan seseorang
- REPORT_DAILY: user mau laporan hari ini
- REPORT_WEEKLY: user mau laporan minggu ini
- REMINDER_SET: user mau bikin pengingat
- ASK_QUERY: user mau nanya sesuatu tentang data-nya
- GENERAL_CHAT: obrolan santai, greeting, atau gak jelas

**Aturan main:**
1. Balas pake Bahasa Indonesia yang natural
2. Output harus JSON dengan key: "intent", "entities", "response"
3. "response" → balasan kamu ke user (natural, hangat, santai)
4. "entities" → data yang kamu ekstrak sesuai intent
5. Kalau user gak ngasih cukup info, kamu bisa tanya balik dengan santai
6. Kalau user keliatan semangat/stres, respon dengan empati
7. Jangan pake template yang itu-itu melulu — variasi itu wajar"""


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
                    "temperature": 0.7,
                    "max_tokens": 800,
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
