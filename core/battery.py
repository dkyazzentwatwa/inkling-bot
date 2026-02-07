"""
Project Inkling - PiSugar Battery Management

Handles communication with PiSugar 2/3 battery power management boards.
Uses the pisugar-server API (default port 8000).
"""

from typing import Dict
import socket
import logging

logger = logging.getLogger(__name__)


class PiSugarClient:
    """Client for interacting with pisugar-server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000, enabled: bool = True):
        self.host = host
        self.port = port
        self.enabled = enabled
        self.timeout = 2.0

    def _send_command(self, command: str) -> str:
        """Send a text command to the pisugar-server."""
        if not self.enabled:
            return ""

        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.sendall(f"{command}\n".encode())
                response = sock.recv(1024).decode().strip()
                return response
        except (socket.timeout, ConnectionRefusedError, OSError):
            # Silently fail if server isn't running (likely not on a PiSugar device)
            return ""

    def get_battery_percentage(self) -> int:
        """Get battery percentage (0-100)."""
        response = self._send_command("get battery")
        if response.startswith("battery:"):
            try:
                # Format: "battery: 85.5"
                return int(float(response.split(":", maxsplit=1)[1].strip()))
            except (ValueError, IndexError):
                pass
        return -1

    def is_charging(self) -> bool:
        """Check if the battery is currently charging."""
        response = self._send_command("get charging")
        # Format: "charging: true" or "charging: false"
        return "true" in response.lower()

    def get_info(self) -> Dict[str, object]:
        """Get combined battery information."""
        level = self.get_battery_percentage()
        if level == -1:
            return {}

        return {
            "percentage": level,
            "charging": self.is_charging(),
        }


# Singleton instance
_client = PiSugarClient()


def get_battery_info() -> Dict[str, object]:
    """Public helper to get battery info."""
    return _client.get_info()
