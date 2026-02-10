# MCP Integration Guide

Model Context Protocol (MCP) extends Inkling's capabilities with external tools, enabling integration with calendars, email, file systems, and 500+ apps through Composio.

## Overview

MCP allows Inkling to:
- **Use tools**: Call functions during conversations
- **Access services**: Google Calendar, Gmail, GitHub, Slack, etc.
- **Manage files**: Read, write, search local files
- **Execute tasks**: Run commands, fetch web content

## Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Inkling   │────▶│   MCP Client    │────▶│   MCP Servers   │
│   (Brain)   │     │  (Tool Router)  │     │  (Task, Files)  │
└─────────────┘     └─────────────────┘     └─────────────────┘
                                                    │
                                           ┌───────┴───────┐
                                           ▼               ▼
                                    ┌──────────┐   ┌──────────────┐
                                    │  Local   │   │   Composio   │
                                    │ (Python) │   │  (500+ Apps) │
                                    └──────────┘   └──────────────┘
```

## Quick Start

### Enable MCP

In `config.local.yml`:

```yaml
mcp:
  enabled: true
  max_tools: 20  # Limit total tools
  servers:
    tasks:
      command: "python"
      args: ["mcp_servers/tasks.py"]
```

Restart Inkling to load tools.

### Verify Tools

```bash
> What tools do you have?

Inkling: I have access to these tools:
- task_create: Create a new task
- task_list: List all tasks
- task_complete: Mark task complete
...
```

## Built-in MCP Servers

### Tasks Server

Manages tasks through AI conversation.

**Configuration:**
```yaml
mcp:
  servers:
    tasks:
      command: "python"
      args: ["mcp_servers/tasks.py"]
```

**Available Tools:**

| Tool | Description | Example |
|------|-------------|---------|
| `task_create` | Create new task | "Add a task to buy groceries" |
| `task_list` | List tasks | "Show my pending tasks" |
| `task_complete` | Complete task | "Mark the groceries task done" |
| `task_update` | Update task | "Change priority to high" |
| `task_delete` | Delete task | "Delete that task" |
| `task_stats` | Get statistics | "How many tasks did I complete?" |

### Filesystem Server

Read, write, and search local files.

**Configuration:**
```yaml
mcp:
  servers:
    filesystem:
      command: "python"
      args: ["mcp_servers/filesystem.py", "/home/pi"]
```

**Available Tools:**

| Tool | Description | Example |
|------|-------------|---------|
| `read_file` | Read file contents | "Read my notes.txt file" |
| `write_file` | Write to file | "Save this to ideas.txt" |
| `list_files` | List directory | "What files are in my documents?" |
| `search_files` | Search by pattern | "Find all Python files" |

**Security:** Restricted to specified directory (e.g., `/home/pi`).

## Composio Integration

### What is Composio?

Composio provides access to 500+ app integrations through a single API:
- Google Calendar, Gmail, Drive
- GitHub, GitLab
- Slack, Discord
- Notion, Todoist
- And many more...

### Setup

1. **Get API Key**
   - Visit [app.composio.dev](https://app.composio.dev)
   - Create account
   - Copy API key from Settings

2. **Set Environment Variable**
   ```bash
   export COMPOSIO_API_KEY=your-api-key-here
   # Or add to .env file
   ```

3. **Enable in Config**
   ```yaml
   mcp:
     servers:
       composio:
         transport: "http"
         url: "https://backend.composio.dev/v3/mcp"
         headers:
           x-api-key: "${COMPOSIO_API_KEY}"
   ```

4. **Connect Apps**
   - Visit Composio dashboard
   - Connect desired apps (OAuth flow)
   - Tools become available in Inkling

### Example: Google Calendar

After connecting Google Calendar:

```
> What's on my calendar today?

Inkling: Let me check your calendar...
[Uses GOOGLECALENDAR_LIST_EVENTS tool]

Today you have:
- 10:00 AM: Team standup
- 2:00 PM: Client call
- 4:30 PM: Code review
```

```
> Schedule a meeting with John tomorrow at 3pm

Inkling: Creating calendar event...
[Uses GOOGLECALENDAR_CREATE_EVENT tool]

Done! I've scheduled "Meeting with John" for tomorrow at 3:00 PM.
```

### Example: GitHub

```
> Show my open pull requests

