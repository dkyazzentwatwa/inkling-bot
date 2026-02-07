# Multiple Directory Access via MCP

## Overview

Project Inkling supports accessing multiple directories through the Model Context Protocol (MCP). Each MCP filesystem server instance can access a different directory, allowing your AI to work with files across multiple locations.

## Configuration

### Basic Setup

Edit `config.local.yml` (or `config.yml`) and add filesystem servers under `mcp.servers`:

```yaml
mcp:
  enabled: true
  max_tools: 20  # Adjust if you have many MCP servers
  servers:
    # Default Inkling data directory (always include this)
    filesystem-inkling:
      command: "python"
      args: ["mcp_servers/filesystem.py", "/home/pi/.inkling"]

    # SD card storage (optional)
    filesystem-sd:
      command: "python"
      args: ["mcp_servers/filesystem.py", "/media/pi/SD_CARD"]

    # Custom project directory
    filesystem-projects:
      command: "python"
      args: ["mcp_servers/filesystem.py", "/home/pi/projects"]

    # Documents folder
    filesystem-docs:
      command: "python"
      args: ["mcp_servers/filesystem.py", "/home/pi/Documents"]

    # USB drive (example)
    filesystem-usb:
      command: "python"
      args: ["mcp_servers/filesystem.py", "/media/pi/USB_DRIVE"]
```

### Important Notes

1. **Server Naming**: Use descriptive names like `filesystem-projects`, `filesystem-sd`, etc.
2. **Path Argument**: The second argument in `args` is the base directory path
3. **Multiple Instances**: Each server runs independently and can access its own directory
4. **Tool Names**: Tools are prefixed with server name (e.g., `fs_list`, `fs_read`, `fs_write`)

## Available MCP Tools

Each filesystem server provides these tools:

| Tool | Description | Example Usage |
|------|-------------|---------------|
| `fs_list` | List files in directory | "List all Python files in my projects" |
| `fs_read` | Read file contents | "Show me the contents of app.py" |
| `fs_write` | Create or update file | "Create a README.md in the docs folder" |
| `fs_search` | Search file contents | "Find all files containing 'TODO'" |
| `fs_info` | Get file metadata | "What's the size of config.yml?" |

## How AI Uses Multiple Directories

When you configure multiple filesystem servers, the AI automatically has access to all of them. You can ask questions like:

**Example 1: Cross-directory operations**
```
User: "Copy my project README from projects/ to the SD card"

Inkling: I'll read the README from the projects directory and write it to the SD card.
*uses fs_read on filesystem-projects*
*uses fs_write on filesystem-sd*
```

**Example 2: Search across locations**
```
User: "Find all Python files with 'import flask' in my projects and docs"

Inkling: Let me search both directories for you.
*uses fs_search on filesystem-projects*
*uses fs_search on filesystem-docs*
```

**Example 3: Organize files**
```
User: "Move all CSV files from .inkling to the documents folder"

Inkling: I'll read the CSV files and copy them to Documents.
*uses fs_list on filesystem-inkling*
*uses fs_read and fs_write to transfer files*
```

## Web UI Integration

### Current Status

The Web UI file browser currently shows two storage locations in the dropdown:
- **Inkling** - `~/.inkling/` directory
- **SD Card** - Auto-detected SD card or configured path

### Accessing Other Directories

While the Web UI dropdown doesn't automatically show all MCP directories yet, you can:

1. **Via AI Commands**: Ask Inkling to read/write files in other directories
2. **Direct Path Access**: If you know the path, you can manually navigate (requires code modification)
3. **Future Enhancement**: Auto-populate dropdown from MCP configuration

### Example Workflow

```
# User asks AI to create a project
User: "Create a Flask app in /home/pi/projects/myapp/"

# AI uses filesystem-projects MCP server
Inkling: *creates files using fs_write*

# User wants to edit via Web UI
User: "Now copy that project to .inkling/myapp so I can edit it in the web UI"

# AI copies files to accessible location
Inkling: *uses fs_read on projects and fs_write on inkling*

# User can now see and edit in Web UI at http://localhost:8081/files
```

## Auto-Detection Examples

### SD Card Auto-Detection

```yaml
mcp:
  servers:
    filesystem-sd:
      command: "python"
      args: ["mcp_servers/filesystem.py", "/media/pi/SD_CARD"]
```

The system will:
1. Check `/media/pi/*` for mounted SD cards
2. Use the first found SD card if multiple exist
3. Fall back to `/mnt/*` if nothing in `/media/pi/`

You can also use `"auto"` to enable auto-detection:

```yaml
storage:
  sd_card:
    enabled: true
    path: "auto"  # Auto-detect SD card
```

### USB Drive Detection

```yaml
mcp:
  servers:
    filesystem-usb:
      command: "python"
      args: ["mcp_servers/filesystem.py", "/media/pi/USB_DRIVE"]
```

Replace `USB_DRIVE` with your actual USB mount point (run `lsblk` to see available drives).

## Security Considerations

### Path Restrictions

Each MCP filesystem server can only access files **within its configured base directory**. This prevents:
- Directory traversal attacks
- Accidental access to system files
- Unauthorized file modifications

Example:
```yaml
# This server can ONLY access /home/pi/projects and subdirectories
filesystem-projects:
  command: "python"
  args: ["mcp_servers/filesystem.py", "/home/pi/projects"]
```

Attempting to access `/etc/passwd` via this server would fail with a security error.

