# Remote Claude Code Access via SSH

Connect your Inkling (Pi Zero 2W) to Claude Code running on your MacBook.
This gives Inkling's AI the ability to run terminal commands, read/write files,
and search codebases on your Mac — all through natural conversation.

## How It Works

```
Inkling (Pi Zero 2W)                    MacBook
┌──────────────────┐                    ┌──────────────────────┐
│ Brain / AI       │                    │                      │
│   ↓              │                    │  claude mcp serve    │
│ MCP Client       │───── SSH ─────────→│  (stdio over SSH)    │
│   (stdio)        │  encrypted tunnel  │     ↓                │
│                  │                    │  Bash, Read, Write,  │
│                  │                    │  Edit, Grep, Glob    │
└──────────────────┘                    └──────────────────────┘
```

Inkling's MCP client spawns `ssh` as a subprocess, which connects to your Mac
and runs `claude mcp serve`. SSH pipes stdio back and forth. Claude Code exposes
its built-in tools (Bash, Read, Write, Edit, Grep, Glob, etc.) as MCP tools.
No custom code required on either side.

## Prerequisites

- **MacBook**: Claude Code CLI installed (`claude` command available)
- **Pi Zero 2W**: Inkling running with MCP enabled
- **Network**: Both devices on the same WiFi network
- **macOS**: Remote Login (SSH) enabled in System Settings

## Phase 1: SSH Key Authentication

### Step 1: Enable SSH on Your Mac

1. Open **System Settings** → **General** → **Sharing**
2. Enable **Remote Login**
3. Note your Mac's local hostname (e.g., `YourName-MacBook.local`)
   - Or find your IP: `ipconfig getifaddr en0` on the Mac

### Step 2: Generate SSH Key on the Pi

On your Pi (or in this dev environment):

```bash
# Generate a dedicated Ed25519 key for Inkling
ssh-keygen -t ed25519 -C "inkling-bot" -f ~/.ssh/inkling_macbook -N ""
```

This creates:
- `~/.ssh/inkling_macbook` — private key (stays on Pi, never shared)
- `~/.ssh/inkling_macbook.pub` — public key (goes to your Mac)

### Step 3: Copy the Public Key to Your Mac

```bash
# Option A: ssh-copy-id (easiest)
ssh-copy-id -i ~/.ssh/inkling_macbook.pub youruser@YourMac.local

# Option B: Manual copy
# On the Pi, display the public key:
cat ~/.ssh/inkling_macbook.pub
# On the Mac, append it to ~/.ssh/authorized_keys:
# echo "PASTE_KEY_HERE" >> ~/.ssh/authorized_keys
```

### Step 4: Test the Connection

```bash
# Should connect without a password prompt
ssh -i ~/.ssh/inkling_macbook -o BatchMode=yes youruser@YourMac.local echo "Connected!"
```

If it prints "Connected!" — you're ready.

### Step 5: Configure SSH Client on Pi

Add to `~/.ssh/config` on the Pi for cleaner configuration:

```
Host macbook
    HostName YourMac.local
    User youruser
    IdentityFile ~/.ssh/inkling_macbook
    BatchMode yes
    StrictHostKeyChecking accept-new
    ServerAliveInterval 30
    ServerAliveCountMax 3
    ConnectTimeout 10
```

Now `ssh macbook` works without specifying all the flags every time.

## Phase 1: MCP Server Configuration

### Add to `config.local.yml`

```yaml
mcp:
  enabled: true
  max_tools: 20
  servers:
    # ... existing servers (tasks, system, etc.) ...

    # Remote Claude Code on MacBook
    # Gives Inkling access to Bash, Read, Write, Edit, Grep, Glob
    # on your Mac via SSH tunnel
    macbook-claude:
      command: "ssh"
      args:
        - "macbook"                # SSH host alias (from ~/.ssh/config)
        - "claude"                 # Claude Code CLI
        - "mcp"                    # MCP subcommand
        - "serve"                  # Start MCP server mode
```

#### With a Specific Working Directory

To point Claude Code at a specific project:

```yaml
    macbook-claude:
      command: "ssh"
      args:
        - "macbook"
        - "claude"
        - "mcp"
        - "serve"
        - "--workdir"
        - "/Users/youruser/projects/my-project"
```

#### Without SSH Config (Inline)

If you prefer not to use `~/.ssh/config`:

```yaml
    macbook-claude:
      command: "ssh"
      args:
        - "-i"
        - "/root/.ssh/inkling_macbook"   # Path to private key
        - "-o"
        - "BatchMode=yes"
        - "-o"
        - "StrictHostKeyChecking=accept-new"
        - "-o"
        - "ConnectTimeout=10"
        - "youruser@YourMac.local"
        - "claude"
        - "mcp"
        - "serve"
```

## Testing

### Manual Test (Before Configuring Inkling)

```bash
# This should output JSON-RPC responses from Claude Code
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}' | \
  ssh macbook claude mcp serve
```

### In Inkling

Start Inkling and try these prompts:

```
"List the files in my Mac's home directory"
"What's in my Mac's ~/projects folder?"
"Run 'git status' on my Mac in ~/projects/my-app"
"Read the README.md in my Mac project"
"Search for TODO comments in my Mac codebase"
```

The AI will use the `macbook-claude__Bash`, `macbook-claude__Read`,
`macbook-claude__Grep` (etc.) tools automatically.

