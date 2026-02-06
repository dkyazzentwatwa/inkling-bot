"""
Project Inkling - WiFi Utilities

Functions for managing WiFi connectivity and BTBerryWifi BLE configuration.
"""

import subprocess
import re
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class WiFiNetwork:
    """Represents a WiFi network."""
    ssid: str
    signal_strength: int  # 0-100
    security: str  # "WPA2", "WPA3", "Open", etc.
    connected: bool = False


@dataclass
class WiFiStatus:
    """Current WiFi connection status."""
    connected: bool
    ssid: Optional[str] = None
    signal_strength: int = 0  # 0-100
    ip_address: Optional[str] = None
    frequency: Optional[str] = None


def get_current_wifi() -> WiFiStatus:
    """
    Get current WiFi connection status.

    Returns:
        WiFiStatus with connection information
    """
    try:
        # Try iwgetid first (simpler, more reliable)
        result = subprocess.run(
            ["iwgetid", "-r"],
            capture_output=True,
            text=True,
            timeout=2
        )

        if result.returncode == 0 and result.stdout.strip():
            ssid = result.stdout.strip()

            # Get signal strength
            signal = _get_signal_strength()

            # Get IP address
            ip = _get_ip_address()

            # Get frequency
            freq = _get_frequency()

            return WiFiStatus(
                connected=True,
                ssid=ssid,
                signal_strength=signal,
                ip_address=ip,
                frequency=freq
            )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fall back to checking ip link
    try:
        result = subprocess.run(
            ["ip", "link", "show", "wlan0"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if "state UP" in result.stdout:
            # Interface is up but not connected or can't determine SSID
            return WiFiStatus(connected=False)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return WiFiStatus(connected=False)


def _get_signal_strength() -> int:
    """
    Get WiFi signal strength as percentage (0-100).

    Returns:
        Signal strength percentage
    """
    try:
        result = subprocess.run(
            ["iwconfig", "wlan0"],
            capture_output=True,
            text=True,
            timeout=2
        )

        # Look for "Link Quality=XX/70" or "Signal level=-XX dBm"
        quality_match = re.search(r"Link Quality=(\d+)/(\d+)", result.stdout)
        if quality_match:
            current = int(quality_match.group(1))
            maximum = int(quality_match.group(2))
            return int((current / maximum) * 100)

        # Try dBm signal level (-100 to -30 typical range)
        signal_match = re.search(r"Signal level[=:](-?\d+)", result.stdout)
        if signal_match:
            dbm = int(signal_match.group(1))
            # Convert dBm to percentage (rough approximation)
            # -30 dBm = excellent (100%), -90 dBm = unusable (0%)
            return max(0, min(100, int((dbm + 90) * (100 / 60))))

    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass

    return 0


def _get_ip_address() -> Optional[str]:
    """Get current IP address for wlan0."""
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", "wlan0"],
            capture_output=True,
            text=True,
            timeout=2
        )

        # Look for "inet 192.168.x.x/24"
        match = re.search(r"inet\s+([0-9.]+)", result.stdout)
        if match:
            return match.group(1)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


def _get_frequency() -> Optional[str]:
    """Get WiFi frequency (2.4GHz or 5GHz)."""
    try:
        result = subprocess.run(
            ["iwconfig", "wlan0"],
            capture_output=True,
            text=True,
            timeout=2
        )

        # Look for "Frequency:2.4" or "Frequency:5.x"
        match = re.search(r"Frequency:([\d.]+)\s*GHz", result.stdout)
        if match:
            freq = float(match.group(1))
            if freq < 3:
                return "2.4GHz"
            else:
                return "5GHz"
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass

    return None


def get_saved_networks() -> List[str]:
    """
    Get list of saved WiFi networks from wpa_supplicant.conf.

    Returns:
        List of SSIDs
    """
    networks = []

    try:
        with open("/etc/wpa_supplicant/wpa_supplicant.conf", "r") as f:
            content = f.read()

            # Find all network blocks and extract SSIDs
            network_blocks = re.finditer(
                r'network\s*=\s*\{[^}]*ssid\s*=\s*"([^"]+)"[^}]*\}',
                content,
                re.MULTILINE | re.DOTALL
            )

            for match in network_blocks:
                ssid = match.group(1)
                if ssid not in networks:
                    networks.append(ssid)
    except (FileNotFoundError, PermissionError):
        pass

    return networks


def scan_networks() -> List[WiFiNetwork]:
    """
    Scan for nearby WiFi networks.

    Returns:
        List of WiFiNetwork objects
    """
    networks = []

    try:
        # Use iwlist to scan
        result = subprocess.run(
            ["sudo", "iwlist", "wlan0", "scan"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return networks

        # Parse iwlist output
        current_network = None

        for line in result.stdout.split("\n"):
            line = line.strip()

            # New cell (network)
            if line.startswith("Cell"):
                if current_network:
                    networks.append(current_network)
                current_network = WiFiNetwork(ssid="", signal_strength=0, security="Unknown")

            # SSID
            elif 'ESSID:"' in line:
                match = re.search(r'ESSID:"([^"]*)"', line)
                if match and current_network:
                    current_network.ssid = match.group(1)

            # Signal quality
            elif "Quality=" in line:
                match = re.search(r"Quality=(\d+)/(\d+)", line)
                if match and current_network:
                    current = int(match.group(1))
                    maximum = int(match.group(2))
                    current_network.signal_strength = int((current / maximum) * 100)

            # Security
            elif "WPA2" in line:
                if current_network:
                    current_network.security = "WPA2"
            elif "WPA3" in line:
                if current_network:
                    current_network.security = "WPA3"
            elif "Encryption key:off" in line:
                if current_network:
                    current_network.security = "Open"

        # Add last network
        if current_network and current_network.ssid:
            networks.append(current_network)

        # Sort by signal strength (strongest first)
        networks.sort(key=lambda n: n.signal_strength, reverse=True)

        # Remove duplicates (keep strongest)
        seen_ssids = set()
        unique_networks = []
        for net in networks:
            if net.ssid not in seen_ssids:
                seen_ssids.add(net.ssid)
                unique_networks.append(net)

        return unique_networks

    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        return networks


def is_btcfg_running() -> bool:
    """
    Check if BTBerryWifi BLE configuration service is running.

    Returns:
        True if service is active
    """
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "btwifiset"],
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.returncode == 0 and result.stdout.strip() == "active"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def is_btcfg_installed() -> bool:
    """
    Check if BTBerryWifi is installed.

    Returns:
        True if service exists
    """
    try:
        result = subprocess.run(
            ["systemctl", "status", "btwifiset"],
            capture_output=True,
            text=True,
            timeout=2
        )
        # Service exists if status doesn't return "not found" error
        return "could not be found" not in result.stderr.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def start_btcfg() -> Tuple[bool, str]:
    """
    Start BTBerryWifi BLE configuration service for 15 minutes.

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Check if installed
    if not is_btcfg_installed():
        return (
            False,
            "BTBerryWifi not installed. Run: curl -L https://raw.githubusercontent.com/nksan/Rpi-SetWiFi-viaBluetooth/main/btwifisetInstall.sh | bash"
        )

    # Check if already running
    if is_btcfg_running():
        return (True, "BTBerryWifi BLE service is already running")

    # Start service
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "start", "btwifiset"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            return (
                True,
                "BTBerryWifi BLE service started. Service will run for 15 minutes.\n\n"
                "📱 Open BTBerryWifi app on your phone:\n"
                "   iOS: https://apps.apple.com/app/btberrywifi/id6479825660\n"
                "   Android: https://play.google.com/store/apps/details?id=com.bluetoothwifisetup\n\n"
                "1. Scan for devices\n"
                "2. Connect to your Inkling\n"
                "3. Select WiFi network and enter password"
            )
        else:
            return (False, f"Failed to start service: {result.stderr}")

    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError) as e:
        return (False, f"Error starting service: {str(e)}")


def get_wifi_bars(signal_strength: int) -> str:
    """
    Convert signal strength percentage to Unicode bar indicator.

    Args:
        signal_strength: 0-100 percentage

    Returns:
        Bar indicator string (e.g., "●●●○" or "▂▄▆█")
    """
    if signal_strength >= 80:
        return "▂▄▆█"  # Excellent
    elif signal_strength >= 60:
        return "▂▄▆"   # Good
    elif signal_strength >= 40:
        return "▂▄"    # Fair
    elif signal_strength >= 20:
        return "▂"     # Poor
    else:
        return "○"     # Very poor
