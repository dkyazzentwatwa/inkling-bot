# Composio Removed from Default Config

## What Changed

**Composio MCP integration has been removed from the default configuration.**

### Why?

- Not working reliably for all users
- Requires Node.js installation (extra dependency)
- Requires external account setup
- Large tool count (215 tools) caused buffer issues
- Most users don't need Gmail/Calendar integration

### What Still Works (100%)

✅ All background tasks:
- Morning briefing (weather via wttr.in)
- RSS feed digest
- Task reminders
- System health checks
- Nightly backups
- Daily/weekly summaries

✅ Built-in MCP servers:
- Tasks (task management)
- System (curl, df, free, uptime, ps, ping)
- Filesystem (.inkling directory)

✅ Smart tool routing (for any MCP servers you add)

### How to Add Composio (Optional)

If you want Gmail/Calendar integration, you can manually add Composio:

**1. Install Node.js on Pi**:
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

**2. Get your Composio MCP URL** from https://app.composio.dev

**3. Add to config.local.yml**:
```yaml
mcp:
  servers:
    composio:
      command: "npx"
      args:
        - "-y"
        - "mcp-remote"
        - "YOUR_COMPOSIO_MCP_URL_HERE"
      env:
        npm_config_yes: "true"
```

See `docs/OPTIONAL_INTEGRATIONS.md` for full setup guide.

## Files Changed

- `config.local.yml` - Removed Composio server config
- `config.yml` - Updated to show Composio as optional example
- `docs/OPTIONAL_INTEGRATIONS.md` - Updated to emphasize Composio is optional

## Migration

If you were using Composio:

**Option 1**: Continue using it (add config manually from above)  
**Option 2**: Remove it (everything else still works!)

No action needed if you weren't using Composio - everything works as before.
