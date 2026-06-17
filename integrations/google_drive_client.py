from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config.settings import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]


class GoogleDriveClient:
    def __init__(self) -> None:
        self.drive_service = None
        self.sheets_service = None
        self.docs_service = None
        self.creds = None
        self._initialized = False

    async def initialize(self) -> bool:
        if not settings.gmail_credentials_file:
            logger.warning("GMAIL_CREDENTIALS_FILE not set. Google Drive integration disabled.")
            return False

        creds_file = settings.gmail_credentials_file
        if not os.path.exists(creds_file):
            logger.warning("Credentials file not found: %s", creds_file)
            return False

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

        self.drive_service = build("drive", "v3", credentials=self.creds)
        self.sheets_service = build("sheets", "v4", credentials=self.creds)
        self.docs_service = build("docs", "v1", credentials=self.creds)
        self._initialized = True
        logger.info("Google Drive client initialized.")
        return True

    @staticmethod
    def extract_id_from_url(url: str) -> dict[str, str | None]:
        sheet_match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
        if sheet_match:
            return {"type": "sheet", "id": sheet_match.group(1)}
        doc_match = re.search(r"/document/d/([a-zA-Z0-9_-]+)", url)
        if doc_match:
            return {"type": "doc", "id": doc_match.group(1)}
        drive_match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
        if drive_match:
            return {"type": "file", "id": drive_match.group(1)}
        return {"type": None, "id": None}

    async def read_sheet(
        self, spreadsheet_id: str, range_name: str = "Sheet1"
    ) -> list[list[Any]]:
        if not self._initialized:
            return []
        try:
            result = await asyncio.to_thread(
                self.sheets_service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute
            )
            return result.get("values", [])
        except Exception as e:
            logger.error("Error reading sheet %s: %s", spreadsheet_id, e)
            return []

    async def read_doc(self, document_id: str) -> str:
        if not self._initialized:
            return ""
        try:
            doc = await asyncio.to_thread(
                self.docs_service.documents().get(documentId=document_id).execute
            )
            content = doc.get("body", {}).get("content", [])
            text = ""
            for element in content:
                paragraph = element.get("paragraph", {})
                for run in paragraph.get("elements", []):
                    text_run = run.get("textRun", {})
                    if "content" in text_run:
                        text += text_run["content"]
            return text.strip()
        except Exception as e:
            logger.error("Error reading doc %s: %s", document_id, e)
            return ""

    async def list_recent(self, page_size: int = 5) -> list[dict[str, Any]]:
        if not self._initialized:
            return []
        try:
            result = await asyncio.to_thread(
                self.drive_service.files()
                .list(
                    pageSize=page_size,
                    fields="files(id, name, mimeType, modifiedTime)",
                )
                .execute
            )
            return result.get("files", [])
        except Exception as e:
            logger.error("Error listing Drive files: %s", e)
            return []

    async def get_file_name(self, file_id: str) -> str | None:
        if not self._initialized:
            return None
        try:
            file = await asyncio.to_thread(
                self.drive_service.files().get(fileId=file_id, fields="name").execute
            )
            return file.get("name")
        except Exception as e:
            logger.error("Error getting file name %s: %s", file_id, e)
            return None


google_drive_client = GoogleDriveClient()
