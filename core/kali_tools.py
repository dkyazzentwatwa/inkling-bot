"""
Project Inkling - Kali Linux Tool Integration

Integrates Kali Linux penetration testing tools for authorized security testing.
Supports nmap, metasploit, hydra, sqlmap, aircrack-ng, and more.

⚠️  LEGAL WARNING: Only use on systems you own or have written authorization to test!
"""

import asyncio
import json
import logging
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import shutil

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Network scan results."""
    target: str
    hosts_up: int
    total_hosts: int
    open_ports: List[Dict[str, str]]
    services: List[Dict[str, str]]
    vulnerabilities: List[Dict[str, str]]
    scan_time: float
    timestamp: str

    @property
    def summary(self) -> str:
        """Get scan summary."""
        return (
            f"{self.hosts_up}/{self.total_hosts} hosts up, "
            f"{len(self.open_ports)} ports open, "
            f"{len(self.vulnerabilities)} vulns"
        )


@dataclass
class ExploitResult:
    """Exploit attempt results."""
    module: str
    target: str
    success: bool
    session_id: Optional[int]
    output: str
    timestamp: str


@dataclass
class ActiveSession:
    """Active shell session."""
    session_id: int
    target: str
    session_type: str  # meterpreter, shell, etc.
    user: str
    platform: str
    created_at: str
    last_active: str


class KaliToolManager:
    """
    Manages Kali Linux security tools for penetration testing.

    ⚠️  ETHICAL USE ONLY - Requires authorization for all targets!
    """

    def __init__(self, data_dir: str = "~/.inkling/pentest"):
        """Initialize Kali tool manager."""
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Check for required tools
        self._check_tools()

    def _check_tools(self) -> Dict[str, bool]:
        """Check which Kali tools are installed."""
        tools = {
            "nmap": shutil.which("nmap"),
            "msfconsole": shutil.which("msfconsole"),
            "hydra": shutil.which("hydra"),
            "sqlmap": shutil.which("sqlmap"),
            "nikto": shutil.which("nikto"),
            "aircrack-ng": shutil.which("aircrack-ng"),
        }

        installed = {k: bool(v) for k, v in tools.items()}
        logger.info(f"Available tools: {installed}")
        return installed

    # ========================================
    # Network Scanning (Nmap)
    # ========================================

    async def nmap_scan(
        self,
        target: str,
        scan_type: str = "quick",
        ports: Optional[str] = None,
        timing: int = 4
    ) -> Optional[ScanResult]:
        """
        Run nmap network scan.

        Args:
            target: Target IP, hostname, or CIDR range
            scan_type: "quick", "full", "stealth", "version", "vuln"
            ports: Port range (e.g., "1-1000", "80,443")
            timing: Timing template 0-5 (0=paranoid, 5=insane)

        Returns:
            ScanResult or None if failed
        """
        if not shutil.which("nmap"):
            logger.error("nmap not installed")
            return None

        # Build nmap command
        cmd = ["nmap", f"-T{timing}"]

        if scan_type == "quick":
            cmd.extend(["-F"])  # Fast scan (100 common ports)
        elif scan_type == "full":
            cmd.extend(["-p-"])  # All 65535 ports
        elif scan_type == "stealth":
            cmd.extend(["-sS"])  # SYN stealth scan
        elif scan_type == "version":
            cmd.extend(["-sV"])  # Version detection
        elif scan_type == "vuln":
            cmd.extend(["-sV", "--script=vuln"])  # Vulnerability scripts

        if ports:
            cmd.extend(["-p", ports])

        # Output XML for parsing
        xml_file = self.data_dir / f"nmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        cmd.extend(["-oX", str(xml_file), target])

        logger.info(f"Running: {' '.join(cmd)}")

        try:
            start_time = datetime.now()

            # Run nmap
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=600  # 10 minute timeout
            )

            scan_time = (datetime.now() - start_time).total_seconds()

            if process.returncode != 0:
                logger.error(f"nmap failed: {stderr.decode()}")
                return None

            # Parse XML results
            result = self._parse_nmap_xml(xml_file)
            if result:
                result.scan_time = scan_time

            return result

        except asyncio.TimeoutError:
            logger.error("nmap scan timed out")
            return None
        except Exception as e:
            logger.error(f"nmap scan error: {e}")
            return None

    def _parse_nmap_xml(self, xml_file: Path) -> Optional[ScanResult]:
        """Parse nmap XML output."""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            hosts_up = 0
            total_hosts = 0
            open_ports = []
            services = []
            vulnerabilities = []

            # Parse host information
            for host in root.findall(".//host"):
                total_hosts += 1

                status = host.find("status")
                if status is not None and status.get("state") == "up":
                    hosts_up += 1

                    # Get IP address
                    address = host.find("address")
                    ip = address.get("addr") if address is not None else "unknown"

                    # Parse ports
                    for port in host.findall(".//port"):
                        port_id = port.get("portid")
                        protocol = port.get("protocol")

                        state = port.find("state")
                        if state is not None and state.get("state") == "open":
                            service = port.find("service")
                            service_name = service.get("name") if service is not None else "unknown"
                            service_version = service.get("version", "") if service is not None else ""

                            port_info = {
                                "host": ip,
                                "port": port_id,
                                "protocol": protocol,
                                "service": service_name,
                                "version": service_version
                            }

                            open_ports.append(port_info)

                            if service_version:
                                services.append({
                                    "host": ip,
                                    "service": f"{service_name} {service_version}",
                                    "port": f"{port_id}/{protocol}"
                                })

                    # Parse vulnerability script results
                    for script in host.findall(".//script[@id='vuln']"):
                        output = script.get("output", "")
                        if "VULNERABLE" in output:
                            vulnerabilities.append({
                                "host": ip,
                                "description": output[:200],  # Truncate
                                "severity": "unknown"
                            })

            target = root.find(".//task/arg[@name='target']")
            target_str = target.get("value") if target is not None else "unknown"

            return ScanResult(
                target=target_str,
                hosts_up=hosts_up,
                total_hosts=total_hosts,
                open_ports=open_ports,
                services=services,
                vulnerabilities=vulnerabilities,
                scan_time=0.0,  # Set by caller
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Failed to parse nmap XML: {e}")
            return None

    # ========================================
    # Password Auditing (Hydra)
    # ========================================

    async def hydra_bruteforce(
        self,
        target: str,
        service: str,
        username: Optional[str] = None,
        userlist: Optional[str] = None,
        password: Optional[str] = None,
        passlist: Optional[str] = None,
        port: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Run hydra password brute force.

        ⚠️  Use responsibly! Rate-limited and logged.

        Args:
            target: Target host
            service: Service type (ssh, ftp, http-post-form, etc.)
            username: Single username to test
            userlist: Path to username list
            password: Single password to test
            passlist: Path to password list
            port: Port number (optional)

        Returns:
            Dict with results
        """
        if not shutil.which("hydra"):
            return {"error": "hydra not installed"}

        if not ((username or userlist) and (password or passlist)):
            return {"error": "Must provide username and password options"}

        # Build hydra command
        cmd = ["hydra"]

        if username:
            cmd.extend(["-l", username])
        elif userlist:
            cmd.extend(["-L", userlist])

        if password:
            cmd.extend(["-p", password])
        elif passlist:
            cmd.extend(["-P", passlist])

        if port:
            cmd.extend(["-s", str(port)])

        # Rate limiting
        cmd.extend(["-t", "4"])  # 4 threads max

        cmd.extend([target, service])

        logger.warning(f"Hydra brute force: {target} {service}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300  # 5 minute timeout
            )

            output = stdout.decode()

            # Parse results
            found = []
            for line in output.split("\n"):
                if "[" in line and "login:" in line:
                    # Extract credentials from hydra output
                    match = re.search(r"login:\s*(\S+)\s+password:\s*(\S+)", line)
                    if match:
                        found.append({
                            "username": match.group(1),
                            "password": match.group(2)
                        })

            return {
                "success": len(found) > 0,
                "found": found,
                "attempts": output.count("attempt"),
                "output": output[:500]  # Truncate
            }

        except asyncio.TimeoutError:
            return {"error": "Hydra timed out"}
        except Exception as e:
            logger.error(f"Hydra error: {e}")
            return {"error": str(e)}

    # ========================================
    # Web Scanning (Nikto)
    # ========================================

    async def nikto_scan(
        self,
        target: str,
        port: int = 80,
        ssl: bool = False
    ) -> Dict[str, any]:
        """
        Run Nikto web vulnerability scanner.

        Args:
            target: Target hostname/IP
            port: Port number
            ssl: Use HTTPS

        Returns:
            Dict with scan results
        """
        if not shutil.which("nikto"):
            return {"error": "nikto not installed"}

        protocol = "https" if ssl else "http"
        url = f"{protocol}://{target}:{port}"

        cmd = ["nikto", "-h", url, "-output", "-", "-Format", "txt"]

        logger.info(f"Nikto scan: {url}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=600  # 10 minute timeout
            )

            output = stdout.decode()

            # Parse findings
            findings = []
            for line in output.split("\n"):
                if "+ " in line and ("OSVDB" in line or "CVE" in line):
                    findings.append(line.strip())

            return {
                "target": url,
                "findings": findings[:50],  # Limit to 50
                "total_findings": len(findings),
                "output": output[:1000]
            }

        except asyncio.TimeoutError:
            return {"error": "Nikto scan timed out"}
        except Exception as e:
            logger.error(f"Nikto error: {e}")
            return {"error": str(e)}

    # ========================================
    # Utility Functions
    # ========================================

    def get_local_ip(self) -> Optional[str]:
        """Get local IP address."""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None

    def validate_target(self, target: str, allowed_ranges: List[str]) -> bool:
        """
        Validate target is in allowed scope.

        Args:
            target: Target IP or hostname
            allowed_ranges: List of allowed CIDR ranges

        Returns:
            True if target is in scope
        """
        import ipaddress

        try:
            target_ip = ipaddress.ip_address(target)

            for allowed_range in allowed_ranges:
                network = ipaddress.ip_network(allowed_range, strict=False)
                if target_ip in network:
                    return True

            return False

        except ValueError:
            # Not an IP address, might be hostname
            logger.warning(f"Cannot validate hostname scope: {target}")
            return False

    def format_scan_summary(self, result: ScanResult) -> str:
        """Format scan result summary for display."""
        summary = f"**SCAN COMPLETE**\n\n"
        summary += f"Target: {result.target}\n"
        summary += f"Hosts: {result.hosts_up}/{result.total_hosts} up\n"
        summary += f"Ports: {len(result.open_ports)} open\n"
        summary += f"Services: {len(result.services)}\n"

        if result.vulnerabilities:
            summary += f"⚠️  Vulnerabilities: {len(result.vulnerabilities)}\n"

        summary += f"\nTime: {result.scan_time:.1f}s"

        return summary
