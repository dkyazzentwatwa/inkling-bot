# Smart Tool Routing System

## Problem Solved

With 215+ Composio tools available, the old system had a hard limit (20-50 tools) that caused important tools to be excluded even when explicitly requested. Query-based search helped but still hit the artificial cap.

## New Smart Routing System

### Key Features

1. **No Hard Limit for Matched Tools** - If you mention "gmail", ALL Gmail tools are loaded (not just 5)
2. **Soft Limit for General Tools** - Non-matched tools fill up to `max_tools` (default: 30)
3. **Safety Cap** - Only applies hard limit at 100 total tools (prevents AI overload)
4. **Expanded Keywords** - Detects more variations (email/mail/inbox, etc.)

### How It Works

```
User: "check my gmail and calendar"
         ↓
Keyword detection: gmail, email, calendar
         ↓
Search all 215 tools:
  - Find ALL gmail tools (e.g., 15 tools)
  - Find ALL calendar tools (e.g., 12 tools)
         ↓
Assembly:
  Core tools: 3 (tasks, system, filesystem)
  Query-matched: 27 (all gmail + calendar tools)
  Other tools: 30 (fill to soft limit)
         ↓
Total: 60 tools (under safety cap of 100)
         ↓
✅ AI has access to ALL relevant tools!
```

### Comparison

| Scenario | Old System | New System |
|----------|-----------|------------|
| User mentions "gmail" | 5 gmail tools (limited) | ALL gmail tools (15+) |
| User mentions "gmail calendar" | 5 gmail + 5 calendar (10 total) | ALL gmail + ALL calendar (27+ total) |
| Generic query | 20-50 random tools | 30 most relevant tools |
| Safety | Hard limit always | Soft limit, hard cap at 100 |

## Configuration

### config.local.yml

```yaml
mcp:
  enabled: true
  max_tools: 30  # Soft limit for general tools
  # Query-matched tools bypass this limit
  # Hard safety cap at 100 total tools
```

**Recommended values**:
- `20-30`: Conservative (fast, fewer tokens)
- `40-50`: Balanced (good coverage)
- `60+`: Aggressive (maximum coverage, more tokens)

**Note**: Query-matched tools ALWAYS load regardless of this setting!

## Supported Keywords

### Email
- gmail, email, mail, inbox

### Calendar
- calendar, event, meeting, schedule

### Sheets
- sheet, sheets, spreadsheet

### Notes
- notion, note, notes

### GitHub
- github, git, repo, pr, issue

### Slack
- slack, message, chat

### Files
- drive, file, document, doc

## Expected Logs

### With Smart Routing

```
User: "check my gmail"

[MCP] Smart routing detected keywords: gmail, email, mail
[MCP] Smart routing loaded: 48 tools
[MCP]   Core: 3, Query-matched: 15, Other: 30
[Brain] Calling tool: gmail_fetch_emails
```

### Generic Query (No Keywords)

```
User: "help me with something"

[MCP] Loaded 33 tools (soft limit: 30)
```

### Safety Cap Applied

```
User: "check gmail calendar sheets github slack"

[MCP] Smart routing detected keywords: gmail, calendar, sheets, github, slack
[MCP] Safety cap applied: 127 → 100
[MCP]   Core: 3, Query-matched: 67, Other: 30
```

## Benefits

### 1. No More "Tool Not Found" Errors

**Before**:
```
User: "check my gmail"
AI: "I don't have access to Gmail tools" ❌
```

**After**:
```
User: "check my gmail"
AI: *calls gmail_fetch_emails* ✅
```

### 2. Multi-Service Queries Work

**Before** (limited to 20 tools):
```
User: "check gmail and calendar"
Result: 5 gmail + 5 calendar + 10 other = 20 tools
Missing: Most gmail/calendar tools ❌
```

**After** (smart routing):
```
User: "check gmail and calendar"
Result: 3 core + 15 gmail + 12 calendar + 30 other = 60 tools
Missing: Nothing! ✅
```

### 3. Token Efficient

- Generic queries: Only 30 tools (fewer tokens)
- Specific queries: Load what's needed (efficient)
- No wasted tokens on irrelevant tools

### 4. AI Model Compatibility

- Safety cap (100 tools) prevents overwhelming AI
- Most queries: 30-60 tools (well within limits)
- OpenAI limit: 128 tools (we stay under)
- Anthropic: No hard limit (we're very safe)

## Testing

### Test 1: Gmail Only

```bash
python main.py --mode ssh

> check my gmail
```

**Expected**:
```
[MCP] Smart routing detected keywords: gmail, email, mail
[MCP] Smart routing loaded: 48 tools
[MCP]   Core: 3, Query-matched: 15, Other: 30
```

### Test 2: Multiple Services

```
> check my gmail and calendar and sheets
```

**Expected**:
```
[MCP] Smart routing detected keywords: calendar, gmail, sheets
[MCP] Smart routing loaded: 75 tools
[MCP]   Core: 3, Query-matched: 42, Other: 30
```

### Test 3: Generic Query

```
> help me think about something
```

**Expected**:
```
[MCP] Loaded 33 tools (soft limit: 30)
```

## Troubleshooting

**"Still not finding my tool"**

1. Check if keyword is in the list (line ~468 in mcp_client.py)
2. Add your keyword:
   ```python
   keywords = [
       "gmail", "email", "mail", "inbox",
       "calendar", "event", "meeting",
       "yourservice",  # Add here
   ]
   ```

**"Too many tools, AI is slow"**

1. Lower `max_tools` to 20-25 (reduces "other" tools)
2. Query-matched tools still load (important ones)

**"Not loading enough tools"**

1. Increase `max_tools` to 40-50
2. Or use more specific keywords in your query

## Future Enhancements

1. **Semantic Search** - Use embeddings to match similar concepts
2. **Learning** - Track which tools are used together
3. **User Preferences** - Remember frequently used tools
4. **Context Awareness** - Consider conversation history

---

**Summary**: Smart routing gives you NO LIMIT on relevant tools while keeping the system fast and efficient. Query "check my gmail" and get ALL 15 Gmail tools, not just 5! 🎉
