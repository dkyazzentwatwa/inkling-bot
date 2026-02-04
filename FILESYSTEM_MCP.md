# Filesystem MCP Server

Lightweight Python-based filesystem access for Inkling.

## Features

✅ **No Node.js required** - Pure Python implementation
✅ **Secure** - Restricted to a base directory, prevents path traversal
✅ **Fast** - No external dependencies beyond stdlib
✅ **Easy to customize** - Simple Python code

## Tools Provided

### 1. `fs_list` - List Directory Contents

Lists files and directories in a path.

**Example:**
```
"list files in Documents"
"show me what's in the downloads folder"
```

**Parameters:**
- `path`: Directory path (relative to base)
- `show_hidden`: Include hidden files (default: false)

### 2. `fs_read` - Read File Contents

Reads a text file's contents.

**Example:**
```
"read the file notes.txt"
"show me what's in config.yml"
```

**Parameters:**
- `path`: File path to read
- `max_size`: Maximum file size in bytes (default: 1MB)

### 3. `fs_write` - Write to File

Writes content to a file.

**Example:**
```
"write 'Hello World' to test.txt"
"create a file called notes.md with my ideas"
```

**Parameters:**
- `path`: File path to write to
- `content`: Content to write
- `append`: Append instead of overwrite (default: false)

### 4. `fs_search` - Search for Files

Search for files by name pattern.

**Example:**
```
"find all .py files"
"search for files named config"
```

**Parameters:**
- `pattern`: Glob pattern (e.g., `*.txt`, `**/*.py`)
- `path`: Directory to search in (default: root)

### 5. `fs_info` - Get File Information

Get detailed information about a file or directory.

**Example:**
```
"get info on that file"
"when was notes.txt last modified?"
```

**Parameters:**
- `path`: Path to get info for

## Security Features

🔒 **Path Validation** - All paths are validated and normalized
🔒 **Base Directory Restriction** - Cannot access files outside base directory
🔒 **No Path Traversal** - `../` attacks are blocked
🔒 **Size Limits** - File reads limited to 1MB by default
🔒 **Safe Operations** - Only read/write text files

## Setup

### Enable in Config

Edit `config.local.yml`:

```yaml
mcp:
  enabled: true
  max_tools: 20
  servers:
    tasks:
      command: "python"
      args: ["mcp_servers/tasks.py"]

    filesystem:
      command: "python"
      args: ["mcp_servers/filesystem.py", "/home/pi"]  # Base directory
```

### Choose Your Base Directory

The base directory restricts where the AI can access files:

**Option 1: User home** (recommended)
```yaml
args: ["mcp_servers/filesystem.py", "/home/pi"]
```

**Option 2: Specific project**
```yaml
args: ["mcp_servers/filesystem.py", "/home/pi/my-project"]
```

**Option 3: Multiple directories** (not supported - choose one)
- If you need multiple, run separate servers

## Testing

### Manual Test

```bash
# List files
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | \
  python mcp_servers/filesystem.py /home/pi

# Expected: List of available tools
```

### In Inkling

```bash
python main.py --mode ssh
```

Then try:
- `"list files in my home directory"`
- `"create a file called test.txt with 'Hello World'"`
- `"read the file test.txt"`
- `"find all .txt files"`

## Comparison to Node.js Version

| Feature | Python Version | Node.js Version |
|---------|---------------|-----------------|
| **Dependencies** | None (stdlib) | Node.js, npm |
| **Install Size** | ~10KB | ~100MB+ |
| **Startup Time** | Instant | ~1-2 seconds |
| **Features** | Basic (5 tools) | Advanced (10+ tools) |
| **Customization** | Easy (Python) | Harder (TypeScript) |
| **Performance** | Fast | Fast |

## Usage Examples

### Example 1: Take Notes

**User:** "Create a file called journal.md with today's thoughts"

**AI Response:** Uses `fs_write` to create the file with content.

### Example 2: Read Config

**User:** "What's in my config file?"

**AI Response:** Uses `fs_read` to read and show the config.

### Example 3: Find Files

**User:** "Find all Python files in my project"

**AI Response:** Uses `fs_search` with pattern `*.py` or `**/*.py`.

### Example 4: Browse Files

**User:** "What files are in my Documents folder?"

**AI Response:** Uses `fs_list` to show directory contents.

## Troubleshooting

### "Invalid path" Error

The path is outside the base directory. Check your base directory setting.

### "File too large" Error

File exceeds 1MB limit. You can increase by passing `max_size` parameter:
```python
# In the tool call
{"path": "large.txt", "max_size": 10485760}  # 10MB
```

### Permission Denied

The Pi user doesn't have permission to access that path. Choose a different base directory or fix permissions.

## Extending the Server

To add new tools, edit `mcp_servers/filesystem.py`:

1. Add tool definition to `self.tools` list
2. Add method `_tool_yourname(self, args)`
3. Add handler in `handle_request()` method

Example:
```python
def _tool_rename(self, args: Dict[str, Any]) -> Dict[str, Any]:
    """Rename a file."""
    old_path = self._safe_path(args["old_path"])
    new_path = self._safe_path(args["new_path"])

    if not old_path or not new_path:
        return {"success": False, "error": "Invalid path"}

    os.rename(old_path, new_path)
    return {"success": True}
```

## Notes

- Text files only (UTF-8 encoding)
- Binary files not supported
- No file deletion tool (for safety)
- No directory creation tool (created automatically on write)
- Symlinks are followed (be careful!)