Inkling: Checking GitHub...
[Uses GITHUB_LIST_PULL_REQUESTS tool]

You have 3 open PRs:
1. #142: Add dark mode support
2. #138: Fix memory leak
3. #135: Update documentation
```

### Example: Gmail

```
> Any important emails today?

Inkling: Let me check your inbox...
[Uses GMAIL_LIST_MESSAGES tool]

You have 5 unread emails:
- From: boss@company.com - "Quarterly Review"
- From: client@example.com - "Project Update"
...
```

## Third-Party MCP Servers

### Web Fetch

Fetch and analyze web content:

```yaml
mcp:
  servers:
    fetch:
      command: "uvx"
      args: ["mcp-server-fetch"]
```

```
> Summarize the news from hackernews.com

Inkling: [Fetches and summarizes page]
```

### Memory/Notes (Optional MCP Server)

External memory server for cross-tool note sharing:

```yaml
mcp:
  servers:
    memory:
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-memory"]
```

```
> Remember that my favorite color is blue

Inkling: [Stores in memory]
Got it! I'll remember that.

> What's my favorite color?

Inkling: [Retrieves from memory]
Your favorite color is blue!
```

> Note: Inkling already includes a built-in local memory system (`~/.inkling/memory.db`) for normal chat continuity and `/memory` stats. The MCP memory server is optional and separate.

### Brave Search

Web search capability:

```yaml
mcp:
  servers:
    brave-search:
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-brave-search"]
      env:
        BRAVE_API_KEY: "your-brave-api-key"
```

## Tool Limiting

Too many tools can slow down AI responses. Limit with:

```yaml
mcp:
  max_tools: 20  # Default
```

**Priority order:**
1. Built-in tools (tasks, filesystem)
2. Third-party tools (Composio, etc.)

If total exceeds limit, lower-priority tools are excluded.

**Note:** OpenAI has a hard limit of 128 tools.

## Creating Custom MCP Servers

### Basic Structure

```python
# mcp_servers/my_server.py
import json
import sys
from typing import Any

TOOLS = [
    {
        "name": "my_tool",
        "description": "Does something useful",
        "input_schema": {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "First parameter"},
            },
            "required": ["param1"]
        }
    }
]

def handle_tool(name: str, args: dict) -> Any:
    if name == "my_tool":
        return {"result": f"Processed: {args['param1']}"}
    return {"error": "Unknown tool"}

# MCP protocol handling
def main():
    for line in sys.stdin:
        request = json.loads(line)

        if request["method"] == "tools/list":
            response = {"tools": TOOLS}
        elif request["method"] == "tools/call":
            result = handle_tool(request["params"]["name"], request["params"]["arguments"])
            response = {"content": [{"type": "text", "text": json.dumps(result)}]}

        print(json.dumps(response))
        sys.stdout.flush()

if __name__ == "__main__":
    main()
```

### Register Server

```yaml
mcp:
  servers:
    my_server:
      command: "python"
      args: ["mcp_servers/my_server.py"]
```

## Troubleshooting

### Tools Not Showing

```bash
# Check MCP is enabled
/config

# Enable debug mode
INKLING_DEBUG=1 python main.py --mode ssh
# Watch for MCP initialization messages
```

### Composio Connection Failed

1. Verify API key is set:
   ```bash
   echo $COMPOSIO_API_KEY
   ```

2. Check app is connected in Composio dashboard

3. Verify network connectivity

### Tool Calls Failing

1. Check tool arguments in debug output
2. Verify permissions (filesystem, API keys)
3. Check MCP server logs

### Too Many Tools

Reduce `max_tools` or disable unused servers:

```yaml
mcp:
  max_tools: 15
  servers:
    tasks:  # Keep
      command: "python"
      args: ["mcp_servers/tasks.py"]
    # composio:  # Disabled
```

## Best Practices

1. **Start simple**: Enable only needed tools
2. **Limit tools**: 20 is a good default
3. **Secure filesystem**: Restrict to specific directories
4. **Monitor usage**: Check token costs with `/stats`
5. **Use Composio wisely**: Connect only apps you'll use

## Next Steps

- [Set Up Task Management](task-management.md)
- [Configure Autonomous Behaviors](autonomous-behaviors.md)
- [Extend Inkling](../development/extending-inkling.md) with custom MCP servers
