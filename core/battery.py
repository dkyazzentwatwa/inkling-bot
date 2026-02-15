"""
Project Inkling - PiSugar Battery Management

Handles communication with PiSugar 2/3 battery power management boards.
Uses the pisugar-server TCP API (port 8423).
"""

from typing import Dict
import socket
import logging

logger = logging.getLogger(__name__)


class PiSugarClient:
    """Client for interacting with pisugar-server via TCP API.

    The pisugar-server exposes a TCP command interface on port 8423.
    Commands are sent as text lines and responses are text-based.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8423,  # TCP command API port (not 8000!)
        enabled: bool = True
    ):
        self.host = host
        self.port = port
        self.enabled = enabled
        self.timeout = 2.0

    def _send_command(self, command: str) -> str:
        """Send a text command to the pisugar-server TCP API."""
        if not self.enabled:
            return ""

        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.sendall(f"{command}\n".encode())
                response = sock.recv(1024).decode().strip()
                return response
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            # Silently fail if server isn't running
            logger.debug(f"PiSugar connection failed: {e}")
            return ""

    def get_battery_percentage(self) -> int:
        """Get battery percentage (0-100)."""
        response = self._send_command("get battery")
        # Response format: "battery: 85.5" or just the value
        if not response:
            return -1

        try:
            if ":" in response:
                # Format: "battery: 85.5"
                value = response.split(":", maxsplit=1)[1].strip()
            else:
                # Format: "85.5"
                value = response.strip()
            return int(float(value))
        except (ValueError, IndexError):
            return -1

    def is_charging(self) -> bool:
        """Check if the battery is currently charging."""
        response = self._send_command("get battery_charging")
        # Format: "battery_charging: true" or "true"
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
