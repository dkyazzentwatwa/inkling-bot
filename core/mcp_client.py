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
        self.max_tools = config.get("max_tools", 20)  # Default to conservative limit
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
            limit=10 * 1024 * 1024,  # 10MB buffer for large responses (Composio has 215 tools)
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
        """Background task to read responses from MCP server.

        Note: Buffer limit is set to 10MB in create_subprocess_exec to handle
        large tool lists like Composio's 215 tools (~500KB JSON response).
        """
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

                except json.JSONDecodeError as e:
                    print(f"[MCP] JSON decode error for {server}: {e}")
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
            "accept": "application/json, text/event-stream",
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

            # Handle both JSON and Server-Sent Events (SSE) responses
            content_type = resp.headers.get("content-type", "").lower()

            if "text/event-stream" in content_type:
                # Parse SSE format
                text = await resp.text()
                data = self._parse_sse_response(text)
            else:
                # Parse as JSON (forcing it even if content-type is wrong)
                text = await resp.text()
                data = json.loads(text)

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
            "accept": "application/json, text/event-stream",
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

    def _parse_sse_response(self, sse_text: str) -> Dict[str, Any]:
        """
        Parse Server-Sent Events (SSE) response format.

        SSE format:
        data: {"jsonrpc":"2.0","id":1,"result":{...}}

        Returns the JSON object from the last 'data:' line.
        """
        lines = sse_text.strip().split('\n')

        # Find all data lines
        for line in reversed(lines):  # Start from end to get latest data
            line = line.strip()
            if line.startswith('data:'):
                # Extract JSON after "data: "
                json_str = line[5:].strip()  # Remove "data:" prefix
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue

        # If no valid data found, raise error
        raise RuntimeError(f"No valid JSON data found in SSE response: {sse_text[:100]}...")

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

    def search_tools(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search through all available tools by name and description.

        Args:
            query: Search query (e.g., "gmail", "calendar", "sheets")
            limit: Maximum number of results to return

        Returns:
            List of matching tool definitions
        """
        query_lower = query.lower()
        matches = []

        for full_name, tool in self.tools.items():
            # Check if query matches tool name or description
            if (query_lower in full_name.lower() or
                query_lower in tool.description.lower() or
                query_lower in tool.server_name.lower()):

                tool_def = {
                    "name": full_name,
                    "description": f"[{tool.server_name}] {tool.description}",
                    "input_schema": tool.input_schema,
                }
                matches.append(tool_def)

                if len(matches) >= limit:
                    break

        return matches

    def get_tools_for_query(self, query: str = "") -> List[Dict[str, Any]]:
        """
        Get tools dynamically based on user query - SMART ROUTING with no hard limit.

        Strategy:
        1. Always include core built-in tools (tasks, system, filesystem)
        2. If query contains keywords, include ALL matching tools (no limit)
        3. Fill remaining slots with other tools up to soft limit
        4. Only cap if total exceeds safety threshold (100 tools)

        Args:
            query: User's message/query (optional)

        Returns:
            List of tool definitions optimized for the query
        """
        # Core tools always included
        core_tools = []
        other_tools = []
        query_matched = []

        for full_name, tool in self.tools.items():
            tool_def = {
                "name": full_name,
                "description": f"[{tool.server_name}] {tool.description}",
                "input_schema": tool.input_schema,
            }

            # Core servers always included
            if tool.server_name in ["tasks", "system", "filesystem-inkling"]:
                core_tools.append(tool_def)
            else:
                other_tools.append(tool_def)

        # If query provided, search for relevant tools (NO LIMIT on matches)
        if query:
            query_lower = query.lower()
            # Expanded keyword list for better matching
            keywords = [
                "gmail", "email", "mail", "inbox",
                "calendar", "event", "meeting", "schedule",
                "sheet", "sheets", "spreadsheet",
                "notion", "note", "notes",
                "github", "git", "repo", "pr", "issue",
                "slack", "message", "chat",
                "drive", "file", "document", "doc"
            ]

            matched_keywords = set()
            for keyword in keywords:
                if keyword in query_lower:
                    matched_keywords.add(keyword)
                    # Search for ALL tools matching this keyword (no limit)
                    matched = self.search_tools(keyword, limit=50)
                    for tool_def in matched:
                        if tool_def not in query_matched and tool_def not in core_tools:
                            query_matched.append(tool_def)

            if matched_keywords:
                print(f"[MCP] Smart routing detected keywords: {', '.join(sorted(matched_keywords))}")

        # Smart assembly:
        # 1. Core tools (always)
        # 2. Query-matched tools (all of them - no limit!)
        # 3. Other tools (fill up to soft limit)

        essential_tools = core_tools + query_matched

        # Calculate remaining space for "other" tools
        soft_limit = self.max_tools  # Use max_tools as soft limit for "other" tools
        remaining_space = max(0, soft_limit - len(essential_tools))

        # Combine all
        all_tools = essential_tools + other_tools[:remaining_space]

        # Remove duplicates while preserving order
        seen = set()
        unique_tools = []
        for tool in all_tools:
            if tool["name"] not in seen:
                seen.add(tool["name"])
                unique_tools.append(tool)

        # Safety cap: Only limit if exceeding 100 tools (prevents AI overload)
        safety_cap = 100
        if len(unique_tools) > safety_cap:
            print(f"[MCP] Safety cap applied: {len(unique_tools)} → {safety_cap}")
            print(f"[MCP]   Core: {len(core_tools)}, Query-matched: {len(query_matched)}, Other: {remaining_space}")
            unique_tools = unique_tools[:safety_cap]
        else:
            if query_matched:
                print(f"[MCP] Smart routing loaded: {len(unique_tools)} tools")
                print(f"[MCP]   Core: {len(core_tools)}, Query-matched: {len(query_matched)}, Other: {len(unique_tools) - len(core_tools) - len(query_matched)}")
            elif len(unique_tools) != len(self.tools):
                print(f"[MCP] Loaded {len(unique_tools)} tools (soft limit: {soft_limit})")

        return unique_tools

    def get_tools_for_ai(self) -> List[Dict[str, Any]]:
        """
        Get tool definitions formatted for Claude's tool use API.

        DEPRECATED: Use get_tools_for_query() instead for dynamic tool selection.

        Returns list of tool definitions compatible with Anthropic's format.
        Limited by max_tools config to prevent overwhelming the AI.
        """
        # Prioritize: built-in tools first, then third-party
        builtin_tools = []
        thirdparty_tools = []

        for full_name, tool in self.tools.items():
            tool_def = {
                "name": full_name,
                "description": f"[{tool.server_name}] {tool.description}",
                "input_schema": tool.input_schema,
            }

            # Built-in servers: tasks, filesystem, etc.
            if tool.server_name in ["tasks", "filesystem", "memory", "fetch", "system"]:
                builtin_tools.append(tool_def)
            else:
                thirdparty_tools.append(tool_def)

        # Combine: all built-in + as many third-party as fit
        all_tools = builtin_tools + thirdparty_tools

        if len(all_tools) > self.max_tools:
            print(f"[MCP] Limiting tools from {len(all_tools)} to {self.max_tools}")
            print(f"[MCP]   Built-in: {len(builtin_tools)}, Third-party: {len(thirdparty_tools[:self.max_tools - len(builtin_tools)])}")
            all_tools = all_tools[:self.max_tools]

        return all_tools

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
