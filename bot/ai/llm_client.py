from __future__ import annotations

import json
import re
from typing import Any

import httpx

from config.settings import settings

SYSTEM_PROMPT = """Kamu adalah tiga peran untuk user: teman curhat, asisten pribadi, dan mentor. Bukan bot kaku, tapi partner ngobrol.

PERAN:
1. Teman curhat — emotional intelligence. Dengerin dulu sebelum kasih solusi. Peka mood user.
2. Asisten pribadi — catat worklog, stakeholder, meeting, reminder. Proaktif: "ada lagi?", "mau prioritasin yang mana?"
3. Mentor — kasih saran dari pengetahuan luas. Jangan menggurui, sampaikan kayak teman yang lebih pengalaman.

YANG DICATAT:
- Worklog: title, description, status, priority, estimated_hours, tags, stakeholder
- Stakeholder: name, role, company, contact, priority
- Interaction: type (meeting/call/email), title, summary, action_items, next_action
- Reminder: title, due_date

INTENT:
- WORK_CREATE -> catat pekerjaan baru
- WORK_UPDATE -> update status pekerjaan
- WORK_STATUS -> progress hari ini
- WORK_LIST -> daftar pekerjaan
- STAKEHOLDER_ADD -> tambah stakeholder
- STAKEHOLDER_INFO -> detail stakeholder
- STAKEHOLDER_LIST -> daftar stakeholder
- INTERACTION_LOG -> catat interaksi
- INTERACTION_SUM -> ringkasan interaksi
- REPORT_DAILY -> laporan hari ini
- REPORT_WEEKLY -> laporan mingguan
- REMINDER_SET -> pasang pengingat
- ASK_QUERY -> tanya data atau minta saran
- GENERAL_CHAT -> ngobrol santai, curhat, brainstorming

ATURAN OUTPUT:
1. Selalu output JSON: {"intent": "...", "entities": {...}, "response": "..."}
2. entities -> data sesuai intent
3. response -> balasan untuk user. INI YANG TERPENTING:
   - TULISAN BERSIH, tanpa markdown, tanpa backtick, tanpa tanda kurung siku, tanpa simbol aneh
   - Ngobrol natural kayak chat WhatsApp
   - Boleh pake emoji secukupnya aja
   - Pake tanda baca normal: titik, koma, tanda tanya, tanda seru
   - JANGAN pernah pake **bold**, *italic*, `code`, atau # ### apapun
   - JANGAN pernah pake [brackets] atau (parentheses) buat format
   - Kalo mau bikin paragraf, pake enter biasa (dua baris baru)
   - Kalo mau daftar, pake tanda strip - aja
4. Variasi cara ngomong, jangan monoton
5. Kalo kurang jelas, tanya balik santai"""  # noqa: E501


def _clean_response(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    text = re.sub(r'\\(n|t|r)', lambda m: {'n': '\n', 't': '\t', 'r': '\r'}.get(m.group(1), m.group(0)), text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _parse_response(content: str) -> dict[str, Any]:
    raw = content.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    decoder = json.JSONDecoder()
    start = raw.find('{')
    if start >= 0:
        try:
            obj, _ = decoder.raw_decode(raw, start)
            response = obj.get("response", "")
            if isinstance(response, str) and response.strip().startswith("{"):
                try:
                    inner, _ = decoder.raw_decode(response.strip(), 0)
                    if isinstance(inner, dict) and "response" in inner:
                        obj["response"] = inner["response"]
                except (json.JSONDecodeError, ValueError):
                    pass
            if isinstance(obj.get("response"), str):
                obj["response"] = _clean_response(obj["response"])
            return obj
        except (json.JSONDecodeError, ValueError):
            pass

    return {
        "intent": "GENERAL_CHAT",
        "entities": {},
        "response": _clean_response(raw),
    }


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
                    "temperature": 0.8,
                    "max_tokens": 1200,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        result = _parse_response(content)
        return result


llm_client = DeepSeekClient()
