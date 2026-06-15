from __future__ import annotations

import asyncio
import logging
import subprocess
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

APPLE_SCRIPT_ACTIVE = """
tell application "System Events"
    set frontApp to name of first application process whose frontmost is true
end tell
return frontApp
"""

APPLE_SCRIPT_TITLE = """
tell application "System Events"
    set frontApp to name of first application process whose frontmost is true
    set appPath to path of first application process whose frontmost is true
end tell

tell application frontApp
    if frontApp is "Google Chrome" or frontApp is "Safari" or frontApp is "Arc" then
        return name of front window & " | " & URL of active tab of front window
    else if frontApp is "Code" or frontApp is "Terminal" or frontApp is "iTerm2" then
        return name of front window
    else
        return ""
    end if
end tell
"""


class DeviceTracker:
    def __init__(self) -> None:
        self.last_activity: dict[str, Any] = {}
        self._running = False

    async def get_active_app(self) -> str:
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    ["osascript", "-e", APPLE_SCRIPT_ACTIVE],
                    capture_output=True,
                    text=True,
                    timeout=5,
                ),
            )
            return result.stdout.strip()
        except Exception as e:
            logger.error("Error getting active app: %s", e)
            return ""

    async def get_active_window_title(self) -> str:
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    ["osascript", "-e", APPLE_SCRIPT_TITLE],
                    capture_output=True,
                    text=True,
                    timeout=5,
                ),
            )
            return result.stdout.strip()
        except Exception as e:
            logger.error("Error getting window title: %s", e)
            return ""

    async def track(self) -> dict[str, Any]:
        app = await self.get_active_app()
        title = await self.get_active_window_title()
        now = datetime.now()

        activity = {
            "app": app,
            "title": title,
            "timestamp": now.isoformat(),
        }

        if (
            self.last_activity.get("app") != app
            or self.last_activity.get("title") != title
        ):
            logger.debug("Activity change: %s - %s", app, title)
            self.last_activity = activity
            return activity

        self.last_activity = activity
        return {}


device_tracker = DeviceTracker()
