# Composio MCP Integration Guide

This guide explains how to integrate Composio with Inkling to add powerful external tool capabilities like Google Calendar, GitHub, Slack, and 500+ other apps.

## What is Composio?

[Composio](https://composio.dev) is an agentic integration platform that provides a unified MCP (Model Context Protocol) endpoint to access 500+ managed integrations. Instead of setting up individual MCP servers for each service, Composio acts as a gateway providing access to all tools through a single endpoint.

## Why Use Composio with Inkling?

Composio enables your AI companion to:

- **Sync with Google Calendar** - Create tasks from meetings, get reminders
- **Manage GitHub Issues** - Create, update, and close issues automatically
- **Send Slack/Discord Notifications** - Share task completions with your team
- **Integrate with Todoist/Linear** - Bi-directional task syncing
- **Execute code** - Run scripts and automation
- **Browse the web** - Research tasks and gather information
- **And 500+ more integrations**

## Prerequisites

1. **Composio Account**
   - Sign up at [composio.dev](https://composio.dev)
   - Get your API key from Settings

2. **MCP Support Enabled**
   - Composio provides MCP endpoints (no additional software needed)

## Setup Instructions

### 1. Get Your Composio API Key

```bash
# Set environment variable
export COMPOSIO_API_KEY=your_api_key_here

# Or add to your shell profile
echo 'export COMPOSIO_API_KEY=your_api_key_here' >> ~/.bashrc
source ~/.bashrc
```

### 2. Enable Composio in Inkling Config

Edit `config.local.yml`:

```yaml
mcp:
  enabled: true
  servers:
    # Built-in task manager
    tasks:
      command: "python"
      args: ["mcp_servers/tasks.py"]

    # Composio MCP Gateway
    composio:
      transport: "http"
      url: "https://backend.composio.dev/v3/mcp"
      headers:
        x-api-key: "${COMPOSIO_API_KEY}"
```

### 3. Install Composio Apps

Visit your [Composio dashboard](https://app.composio.dev) and connect the apps you want to use:

**Recommended for Task Management:**
- **Google Calendar** - Sync tasks with calendar events
- **GitHub** - Create issues from tasks
- **Slack** - Task completion notifications
- **Todoist** - Bi-directional task sync
- **Linear** - Project management integration
- **Notion** - Documentation integration

### 4. Test the Integration

Start Inkling:

```bash
source .venv/bin/activate
python main.py --mode ssh
```

**Test commands:**

```
# Test Composio connection
Ask: "What tools do you have access to?"

# Create a calendar event
Ask: "Create a calendar event for tomorrow at 2 PM for design review"

# Create a GitHub issue
Ask: "Create a GitHub issue in my repo for fixing the login bug"

# Sync tasks to Todoist
Ask: "Create a Todoist task for my important task"
```

## Multi-Step Workflows

Composio unlocks powerful multi-step orchestrations:

### Example 1: Meeting to Tasks

**User:** "Check my calendar for tomorrow and create tasks for each meeting"

**AI Workflow:**
```
Round 1: composio_google_calendar_list(date="tomorrow")
         → Returns: 3 meetings

Round 2: task_create(title="Prepare for standup")
Round 3: task_create(title="Design review prep")
Round 4: task_create(title="1-on-1 with manager")

Response: "Added 3 tasks from your calendar!"
```

### Example 2: Task to Issue

**User:** "Create a GitHub issue for my urgent task and link them"

**AI Workflow:**
```
Round 1: task_list(status="pending", priority="urgent")
         → Returns: "Fix production bug"

Round 2: composio_github_create_issue(
           title="Fix production bug",
           body="Created from Inkling task",
           labels=["bug", "urgent"]
         )
         → Returns: Issue #42 URL

Round 3: task_update(
           task_id="...",
           description="GitHub Issue #42: https://..."
         )

Response: "Created issue #42 and linked to your task!"
```

### Example 3: Research and Summarize

**User:** "Research React Server Components and create a task with notes"

**AI Workflow:**
```
Round 1: composio_browser_search(query="React Server Components 2026")
         → Returns: Latest documentation

Round 2: task_create(
           title="Learn React Server Components",
           description="[Summary of findings]",
           tags=["learning", "react"]
         )

Response: "Created task with research notes!"
```

## Available Composio Tools

When Composio is enabled, the AI automatically discovers and uses relevant tools:

### Calendar & Scheduling
- Google Calendar
- Outlook Calendar
- Calendly

### Project Management
- GitHub Issues
- Linear
- Jira
- Asana
- Monday.com
- Trello

### Communication
- Slack
- Discord
- Microsoft Teams
- Gmail

### Task Management
- Todoist
- TickTick
- Things
- Any.do

### Documentation
- Notion
- Confluence
- Google Docs

### Code & Development
- GitHub (repos, PRs, issues)
- GitLab
- Bitbucket

### And 500+ More Apps

See full list: [https://composio.dev/tools](https://composio.dev/tools)

## Authentication Flow

Composio handles authentication automatically:

1. **First Use**: When you ask to use a tool (e.g., "Create a calendar event")
2. **Auth Prompt**: Composio returns an authentication link
3. **Connect**: Click the link to grant access to your account
4. **Cached**: Future requests use the saved connection

## Configuration Tips

### Limit Tool Access

To prevent the AI from accessing all 500+ tools, you can specify which apps to enable:

```yaml
composio:
  transport: "http"
  url: "https://backend.composio.dev/v3/mcp"
  headers:
    x-api-key: "${COMPOSIO_API_KEY}"
  # Optional: Limit to specific apps
  allowed_apps:
    - github
    - google_calendar
    - slack
    - todoist
```

### Custom Tool Routing

Composio can route tools based on context:

```python
# In your config or code, specify tool preferences
tool_preferences = {
    "calendar": "google_calendar",  # Prefer Google Calendar
    "tasks": "todoist",             # Prefer Todoist for external tasks
    "code": "github",               # Prefer GitHub for code
}
```

## Example Use Cases

### 1. Calendar-Driven Task Management

```
You: "What's on my calendar today?"
AI: [Uses Composio to check calendar]
    "You have 3 meetings today. Should I create prep tasks?"

You: "Yes"
AI: [Creates 3 tasks with details from calendar events]
```

### 2. Automated Issue Tracking

```
You: "Track this bug in GitHub"
AI: [Creates GitHub issue, adds to your tasks]
    "Created issue #42 and linked to your task!"
```

### 3. Team Notifications

```
When you complete an important task:
AI: [Posts to Slack #wins channel]
    "🎉 Just completed: Fix production bug (+40 XP)"
```

### 4. Research Automation

```
You: "Research best practices for React hooks"
AI: [Searches web, summarizes findings, creates task with notes]
```

## Troubleshooting

### Issue: "Composio tools not loading"

**Check:**
1. Is `COMPOSIO_API_KEY` set correctly?
   ```bash
   echo $COMPOSIO_API_KEY
   ```

2. Is MCP enabled in config?
   ```bash
   grep "enabled: true" config.local.yml
   ```

3. Check MCP logs:
   ```bash
   INKLING_DEBUG=1 python main.py --mode ssh
   ```

### Issue: "Authentication failed"

**Solution:**
- Visit Composio dashboard
- Re-authenticate the app
- Check app permissions

### Issue: "Too many tools, AI is confused"

**Solution:**
- Limit `allowed_apps` in config
- Be specific in prompts ("Use Google Calendar to...")
- Use tool routing preferences

## Best Practices

### 1. Start Small

Begin with 2-3 apps:
- Google Calendar
- GitHub
- Slack

### 2. Use Descriptive Prompts

❌ **Bad:** "Create an event"
✅ **Good:** "Create a Google Calendar event for tomorrow at 2 PM"

### 3. Leverage Multi-Step Workflows

Instead of manual steps:
```
❌ Create calendar event → manually create task → manually notify team

✅ "Create a calendar event, add a task, and notify the team in Slack"
```

### 4. Set Up Automation

Create custom behaviors:
```python
# Example: Auto-create tasks from calendar
if event.title.startswith("[Task]"):
    task_manager.create_task(
        title=event.title.replace("[Task] ", ""),
        due_date=event.start_time
    )
```

## Security Considerations

1. **API Key Protection**: Never commit `COMPOSIO_API_KEY` to git
2. **App Permissions**: Review what each app can access
3. **Rate Limits**: Composio enforces rate limits per API key
4. **Data Privacy**: Data flows through Composio's servers

## Cost

Composio offers:
- **Free Tier**: 1,000 tool calls/month
- **Pro**: $29/month - 10,000 calls
- **Enterprise**: Custom pricing

Check current pricing: [https://composio.dev/pricing](https://composio.dev/pricing)

## Advanced: Custom MCP Servers

You can combine Composio with custom MCP servers:

```yaml
mcp:
  enabled: true
  servers:
    # Built-in task manager
    tasks:
      command: "python"
      args: ["mcp_servers/tasks.py"]

    # Composio for external apps
    composio:
      transport: "http"
      url: "https://backend.composio.dev/v3/mcp"
      headers:
        x-api-key: "${COMPOSIO_API_KEY}"

    # Custom file system access
    filesystem:
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/projects"]

    # Custom web fetch
    fetch:
      command: "uvx"
      args: ["mcp-server-fetch"]
```

The AI will intelligently route between local tools (tasks, filesystem) and external tools (Composio).

## Next Steps

1. **Enable Composio** in `config.local.yml`
2. **Connect 2-3 apps** in Composio dashboard
3. **Test workflows** with simple commands
4. **Build automation** with multi-step orchestrations
5. **Create custom behaviors** for your specific needs

---

## Resources

- [Composio Documentation](https://docs.composio.dev)
- [MCP Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [Composio Tools List](https://composio.dev/tools)
- [Composio Blog: What is MCP](https://composio.dev/blog/what-is-model-context-protocol-mcp-explained)
- [Best MCP Gateways 2026](https://composio.dev/blog/best-mcp-gateway-for-developers)

---

**Created:** 2026-02-03
**Status:** Ready to use
**Branch:** `claude/task-manager-ai-companion-LqyIU`
