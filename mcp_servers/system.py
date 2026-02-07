#!/usr/bin/env python3
"""
Inkling System Tools MCP Server

Provides lightweight Linux utility tools via MCP:
- curl: Make HTTP requests
- df: Check disk space usage
- free: Check memory usage
- uptime: System uptime and load
- ps: List running processes
- ping: Test network connectivity

Usage:
    python mcp_servers/system.py

Configuration in config.yml:
    mcp:
      enabled: true
      servers:
        system:
          command: "python"
          args: ["mcp_servers/system.py"]
"""

import sys
import json
import os
import socket
import subprocess
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

try:
    import psutil
    import requests
except ImportError:
    print("ERROR: Missing required packages. Install with:", file=sys.stderr)
    print("  pip install psutil requests", file=sys.stderr)
    sys.exit(1)


class SystemMCPServer:
    """MCP server for system utilities."""

    def __init__(self):
        self.request_id = 0

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an MCP request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "initialize":
                return self._initialize(request_id)
            elif method == "tools/list":
                return self._list_tools(request_id)
            elif method == "tools/call":
                return self._call_tool(request_id, params)
            else:
                return self._error(request_id, f"Unknown method: {method}")

        except Exception as e:
            return self._error(request_id, str(e))

    def _initialize(self, request_id: int) -> Dict[str, Any]:
        """Handle initialization request."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "1.0",
                "serverInfo": {
                    "name": "inkling-system",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        }

    def _list_tools(self, request_id: int) -> Dict[str, Any]:
        """List available tools."""
        tools = [
            {
                "name": "curl",
                "description": "Make an HTTP request and return the response. Supports GET and POST methods with custom headers.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to fetch (http:// or https:// only)"
                        },
                        "method": {
                            "type": "string",
                            "enum": ["GET", "POST"],
                            "description": "HTTP method (default: GET)"
                        },
                        "headers": {
                            "type": "object",
                            "description": "HTTP headers as key-value pairs"
                        },
                        "body": {
                            "type": "string",
                            "description": "Request body for POST requests"
                        }
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "df",
                "description": "Show disk space usage for filesystem. Returns total, used, available space and usage percentage.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to check (default: root filesystem)"
                        }
                    }
                }
            },
            {
                "name": "free",
                "description": "Show memory (RAM) and swap usage. Returns total, used, and available memory in MB.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "uptime",
                "description": "Show system uptime and load averages. Returns uptime string and 1/5/15 minute load averages.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "ps",
                "description": "List running processes with CPU and memory usage. Returns top processes by CPU usage.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "Filter processes by name (substring match)"
                        },
                        "limit": {
                            "type": "number",
                            "description": "Maximum number of processes to return (default: 10)"
                        }
                    }
                }
            },
            {
                "name": "ping",
                "description": "Test network connectivity to a host. Returns whether host is reachable and latency in milliseconds.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "host": {
                            "type": "string",
                            "description": "Hostname or IP address to ping"
                        }
                    },
                    "required": ["host"]
                }
            }
        ]

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools
            }
        }

    def _call_tool(self, request_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            if tool_name == "curl":
                result = self._curl(arguments)
            elif tool_name == "df":
                result = self._df(arguments)
            elif tool_name == "free":
                result = self._free(arguments)
            elif tool_name == "uptime":
                result = self._uptime(arguments)
            elif tool_name == "ps":
                result = self._ps(arguments)
            elif tool_name == "ping":
                result = self._ping(arguments)
            else:
                return self._error(request_id, f"Unknown tool: {tool_name}")

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }

        except Exception as e:
            return self._error(request_id, f"Tool execution failed: {str(e)}")

    @staticmethod
    def _is_private_ip(hostname: str) -> bool:
        """Check if a hostname resolves to a private/reserved IP address."""
        import ipaddress
        try:
            # Resolve hostname to IP
            ip_str = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(ip_str)
            return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
        except (socket.gaierror, ValueError):
            return True  # Fail closed — if we can't resolve, block it

    def _curl(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request."""
        url = args.get("url")
        method = args.get("method", "GET").upper()
        headers = args.get("headers", {})
        body = args.get("body")

        # Security validation
        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            raise ValueError("Only HTTP and HTTPS URLs are allowed")

        # SSRF protection: block requests to private/internal IPs
        hostname = parsed.hostname or ""
        if self._is_private_ip(hostname):
            raise ValueError("Requests to private/internal IP addresses are not allowed")

        # Make request with timeout and size limit
        try:
            if method == "GET":
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=5,
                    stream=True
                )
            elif method == "POST":
                response = requests.post(
                    url,
                    headers=headers,
                    data=body,
                    timeout=5,
                    stream=True
                )
            else:
                raise ValueError(f"Unsupported method: {method}")

            # Read response with 1MB limit
            content = ""
            size = 0
            max_size = 1024 * 1024  # 1MB

            for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
                if chunk:
                    size += len(chunk)
                    if size > max_size:
                        content += "\n[Response truncated - exceeded 1MB limit]"
                        break
                    content += chunk

            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": content,
                "size_bytes": size
            }

        except requests.exceptions.Timeout:
            raise ValueError("Request timed out after 5 seconds")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Request failed: {str(e)}")

    def _df(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get disk space usage."""
        path = args.get("path", "/")

        try:
            usage = psutil.disk_usage(path)
            return {
                "path": path,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent_used": usage.percent
            }
        except Exception as e:
            raise ValueError(f"Failed to get disk usage: {str(e)}")

    def _free(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get memory usage."""
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()

            return {
                "memory": {
                    "total_mb": round(mem.total / (1024**2), 2),
                    "used_mb": round(mem.used / (1024**2), 2),
                    "available_mb": round(mem.available / (1024**2), 2),
                    "percent_used": mem.percent
                },
                "swap": {
                    "total_mb": round(swap.total / (1024**2), 2),
                    "used_mb": round(swap.used / (1024**2), 2),
                    "free_mb": round(swap.free / (1024**2), 2),
                    "percent_used": swap.percent
                }
            }
        except Exception as e:
            raise ValueError(f"Failed to get memory usage: {str(e)}")

    def _uptime(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get system uptime."""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = psutil.time.time() - boot_time

            # Format uptime
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)

            uptime_str = ""
            if days > 0:
                uptime_str += f"{days}d "
            if hours > 0 or days > 0:
                uptime_str += f"{hours}h "
            uptime_str += f"{minutes}m"

            # Get load averages (Unix-like systems only)
            try:
                load1, load5, load15 = os.getloadavg()
            except (AttributeError, OSError):
                load1 = load5 = load15 = 0.0

            return {
                "uptime": uptime_str.strip(),
                "uptime_seconds": int(uptime_seconds),
                "load_average": {
                    "1min": round(load1, 2),
                    "5min": round(load5, 2),
                    "15min": round(load15, 2)
                }
            }
        except Exception as e:
            raise ValueError(f"Failed to get uptime: {str(e)}")

    def _ps(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List running processes."""
        filter_str = args.get("filter", "").lower()
        limit = args.get("limit", 10)

        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'cmdline']):
                try:
                    info = proc.info

                    # Apply filter if specified
                    if filter_str and filter_str not in info['name'].lower():
                        continue

                    # Get command line (truncated, with sensitive args redacted)
                    cmdline = ' '.join(info['cmdline']) if info['cmdline'] else info['name']
                    # Redact common credential patterns
                    import re as _re
                    cmdline = _re.sub(r'(?<=-p\s).+?(?=\s|$)', '[REDACTED]', cmdline)
                    cmdline = _re.sub(r'(?<=password[=:\s]).+?(?=\s|$)', '[REDACTED]', cmdline, flags=_re.IGNORECASE)
                    cmdline = _re.sub(r'(?<=key[=:\s])\S+', '[REDACTED]', cmdline, flags=_re.IGNORECASE)
                    cmdline = _re.sub(r'(?<=token[=:\s])\S+', '[REDACTED]', cmdline, flags=_re.IGNORECASE)
                    cmdline = _re.sub(r'(?<=secret[=:\s])\S+', '[REDACTED]', cmdline, flags=_re.IGNORECASE)
                    cmdline = _re.sub(r'sk-[a-zA-Z0-9]{10,}', '[REDACTED]', cmdline)
                    if len(cmdline) > 80:
                        cmdline = cmdline[:77] + "..."

                    processes.append({
                        "pid": info['pid'],
                        "name": info['name'],
                        "cpu_percent": round(info['cpu_percent'] or 0.0, 1),
                        "memory_percent": round(info['memory_percent'] or 0.0, 1),
                        "command": cmdline
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort by CPU usage (descending)
            processes.sort(key=lambda p: p['cpu_percent'], reverse=True)

            # Limit results
            processes = processes[:limit]

            return {
                "processes": processes,
                "total_count": len(psutil.pids()),
                "shown_count": len(processes)
            }
        except Exception as e:
            raise ValueError(f"Failed to list processes: {str(e)}")

    def _ping(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Test network connectivity."""
        host = args.get("host")

        if not host:
            raise ValueError("Host is required")

        try:
            # Try to resolve hostname
            try:
                ip = socket.gethostbyname(host)
            except socket.gaierror:
                return {
                    "host": host,
                    "reachable": False,
                    "error": "Could not resolve hostname"
                }

            # Test TCP connection on port 80 (HTTP)
            start_time = psutil.time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)

            try:
                result = sock.connect_ex((ip, 80))
                latency_ms = round((psutil.time.time() - start_time) * 1000, 2)

                if result == 0:
                    reachable = True
                    error = None
                else:
                    # Try HTTPS port 443
                    start_time = psutil.time.time()
                    result = sock.connect_ex((ip, 443))
                    latency_ms = round((psutil.time.time() - start_time) * 1000, 2)
                    reachable = (result == 0)
                    error = None if reachable else "Ports 80 and 443 not responding"

                return {
                    "host": host,
                    "ip": ip,
                    "reachable": reachable,
                    "latency_ms": latency_ms if reachable else None,
                    "error": error
                }
            finally:
                sock.close()

        except socket.timeout:
            return {
                "host": host,
                "reachable": False,
                "error": "Connection timed out"
            }
        except Exception as e:
            return {
                "host": host,
                "reachable": False,
                "error": str(e)
            }

    def _error(self, request_id: int, message: str) -> Dict[str, Any]:
        """Return an error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -1,
                "message": message
            }
        }


def main():
    """Main entry point for MCP server."""
    server = SystemMCPServer()

    # Read requests from stdin, write responses to stdout
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            response = server.handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}"
                }
            }
            print(json.dumps(error_response), flush=True)
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -1,
                    "message": f"Internal error: {str(e)}"
                }
            }
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    main()
