from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from datetime import datetime, timedelta
from email import message_from_bytes
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config.settings import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]


class GmailClient:
    def __init__(self) -> None:
        self.service = None
        self.creds = None
        self._initialized = False

    async def initialize(self) -> bool:
        if not settings.gmail_credentials_file:
            logger.warning("GMAIL_CREDENTIALS_FILE not set. Gmail integration disabled.")
            return False

        creds_file = settings.gmail_credentials_file
        if not os.path.exists(creds_file):
            logger.warning("Gmail credentials file not found: %s", creds_file)
            return False

        self.creds = None
        token_file = os.path.join(os.path.dirname(creds_file), "gmail_token.json")
        if os.path.exists(token_file):
            self.creds = Credentials.from_authorized_user_file(token_file, SCOPES)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                await asyncio.to_thread(self.creds.refresh, Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
                self.creds = await asyncio.to_thread(flow.run_local_server, port=0)
            async with asyncio.Lock():
                with open(token_file, "w") as f:
                    f.write(self.creds.to_json())

        self.service = build("gmail", "v1", credentials=self.creds)
        self._initialized = True
        logger.info("Gmail client initialized.")
        return True

    async def fetch_unread(self, max_results: int = 10) -> list[dict[str, Any]]:
        if not self._initialized:
            return []

        try:
            results = await asyncio.to_thread(
                self.service.users()
                .messages()
                .list(userId="me", q="is:unread", maxResults=max_results)
                .execute
            )
            messages = results.get("messages", [])
            parsed = []
            for msg in messages:
                data = await self._get_message(msg["id"])
                if data:
                    parsed.append(data)
            return parsed
        except Exception as e:
            logger.error("Error fetching Gmail: %s", e)
            return []

    async def _get_message(self, msg_id: str) -> dict[str, Any] | None:
        try:
            msg = await asyncio.to_thread(
                self.service.users()
                .messages()
                .get(userId="me", id=msg_id, format="raw")
                .execute
            )
            raw = base64.urlsafe_b64decode(msg["raw"].encode("ASCII"))
            mime_msg = message_from_bytes(raw)

            subject = mime_msg["subject"] or "(no subject)"
            sender = mime_msg["from"] or "(unknown)"
            date_str = mime_msg["date"] or ""

            body = ""
            if mime_msg.is_multipart():
                for part in mime_msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode(
                                "utf-8", errors="replace"
                            )
                        except Exception:
                            pass
                        break
            else:
                try:
                    body = mime_msg.get_payload(decode=True).decode(
                        "utf-8", errors="replace"
                    )
                except Exception:
                    pass

            return {
                "id": msg_id,
                "subject": subject,
                "from": sender,
                "date": date_str,
                "body": body[:2000],
            }
        except Exception as e:
            logger.error("Error parsing message %s: %s", msg_id, e)
            return None

    async def mark_read(self, msg_id: str) -> None:
        if not self._initialized:
            return
        try:
            await asyncio.to_thread(
                self.service.users()
                .messages()
                .modify(
                    userId="me",
                    id=msg_id,
                    body={"removeLabelIds": ["UNREAD"]},
                ).execute
            )
        except Exception as e:
            logger.error("Error marking message %s read: %s", msg_id, e)

    async def search_recent(
        self, query: str, max_results: int = 5
    ) -> list[dict[str, Any]]:
        if not self._initialized:
            return []
        try:
            results = await asyncio.to_thread(
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute
            )
            messages = results.get("messages", [])
            parsed = []
            for msg in messages:
                data = await self._get_message(msg["id"])
                if data:
                    parsed.append(data)
            return parsed
        except Exception as e:
            logger.error("Error searching Gmail: %s", e)
            return []


gmail_client = GmailClient()
