"""
Shared command bridge for BLE transport.

Routes BLE input lines to the active Inkling mode and returns plain text output.
"""

from __future__ import annotations

import asyncio
import io
import re
import threading
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Optional, Tuple

from core.shell_utils import run_bash_command


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


class InklingModeBridge:
    """Bridge BLE input to the currently running Inkling mode."""

    def __init__(
        self,
        mode: Any,
        loop: Optional[asyncio.AbstractEventLoop],
        allow_bash: bool = True,
        bash_timeout_seconds: int = 8,
        max_output_bytes: int = 8192,
    ) -> None:
        self._mode = mode
        self._loop = loop
        self._allow_bash = allow_bash
        self._bash_timeout_seconds = bash_timeout_seconds
        self._max_output_bytes = max_output_bytes
        self._lock = threading.Lock()
        self._loop_thread_id: Optional[int] = None
        if loop and loop.is_running():
            self._loop_thread_id = threading.get_ident()

    def handle_line(self, line: str) -> str:
        """Handle a single line of BLE input and return formatted output."""
        with self._lock:
            return self._handle_line_locked(line)

    def _handle_line_locked(self, line: str) -> str:
        line = (line or "").strip()
        if not line:
            return self._format_ok("")

        if line.startswith("/bash"):
            return self._handle_bash(line)

        if self._is_web_mode():
            return self._handle_web(line)

        return self._handle_ssh(line)

    def _handle_bash(self, line: str) -> str:
        if not self._allow_bash:
            return self._format_err(1, "bash disabled")

        parts = line.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            return self._format_err(1, "Usage: /bash <command>")

        cmd = parts[1].strip()
        try:
            exit_code, output = run_bash_command(
                cmd,
                timeout_seconds=self._bash_timeout_seconds,
                max_output_bytes=self._max_output_bytes,
            )
        except Exception as exc:
            return self._format_err(1, f"Error: {exc}")

        if exit_code == 0:
            return self._format_ok(output)
        return self._format_err(exit_code, output)

    def _handle_web(self, line: str) -> str:
        if line.startswith("/"):
            result = self._mode._handle_command_sync(line)
        else:
            result = self._mode._handle_chat_sync(line)

        response = result.get("response", "") if isinstance(result, dict) else str(result)
        error = bool(result.get("error")) if isinstance(result, dict) else False

        if error:
            return self._format_err(1, response)
        return self._format_ok(response)

    def _handle_ssh(self, line: str) -> str:
        if not self._loop or not self._loop.is_running():
            return self._format_err(1, "SSH mode loop is not running")

        if self._loop_thread_id == threading.get_ident():
            return self._format_err(1, "BLE bridge called from event loop thread")

        async def run_and_capture(coro) -> Tuple[bool, str]:
            buffer = io.StringIO()
            with redirect_stdout(buffer), redirect_stderr(buffer):
                ok = await coro
            return bool(ok), buffer.getvalue()

        if line.startswith("/"):
            coro = self._mode._handle_command(line)
        else:
            coro = self._mode._handle_message(line)

        future = asyncio.run_coroutine_threadsafe(run_and_capture(coro), self._loop)
        try:
            ok, output = future.result()
        except Exception as exc:
            return self._format_err(1, f"Error: {exc}")
        output = self._strip_ansi(output)

        if ok:
            return self._format_ok(output)
        return self._format_err(1, output or "Error")

    def _is_web_mode(self) -> bool:
        return hasattr(self._mode, "_handle_command_sync") and hasattr(self._mode, "_handle_chat_sync")

    def _strip_ansi(self, text: str) -> str:
        return ANSI_ESCAPE_RE.sub("", text or "")

    def _format_ok(self, output: str) -> str:
        payload = (output or "").rstrip("\n")
        if payload:
            return f"OK 0\n{payload}\n<END>\n"
        return "OK 0\n<END>\n"

    def _format_err(self, code: int, output: str) -> str:
        payload = (output or "").rstrip("\n")
        if payload:
            return f"ERR {code}\n{payload}\n<END>\n"
        return f"ERR {code}\n<END>\n"
