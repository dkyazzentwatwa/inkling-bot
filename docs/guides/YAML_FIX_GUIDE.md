# YAML Configuration Fix Guide

## Problem

You're seeing this error:
```
yaml.parser.ParserError: while parsing a block mapping
  in "<unicode string>", line 97, column 5:
        tasks:
        ^
expected <block end>, but found '<block mapping start>'
  in "<unicode string>", line 106, column 6:
         composio:
         ^
```

## Cause

There's a YAML indentation error in your `config.local.yml` file. The `composio:` section needs to be at the same indentation level as `tasks:` under the `servers:` key.

## Solution

### Option 1: Use the Example File (Recommended)

1. On the Pi, backup your current config:
   ```bash
   cd ~/cypher/inkling-bot
   cp config.local.yml config.local.yml.backup
   ```

2. Copy the example file:
   ```bash
   cp config.local.yml.example config.local.yml
   ```

3. Edit with nano:
   ```bash
   nano config.local.yml
   ```

4. Make sure it looks like this (PAY ATTENTION TO INDENTATION):
   ```yaml
   # MCP Servers (Model Context Protocol)
   mcp:
     enabled: true
     servers:
       # Task Management (built-in)
       tasks:
         command: "python"
         args: ["mcp_servers/tasks.py"]

       # Composio MCP Gateway (500+ app integrations)
       composio:
         transport: "http"
         url: "https://backend.composio.dev/v3/mcp"
         headers:
           x-api-key: "${COMPOSIO_API_KEY}"
   ```

### Option 2: Fix Existing File

1. Edit your config.local.yml:
   ```bash
   cd ~/cypher/inkling-bot
   nano config.local.yml
   ```

2. Find the `mcp:` section (around line 90-110)

3. Make sure indentation is EXACTLY like this:
   - `mcp:` at column 0
   - `enabled:` and `servers:` indented 2 spaces
   - `tasks:` and `composio:` indented 4 spaces (under `servers:`)
   - Properties of tasks/composio indented 6 spaces

4. **CRITICAL**: Use SPACES, not tabs! YAML doesn't allow tabs.

5. Save and exit (Ctrl+O, Enter, Ctrl+X)

### Option 3: Comment Out Composio (Quick Fix)

If you don't need Composio right now:

1. Edit config.local.yml:
   ```bash
   nano config.local.yml
   ```

2. Add `#` in front of the composio section:
   ```yaml
   # composio:
   #   transport: "http"
   #   url: "https://backend.composio.dev/v3/mcp"
   #   headers:
   #     x-api-key: "${COMPOSIO_API_KEY}"
   ```

3. Save and try running again

## Verify the Fix

After fixing, validate the YAML:

```bash
python3 -c "import yaml; yaml.safe_load(open('config.local.yml'))"
```

If no error, the YAML is valid!

## Common Issues

**Mixing tabs and spaces**: YAML requires spaces only
- Fix: Use `cat -A config.local.yml` to see tabs (shown as `^I`)
- Replace tabs with spaces

**Wrong indentation level**: composio must align with tasks
- Both should be 4 spaces under `servers:`

**Missing colons**: Every key needs a colon
- `composio:` not `composio`

**Long URLs breaking across lines**: Keep URL on one line
- If your URL is very long, that's fine - just keep it on one line

## Notes

- The file browser feature works WITHOUT Composio - it's already enabled
- Composio is optional and only needed for 500+ app integrations
- You can test the file browser first, then enable Composio later