## SSH Hardening

### Restrict the SSH Key to Claude Code Only

On your **Mac**, edit `~/.ssh/authorized_keys` and add a `command=` prefix
to the Inkling public key. This ensures the key can ONLY run `claude mcp serve`
and nothing else:

```
command="claude mcp serve",no-port-forwarding,no-X11-forwarding,no-agent-forwarding ssh-ed25519 AAAA...your_key... inkling-bot
```

With this restriction:
- The key can only execute `claude mcp serve`
- No port forwarding, X11 forwarding, or agent forwarding
- Even if the Pi is compromised, the attacker can only talk to Claude Code's
  MCP protocol — they cannot get a shell

**Important**: If you use `--workdir`, include it in the forced command:
```
command="claude mcp serve --workdir /Users/youruser/projects",no-port-forwarding,no-X11-forwarding,no-agent-forwarding ssh-ed25519 AAAA...your_key... inkling-bot
```

### Create a Dedicated macOS User (Optional, Extra Security)

For maximum isolation, create a separate macOS user for Inkling:

```bash
# On your Mac (requires admin)
sudo dscl . -create /Users/inkling
sudo dscl . -create /Users/inkling UserShell /bin/bash
sudo dscl . -create /Users/inkling RealName "Inkling Bot"
sudo dscl . -create /Users/inkling UniqueID 599
sudo dscl . -create /Users/inkling PrimaryGroupID 20
sudo dscl . -create /Users/inkling NFSHomeDirectory /Users/inkling
sudo mkdir -p /Users/inkling/.ssh
sudo cp ~/.ssh/authorized_keys /Users/inkling/.ssh/
sudo chown -R inkling:staff /Users/inkling
```

Then update your SSH config to use `User inkling` and grant that user
read access to your project directories.

### Firewall: Limit SSH to Pi's IP Only

On your Mac, restrict SSH to only accept connections from your Pi:

```bash
# Find your Pi's IP
# On Pi: hostname -I

# On Mac: Add pf firewall rule
echo "pass in on en0 proto tcp from PI_IP_HERE to any port 22" | \
  sudo pfctl -ef -
```

Or use the macOS firewall UI to restrict Remote Login to specific users.

## Exposed Tools

When `claude mcp serve` connects, Inkling gains access to these tools
(prefixed with `macbook-claude__`):

| Tool | What It Does |
|------|-------------|
| `Bash` | Run any terminal command on your Mac |
| `Read` | Read file contents |
| `Write` | Create or overwrite files |
| `Edit` | Make targeted edits to files |
| `Grep` | Search file contents with regex |
| `Glob` | Find files by name pattern |
| `LS` | List directory contents |

**Note**: Claude Code's MCP serve does NOT pass through other MCP servers
configured on your Mac. You only get the built-in tools listed above.

## Troubleshooting

### "Connection refused"
- Ensure Remote Login is enabled on your Mac (System Settings → Sharing)
- Check your Mac's firewall isn't blocking SSH
- Verify the hostname: `ping YourMac.local` from the Pi

### "Permission denied (publickey)"
- Verify the key was copied: `ssh -vvv macbook` shows auth attempts
- Check `~/.ssh/authorized_keys` permissions on Mac: `chmod 600`
- Check `~/.ssh` directory permissions on Mac: `chmod 700`

### "claude: command not found"
- Claude Code may not be in the SSH PATH
- Use full path: replace `"claude"` with `"/usr/local/bin/claude"` in config
- Or add to Mac's `~/.bashrc`: `export PATH="$PATH:/usr/local/bin"`

### MCP timeout / no response
- Test manually first: `ssh macbook claude mcp serve`
- Check Claude Code is installed and working on the Mac: `claude --version`
- Increase Inkling's MCP timeout if your network is slow

### SSH connection drops
- `ServerAliveInterval 30` in SSH config sends keepalives every 30s
- `ServerAliveCountMax 3` disconnects after 90s of no response
- If WiFi is unreliable, Inkling will show MCP errors but recover on next request

## What This Does NOT Give You

- **No MCP passthrough**: Other MCP servers on your Mac (GitHub, memory, etc.)
  are not accessible through this connection
- **No session sharing**: You can't see or continue your Mac's Claude Code
  conversations from Inkling
- **No file watching**: Changes happen on-demand, not in real-time

For MCP servers that support HTTP transport, configure them directly on Inkling
instead of going through the Mac. For stdio-only MCP servers on your Mac, you
can bridge them individually (see "Adding More Mac MCP Servers" below).

## Adding More Mac MCP Servers (Phase 2)

You can bridge additional MCP servers from your Mac by adding separate SSH entries:

```yaml
mcp:
  servers:
    # Claude Code tools
    macbook-claude:
      command: "ssh"
      args: ["macbook", "claude", "mcp", "serve"]

    # GitHub MCP server (runs on Mac, accessed via SSH)
    macbook-github:
      command: "ssh"
      args: ["macbook", "npx", "-y", "@modelcontextprotocol/server-github"]
      env:
        GITHUB_PERSONAL_ACCESS_TOKEN: "your-token"

    # Memory MCP server (runs on Mac, accessed via SSH)
    macbook-memory:
      command: "ssh"
      args: ["macbook", "npx", "-y", "@modelcontextprotocol/server-memory"]
```

Each entry is a separate SSH session. Keep `max_tools` in mind as you add more.
