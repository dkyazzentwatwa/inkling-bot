# Web Mode Commands

The web UI now supports all commands available in SSH mode. Commands can be executed in two ways:

## Using Command Buttons

Click any button in the command palette to execute a command instantly:

### Info Commands
- **Help** - Show all available commands
- **Level** - View XP, level, and progression
- **Stats** - Check token usage statistics
- **History** - See recent conversation messages

### Personality Commands
- **Mood** - Check current mood and intensity
- **Energy** - View energy level with visual bar
- **Traits** - Display all personality traits

### Social Commands
- **Fish** - Fetch a random dream from the Night Pool
- **Queue** - Check offline request queue status

### System Commands
- **System** - View CPU, memory, and temperature
- **Config** - See AI provider configuration
- **Identity** - Show device public key
- **Faces** - List all available face expressions
- **Refresh** - Force display refresh
- **Clear** - Clear conversation history

## Using Chat Input

Type commands directly in the chat input (with or without `/`):

```
/help
/mood
/level
/fish
```

## Commands Requiring Arguments

Some commands need additional input:

- `/face <name>` - Test a specific face expression
  ```
  /face happy
  /face thinking
  ```

- `/dream <text>` - Post a dream to the Night Pool
  ```
  /dream The stars look different tonight...
  ```

- `/ask <message>` - Explicit chat command (or just type without /)
  ```
  /ask What's the weather like?
  ```

## Special Cases

### Prestige
The `/prestige` command requires confirmation and is only available in SSH mode:
```bash
python main.py --mode ssh
/prestige
```

### Real-time Updates
The web UI polls for status updates every 5 seconds. Command results are displayed immediately when you click a button or send a command.

## API Access

Commands can also be executed via the API:

```bash
curl -X POST http://localhost:8080/api/command \
  -H "Content-Type: application/json" \
  -d '{"command": "/mood"}'
```

Response format:
```json
{
  "response": "Mood: curious\nIntensity: 75%\nEnergy: 80%",
  "face": "(o.o)",
  "status": "Lvl 5 | Curious | 85%",
  "error": false
}
```

## Troubleshooting

**Command not working?**
- Check if the feature is enabled (some commands require AI or social features)
- Look for error messages in the response
- Try refreshing the page

**Missing buttons?**
- Ensure you're running the latest version
- Check browser console for JavaScript errors
- Try clearing browser cache

**Need help?**
Click the **Help** button or type `/help` to see all available commands.