### Protected System Directories

**Do NOT add MCP servers for these directories**:
- `/etc/` - System configuration
- `/sys/` - System information
- `/proc/` - Process information
- `/root/` - Root user home (unless you know what you're doing)
- `/boot/` - Boot files

### Recommended Directories

**Safe to add**:
- `/home/pi/projects/` - User projects
- `/home/pi/Documents/` - User documents
- `/home/pi/.inkling/` - Inkling data (default)
- `/media/pi/*` - External storage (SD, USB)
- `/tmp/` - Temporary files (be cautious with cleanup)

## Troubleshooting

### Issue: "Storage 'projects' not available"

**Cause**: Web UI doesn't recognize the MCP server name.

**Solution**: Currently, the Web UI only supports "inkling" and "sd". Use the AI to access other directories:
```
User: "Read the file /home/pi/projects/app.py"
Inkling: *uses filesystem-projects MCP server*
```

### Issue: "Permission denied" when accessing directory

**Cause**: Directory doesn't exist or Pi user lacks permissions.

**Solution**:
```bash
# Create the directory
mkdir -p /home/pi/projects

# Fix permissions
sudo chown pi:pi /home/pi/projects
chmod 755 /home/pi/projects
```

### Issue: MCP tools not appearing

**Cause**: MCP server failed to start or `mcp.enabled: false`.

**Solution**:
1. Check configuration:
   ```yaml
   mcp:
     enabled: true  # Must be true
   ```

2. Verify server definition:
   ```yaml
   servers:
     filesystem-projects:  # Name must start with 'filesystem-'
       command: "python"
       args: ["mcp_servers/filesystem.py", "/home/pi/projects"]  # Valid path
   ```

3. Restart Inkling:
   ```bash
   # Kill running instance
   pkill -f "python main.py"

   # Start with debug output
   INKLING_DEBUG=1 python main.py --mode ssh
   ```

4. Check logs for MCP errors:
   ```bash
   cat ~/.inkling/inkling.log | grep -i "mcp"
   ```

### Issue: "File type not supported"

**Cause**: File extension not in SUPPORTED_EXTENSIONS.

**Solution**: Add the extension to the supported list in `modes/web_chat.py:3523` (view endpoint) and `modes/web_chat.py:3605` (edit endpoint).

## Advanced Configuration

### Limit Tools per Server

If you have many MCP servers, you might hit the tool limit (default 20). Increase it:

```yaml
mcp:
  max_tools: 50  # Increase limit (OpenAI allows up to 128)
```

### Prioritize Built-in Servers

Built-in servers (tasks, system, filesystem-inkling) are loaded first. Third-party servers are loaded after.

### Disable Specific Servers

Comment out servers you don't need:

```yaml
mcp:
  servers:
    # filesystem-sd:  # Disabled
    #   command: "python"
    #   args: ["mcp_servers/filesystem.py", "/media/pi/SD_CARD"]

    filesystem-projects:  # Enabled
      command: "python"
      args: ["mcp_servers/filesystem.py", "/home/pi/projects"]
```

## Example Use Cases

### Use Case 1: Development Workflow

```yaml
mcp:
  servers:
    filesystem-inkling:
      command: "python"
      args: ["mcp_servers/filesystem.py", "/home/pi/.inkling"]

    filesystem-projects:
      command: "python"
      args: ["mcp_servers/filesystem.py", "/home/pi/projects"]

    filesystem-backups:
      command: "python"
      args: ["mcp_servers/filesystem.py", "/home/pi/backups"]
```

**Workflow**:
1. AI creates code in `projects/`
2. User edits via Web UI after copying to `.inkling/`
3. AI backs up finished projects to `backups/`

### Use Case 2: Data Analysis

```yaml
mcp:
  servers:
    filesystem-inkling:
      command: "python"
      args: ["mcp_servers/filesystem.py", "/home/pi/.inkling"]

    filesystem-data:
      command: "python"
      args: ["mcp_servers/filesystem.py", "/home/pi/data"]

    filesystem-reports:
      command: "python"
      args: ["mcp_servers/filesystem.py", "/home/pi/reports"]
```

**Workflow**:
1. AI reads CSV files from `data/`
2. AI generates analysis reports in `reports/`
3. User downloads reports via Web UI

### Use Case 3: Multi-Device Sync

```yaml
mcp:
  servers:
    filesystem-inkling:
      command: "python"
      args: ["mcp_servers/filesystem.py", "/home/pi/.inkling"]

    filesystem-sd:
      command: "python"
      args: ["mcp_servers/filesystem.py", "/media/pi/SD_CARD"]

    filesystem-usb:
      command: "python"
      args: ["mcp_servers/filesystem.py", "/media/pi/USB_DRIVE"]
```

**Workflow**:
1. AI syncs important files to SD card
2. AI creates backup on USB drive
3. User can swap drives and access files on multiple Pis

## Summary

- ✅ Each MCP filesystem server accesses one directory
- ✅ Configure multiple servers to access multiple directories
- ✅ AI can work across all configured directories
- ✅ Web UI shows "inkling" and "sd" in dropdown
- ✅ Other directories accessible via AI commands
- ✅ Path security prevents directory traversal
- ✅ Protected system files cannot be deleted

**Next Steps**:
1. Edit `config.local.yml` to add desired directories
2. Restart Inkling
3. Ask AI to list files in new directories
4. Use Web UI for editing files in `.inkling/` and SD card
