"""
Project Inkling - MCP Client Integration

Connects to MCP (Model Context Protocol) servers to give Inkling access to
external tools like file systems, databases, APIs, and more.
"""

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager
import aiohttp


@dataclass
class MCPTool:
    """Represents a tool exposed by an MCP server."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str


@dataclass
class MCPServer:
    """Configuration for an MCP server."""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    transport: str = "stdio"  # stdio | http
    url: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    session_id: Optional[str] = None


class MCPClientManager:
    """
    Manages connections to multiple MCP servers.

    Handles:
    - Starting/stopping MCP server processes
    - Discovering available tools from each server
    - Routing tool calls to the appropriate server
    - Aggregating tools for the AI to use
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize with MCP configuration.

        Config format:
        {
            "servers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/pi"],
                },
                "fetch": {
                    "command": "uvx",
                    "args": ["mcp-server-fetch"],
                }
            }
        }
        """
        self.config = config
        self.servers: Dict[str, MCPServer] = {}
        self.processes: Dict[str, subprocess.Popen] = {}
        self.tools: Dict[str, MCPTool] = {}  # tool_name -> MCPTool
        self._readers: Dict[str, asyncio.StreamReader] = {}
        self._writers: Dict[str, asyncio.StreamWriter] = {}
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._http_sessions: Dict[str, aiohttp.ClientSession] = {}

        self._parse_config()

    def _parse_config(self) -> None:
        """Parse server configurations."""
        servers_config = self.config.get("servers", {})
        for name, server_config in servers_config.items():
            self.servers[name] = MCPServer(
                name=name,
                command=server_config.get("command", ""),
                args=server_config.get("args", []),
                env=server_config.get("env", {}),
                transport=server_config.get("transport", "http" if server_config.get("url") else "stdio"),
                url=server_config.get("url"),
                headers=server_config.get("headers", {}),
            )

    async def start_all(self) -> None:
        """Start all configured MCP servers."""
        for name in self.servers:
            try:
                await self.start_server(name)
            except Exception as e:
                print(f"[MCP] Failed to start {name}: {e}")

    async def start_server(self, name: str) -> None:
        """Start a single MCP server and discover its tools."""
        if name not in self.servers:
            raise ValueError(f"Unknown server: {name}")

        server = self.servers[name]

        if server.transport == "http":
            # Initialize HTTP-based MCP server
            if not server.url:
                raise ValueError(f"HTTP transport requires url for server: {name}")
            await self._initialize(name)
            await self._discover_tools(name)
            return

        # Build environment
        env = os.environ.copy()
        env.update(server.env)

        # Start the process with pipes for JSON-RPC communication
        cmd = [server.command] + server.args
        print(f"[MCP] Starting {name}: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        self.processes[name] = process
        self._readers[name] = process.stdout
        self._writers[name] = process.stdin

        # Start reading responses in background
        asyncio.create_task(self._read_responses(name))

        # Initialize the connection (MCP protocol)
        await self._initialize(name)

        # Discover tools
        await self._discover_tools(name)

    async def _initialize(self, name: str) -> None:
        """Send MCP initialize request."""
        response = await self._send_request(name, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "inkling",
                "version": "1.0.0"
            }
        })

        # Send initialized notification
        await self._send_notification(name, "notifications/initialized", {})
        print(f"[MCP] {name} initialized: {response.get('serverInfo', {}).get('name', 'unknown')}")

    async def _discover_tools(self, name: str) -> None:
        """Discover tools from an MCP server."""
        response = await self._send_request(name, "tools/list", {})

        tools = response.get("tools", [])
        for tool in tools:
            tool_name = tool["name"]
            # Prefix with server name to avoid collisions
            full_name = f"{name}__{tool_name}"
            self.tools[full_name] = MCPTool(
                name=tool_name,
                description=tool.get("description", ""),
                input_schema=tool.get("inputSchema", {}),
                server_name=name,
            )

        print(f"[MCP] {name} provides {len(tools)} tools: {[t['name'] for t in tools]}")

    async def _send_request(self, server: str, method: str, params: Dict) -> Dict:
        """Send a JSON-RPC request and wait for response."""
        srv = self.servers.get(server)
        if srv and srv.transport == "http":
            return await self._send_request_http(server, method, params)

        self._request_id += 1
        request_id = self._request_id

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        # Send request
        writer = self._writers.get(server)
        if not writer:
            raise RuntimeError(f"No connection to {server}")

        message = json.dumps(request) + "\n"
        writer.write(message.encode())
        await writer.drain()

        # Wait for response with timeout
        try:
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
        except asyncio.TimeoutError:
            del self._pending_requests[request_id]
            raise RuntimeError(f"Timeout waiting for response from {server}")

    async def _send_notification(self, server: str, method: str, params: Dict) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        srv = self.servers.get(server)
        if srv and srv.transport == "http":
            await self._send_notification_http(server, method, params)
            return

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        writer = self._writers.get(server)
        if writer:
            message = json.dumps(notification) + "\n"
            writer.write(message.encode())
            await writer.drain()

    async def _read_responses(self, server: str) -> None:
        """Background task to read responses from MCP server."""
        reader = self._readers.get(server)
        if not reader:
            return

        try:
            while True:
                line = await reader.readline()
                if not line:
                    break

                try:
                    message = json.loads(line.decode())

                    # Handle response to our request
                    if "id" in message and message["id"] in self._pending_requests:
                        future = self._pending_requests.pop(message["id"])
                        if "error" in message:
                            future.set_exception(RuntimeError(message["error"]))
                        else:
                            future.set_result(message.get("result", {}))

                except json.JSONDecodeError:
                    continue

        except Exception as e:
            print(f"[MCP] Reader error for {server}: {e}")

    async def _send_request_http(self, server: str, method: str, params: Dict) -> Dict:
        """Send a JSON-RPC request over HTTP and return response."""
        self._request_id += 1
        request_id = self._request_id
        srv = self.servers[server]

        if server not in self._http_sessions:
            self._http_sessions[server] = aiohttp.ClientSession()

        headers = {
            "content-type": "application/json",
            **(srv.headers or {}),
        }
        if srv.session_id:
            headers["Mcp-Session-Id"] = srv.session_id

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        session = self._http_sessions[server]
        async with session.post(srv.url, json=payload, headers=headers) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise RuntimeError(f"HTTP {resp.status} from {server}: {text}")

            # Capture MCP session id if provided
            session_id = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
            if session_id:
                srv.session_id = session_id

            data = await resp.json()
            if "error" in data:
                raise RuntimeError(data["error"])
            return data.get("result", {})

    async def _send_notification_http(self, server: str, method: str, params: Dict) -> None:
        """Send a JSON-RPC notification over HTTP (no response expected)."""
        srv = self.servers[server]
        if server not in self._http_sessions:
            self._http_sessions[server] = aiohttp.ClientSession()

        headers = {
            "content-type": "application/json",
            **(srv.headers or {}),
        }
        if srv.session_id:
            headers["Mcp-Session-Id"] = srv.session_id

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        session = self._http_sessions[server]
        async with session.post(srv.url, json=payload, headers=headers) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise RuntimeError(f"HTTP {resp.status} from {server}: {text}")
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool by name.

        Args:
            tool_name: Full tool name (server__toolname)
            arguments: Tool arguments

        Returns:
            Tool result
        """
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        tool = self.tools[tool_name]
        server = tool.server_name

        response = await self._send_request(server, "tools/call", {
            "name": tool.name,  # Use original tool name (without prefix)
            "arguments": arguments,
        })

        # Extract content from response
        content = response.get("content", [])
        if content and len(content) > 0:
            return content[0].get("text", str(content))
        return str(response)

    def get_tools_for_ai(self) -> List[Dict[str, Any]]:
        """
        Get tool definitions formatted for Claude's tool use API.

        Returns list of tool definitions compatible with Anthropic's format.
        """
        tools = []
        for full_name, tool in self.tools.items():
            tools.append({
                "name": full_name,
                "description": f"[{tool.server_name}] {tool.description}",
                "input_schema": tool.input_schema,
            })
        return tools

    async def stop_all(self) -> None:
        """Stop all MCP server processes."""
        for name, process in self.processes.items():
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except:
                process.kill()
            print(f"[MCP] Stopped {name}")

        for name, session in self._http_sessions.items():
            try:
                await session.close()
            except Exception:
                pass

        self.processes.clear()
        self._readers.clear()
        self._writers.clear()
        self.tools.clear()
        self._http_sessions.clear()

    @property
    def has_tools(self) -> bool:
        """Check if any tools are available."""
        return len(self.tools) > 0

    @property
    def tool_count(self) -> int:
        """Number of available tools."""
        return len(self.tools)
