#!/usr/bin/env python3
"""
Filesystem MCP Server - Lightweight Python Implementation

Provides safe file system access through MCP protocol.

Tools:
- fs_list: List files and directories
- fs_read: Read file contents
- fs_write: Write to a file
- fs_search: Search for files by name pattern
- fs_info: Get file/directory information
"""

import json
import os
import sys
import glob
import time
from pathlib import Path
from typing import Dict, Any, List, Optional


class FilesystemMCPServer:
    """MCP server for filesystem operations."""

    def __init__(self, base_path: str = None):
        """
        Initialize filesystem server.

        Args:
            base_path: Root directory for file operations (security boundary)
                      Defaults to user's home directory
        """
        if base_path is None:
            base_path = str(Path.home())

        self.base_path = os.path.abspath(os.path.expanduser(base_path))

        # Ensure base path exists
        if not os.path.exists(self.base_path):
            raise ValueError(f"Base path does not exist: {self.base_path}")

        # Tool definitions
        self.tools = [
            {
                "name": "fs_list",
                "description": f"List files and directories. Base path: {self.base_path}",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": f"Directory path relative to {self.base_path} (default: root)"
                        },
                        "show_hidden": {
                            "type": "boolean",
                            "description": "Include hidden files (starting with .)",
                            "default": False
                        }
                    }
                }
            },
            {
                "name": "fs_read",
                "description": "Read a text file's contents",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path to read"
                        },
                        "max_size": {
                            "type": "integer",
                            "description": "Maximum file size in bytes (default: 1MB)",
                            "default": 1048576
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "fs_write",
                "description": "Write content to a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path to write to"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write"
                        },
                        "append": {
                            "type": "boolean",
                            "description": "Append instead of overwrite",
                            "default": False
                        }
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "fs_search",
                "description": "Search for files by name pattern",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern to search (e.g., '*.txt', '**/*.py')"
                        },
                        "path": {
                            "type": "string",
                            "description": "Directory to search in (default: root)"
                        }
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "fs_info",
                "description": "Get file or directory information",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to get info for"
                        }
                    },
                    "required": ["path"]
                }
            }
        ]

    def _safe_path(self, path: str) -> Optional[str]:
        """
        Validate and resolve a path within the base directory.
        Uses realpath to resolve symlinks and commonpath for containment.

        Args:
            path: User-provided path

        Returns:
            Absolute safe path, or None if invalid
        """
        try:
            base_real = os.path.realpath(self.base_path)

            # Handle empty path (root)
            if not path or path == ".":
                return base_real

            # Resolve relative to base, following symlinks
            full_path = os.path.realpath(os.path.normpath(os.path.join(base_real, path)))

            # Security: Ensure path is within base directory using commonpath
            if os.path.commonpath([base_real, full_path]) != base_real:
                return None

            return full_path
        except (ValueError, OSError):
            return None

    def _error(self, request_id: int, message: str) -> Dict[str, Any]:
        """Create an error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32000,
                "message": message
            }
        }

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an MCP request."""
        method = request.get("method")
        request_id = request.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "filesystem",
                        "version": "1.0.0"
                    }
                }
            }

        elif method == "notifications/initialized":
            # No response needed for notifications
            return None

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": self.tools
                }
            }

        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            # Execute the tool
            if tool_name == "fs_list":
                result = self._tool_list(arguments)
            elif tool_name == "fs_read":
                result = self._tool_read(arguments)
            elif tool_name == "fs_write":
                result = self._tool_write(arguments)
            elif tool_name == "fs_search":
                result = self._tool_search(arguments)
            elif tool_name == "fs_info":
                result = self._tool_info(arguments)
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

        else:
            return self._error(request_id, f"Unknown method: {method}")

    def _tool_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List files and directories."""
        path = args.get("path", "")
        show_hidden = args.get("show_hidden", False)

        safe_path = self._safe_path(path)
        if not safe_path:
            return {"success": False, "error": "Invalid path"}

        if not os.path.exists(safe_path):
            return {"success": False, "error": "Path does not exist"}

        if not os.path.isdir(safe_path):
            return {"success": False, "error": "Path is not a directory"}

        try:
            entries = []
            for entry in os.scandir(safe_path):
                # Skip hidden files unless requested
                if not show_hidden and entry.name.startswith('.'):
                    continue

                stat = entry.stat()
                entries.append({
                    "name": entry.name,
                    "type": "directory" if entry.is_dir() else "file",
                    "size": stat.st_size if entry.is_file() else None,
                    "modified": stat.st_mtime,
                    "path": os.path.relpath(entry.path, self.base_path)
                })

            # Sort: directories first, then by name
            entries.sort(key=lambda x: (x["type"] != "directory", x["name"]))

            return {
                "success": True,
                "path": os.path.relpath(safe_path, self.base_path) or ".",
                "count": len(entries),
                "entries": entries
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_read(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Read a file's contents."""
        path = args.get("path")
        max_size = args.get("max_size", 1048576)  # 1MB default

        if not path:
            return {"success": False, "error": "Path is required"}

        safe_path = self._safe_path(path)
        if not safe_path:
            return {"success": False, "error": "Invalid path"}

        if not os.path.exists(safe_path):
            return {"success": False, "error": "File does not exist"}

        if not os.path.isfile(safe_path):
            return {"success": False, "error": "Path is not a file"}

        try:
            # Check file size
            file_size = os.path.getsize(safe_path)
            if file_size > max_size:
                return {
                    "success": False,
                    "error": f"File too large: {file_size} bytes (max: {max_size})"
                }

            # Read file
            with open(safe_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            return {
                "success": True,
                "path": path,
                "size": file_size,
                "content": content
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_write(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Write content to a file."""
        path = args.get("path")
        content = args.get("content")
        append = args.get("append", False)

        if not path:
            return {"success": False, "error": "Path is required"}

        if content is None:
            return {"success": False, "error": "Content is required"}

        safe_path = self._safe_path(path)
        if not safe_path:
            return {"success": False, "error": "Invalid path"}

        try:
            # Create parent directories if needed
            parent_dir = os.path.dirname(safe_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir)

            # Write file
            mode = 'a' if append else 'w'
            with open(safe_path, mode, encoding='utf-8') as f:
                f.write(content)

            return {
                "success": True,
                "path": path,
                "size": len(content),
                "mode": "appended" if append else "written"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search for files by pattern."""
        pattern = args.get("pattern")
        search_path = args.get("path", "")

        if not pattern:
            return {"success": False, "error": "Pattern is required"}

        safe_path = self._safe_path(search_path)
        if not safe_path:
            return {"success": False, "error": "Invalid path"}

        if not os.path.exists(safe_path):
            return {"success": False, "error": "Path does not exist"}

        try:
            base_real = os.path.realpath(self.base_path)
            # Use glob to search with result limit
            search_pattern = os.path.join(safe_path, pattern)
            matches = []
            max_results = 100

            for match in glob.glob(search_pattern, recursive=True):
                # Security check using realpath + commonpath
                try:
                    real_match = os.path.realpath(match)
                    if os.path.commonpath([base_real, real_match]) != base_real:
                        continue
                except (ValueError, OSError):
                    continue

                stat = os.stat(real_match)
                matches.append({
                    "path": os.path.relpath(real_match, base_real),
                    "name": os.path.basename(real_match),
                    "type": "directory" if os.path.isdir(real_match) else "file",
                    "size": stat.st_size if os.path.isfile(real_match) else None,
                    "modified": stat.st_mtime
                })

                if len(matches) >= max_results:
                    break

            return {
                "success": True,
                "pattern": pattern,
                "count": len(matches),
                "matches": matches,
                "truncated": len(matches) >= max_results
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get file/directory information."""
        path = args.get("path")

        if not path:
            return {"success": False, "error": "Path is required"}

        safe_path = self._safe_path(path)
        if not safe_path:
            return {"success": False, "error": "Invalid path"}

        if not os.path.exists(safe_path):
            return {"success": False, "error": "Path does not exist"}

        try:
            stat = os.stat(safe_path)
            is_dir = os.path.isdir(safe_path)

            info = {
                "success": True,
                "path": path,
                "name": os.path.basename(safe_path),
                "type": "directory" if is_dir else "file",
                "size": stat.st_size if not is_dir else None,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
                "permissions": oct(stat.st_mode)[-3:],
                "owner": stat.st_uid,
            }

            # Add directory-specific info
            if is_dir:
                try:
                    entries = list(os.scandir(safe_path))
                    info["item_count"] = len(entries)
                except:
                    pass

            return info

        except Exception as e:
            return {"success": False, "error": str(e)}

    def run(self):
        """Run the MCP server (stdio mode)."""
        print(f"[Filesystem] Base path: {self.base_path}", file=sys.stderr)

        for line in sys.stdin:
            try:
                request = json.loads(line)
                response = self.handle_request(request)

                # Only send response if not None (notifications don't get responses)
                if response is not None:
                    print(json.dumps(response), flush=True)

            except json.JSONDecodeError:
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }), flush=True)
            except Exception as e:
                print(f"[Filesystem] Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    # Get base path from command line arg or use home directory
    base_path = sys.argv[1] if len(sys.argv) > 1 else None

    server = FilesystemMCPServer(base_path=base_path)
    server.run()
