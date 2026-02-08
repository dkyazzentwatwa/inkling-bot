"""System and network commands."""
from typing import Dict, Any

from . import CommandHandler


class SystemCommands(CommandHandler):
    """Handlers for system commands (/system, /config, /bash, /wifi, /btcfg, /wifiscan)."""

    def system(self) -> Dict[str, Any]:
        """Show system stats."""
        from core import system_stats

        stats = system_stats.get_all_stats()
        response = "SYSTEM STATUS\n\n"
        response += f"CPU:    {stats['cpu']}%\n"
        response += f"Memory: {stats['memory']}%\n"

        temp = stats['temperature']
        if temp > 0:
            response += f"Temp:   {temp}°C\n"
        else:
            response += f"Temp:   --°C\n"

        response += f"Uptime: {stats['uptime']}"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def config(self) -> Dict[str, Any]:
        """Show AI configuration."""
        response = "AI CONFIGURATION\n\n"
        response += f"Providers: {', '.join(self.brain.available_providers)}\n"

        if self.brain.providers:
            primary = self.brain.providers[0]
            response += f"Primary:   {primary.name}\n"
            response += f"Model:     {primary.model}\n"
            response += f"Max tokens: {primary.max_tokens}\n"

        stats = self.brain.get_stats()
        response += f"\nBudget: {stats['tokens_used_today']}/{stats['daily_limit']} tokens today"

        return {
            "response": response,
            "face": self._get_face_str(),
            "status": self.personality.get_status_line(),
        }

    def bash(self, args: str) -> Dict[str, Any]:
        """Disable bash execution in web UI."""
        return {
            "response": "The /bash command is disabled in the web UI.",
            "error": True,
        }

    def wifi(self) -> Dict[str, Any]:
        """Show WiFi status and saved networks."""
        from core.wifi_utils import get_current_wifi, get_saved_networks, is_btcfg_running, get_wifi_bars

        status = get_current_wifi()
        output = ["**WiFi Status**\n"]

        # Current connection
        if status.connected and status.ssid:
            bars = get_wifi_bars(status.signal_strength)
            output.append(f"✓ Connected to: **{status.ssid}**")
            output.append(f"  Signal: {bars} {status.signal_strength}%")
            if status.ip_address:
                output.append(f"  IP: {status.ip_address}")
            if status.frequency:
                output.append(f"  Band: {status.frequency}")
        else:
            output.append("✗ Not connected")

        output.append("")

        # BLE service status
        if is_btcfg_running():
            output.append("🔵 **BLE Configuration: Running** (15 min window)")
            output.append("   Use BTBerryWifi app to configure WiFi")
        else:
            output.append("🔵 BLE Configuration: Stopped")
            output.append("   Use /btcfg to start configuration service")

        output.append("")

        # Saved networks
        saved = get_saved_networks()
        if saved:
            output.append(f"**Saved Networks ({len(saved)}):**")
            for ssid in saved:
                icon = "●" if status.connected and status.ssid == ssid else "○"
                output.append(f"  {icon} {ssid}")
        else:
            output.append("*No saved networks*")

        output.append("")
        output.append("*Tip: Use /wifiscan to find nearby networks*")

        return {
            "response": "\n".join(output),
            "face": self.personality.face,
        }

    def btcfg(self) -> Dict[str, Any]:
        """Start BTBerryWifi BLE configuration service."""
        from core.wifi_utils import start_btcfg

        success, message = start_btcfg()

        return {
            "response": message,
            "face": self.personality.face,
            "error": not success,
        }

    def wifiscan(self) -> Dict[str, Any]:
        """Scan for nearby WiFi networks."""
        from core.wifi_utils import scan_networks, get_current_wifi

        networks = scan_networks()
        current = get_current_wifi()

        if not networks:
            return {
                "response": "No networks found or permission denied.\n\n*Tip: Scanning requires sudo access*",
                "face": self.personality.face,
                "error": True,
            }

        output = [f"**Nearby Networks ({len(networks)})**\n"]

        for net in networks:
            # Visual signal indicator
            if net.signal_strength >= 80:
                signal_icon = "▂▄▆█"
            elif net.signal_strength >= 60:
                signal_icon = "▂▄▆"
            elif net.signal_strength >= 40:
                signal_icon = "▂▄"
            elif net.signal_strength >= 20:
                signal_icon = "▂"
            else:
                signal_icon = "○"

            # Connection indicator
            connected = current.connected and current.ssid == net.ssid
            conn_icon = "●" if connected else " "

            # Security badge
            if net.security == "Open":
                security_badge = "[OPEN]"
            elif net.security == "WPA3":
                security_badge = "[WPA3]"
            elif net.security == "WPA2":
                security_badge = "[WPA2]"
            else:
                security_badge = f"[{net.security}]"

            output.append(f"{conn_icon} {signal_icon} {net.signal_strength:3}% {security_badge} {net.ssid}")

        output.append("")
        output.append("*Use /btcfg to start BLE configuration service*")

        return {
            "response": "\n".join(output),
            "face": self.personality.face,
        }
