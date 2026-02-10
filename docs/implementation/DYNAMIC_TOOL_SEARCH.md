# Dynamic Tool Search Feature

## Problem

The original MCP implementation used a **static tool list** limited to `max_tools` (default 20). With 215+ Composio tools available, important tools like Gmail or Calendar could be excluded from the top 20, causing the AI to not use them even when the user explicitly requested.

## Solution

Implemented **query-based dynamic tool search**:

1. User asks: "check my gmail"
2. Brain passes query to MCP client
3. MCP searches all 215 tools for "gmail" keywords
4. Returns: **core tools + gmail tools + other tools** (up to max_tools)
5. AI now has Gmail tools available!

## How It Works

### Tool Selection Strategy

```python
get_tools_for_query(query):
    1. Always include: tasks, system, filesystem (core)
    2. Search query for keywords: gmail, email, calendar, sheets, etc.
    3. Load matching tools (up to 5 per keyword)
    4. Fill remaining slots with other tools
    5. Limit total to max_tools
```

### Example

**User**: "check my gmail"

**Before** (static):
```
[MCP] Limiting tools from 215 to 20
Tools: tasks, system, filesystem, random_tool_1, random_tool_2, ... (no Gmail!)
```

**After** (dynamic):
```
[MCP] Query-based tool selection: 215 → 20
[MCP]   Core: 3, Query-matched: 5 (gmail_*), Other: 12
Tools: tasks, system, filesystem, gmail_fetch, gmail_send, gmail_list, ... ✅
```

## Supported Keywords

Auto-detected in user queries:
- **gmail** / **email** → Gmail tools
- **calendar** → Google Calendar tools
- **sheet** / **sheets** → Google Sheets tools
- **notion** → Notion tools
- **github** → GitHub tools
- **slack** → Slack tools

More keywords can be added in `get_tools_for_query()`.

## Code Changes

### 1. MCPClientManager (`core/mcp_client.py`)

**New methods**:
- `search_tools(query, limit)` - Search all tools by name/description
- `get_tools_for_query(query)` - Dynamic tool selection based on query

**Updated method**:
- `get_tools_for_ai()` - Now deprecated, kept for backward compatibility

### 2. Brain (`core/brain.py`)

**Changed line 801**:
```python
# OLD: Static tool list
tools = self.mcp_client.get_tools_for_ai()

# NEW: Dynamic query-based
tools = self.mcp_client.get_tools_for_query(user_message)
```

## Configuration

No config changes needed! Works automatically.

**Optional**: Increase `max_tools` for more room:
```yaml
mcp:
  max_tools: 30  # Default 20, allows more query-matched tools
```

## Benefits

1. **Lower default max_tools** - Faster for non-tool-heavy queries
2. **Better tool coverage** - Relevant tools always available when needed
3. **Smarter AI** - Gets exactly the tools it needs
4. **No manual prioritization** - System handles it automatically

## Testing

### Test Gmail Tool Search

```bash
python main.py --mode ssh
```

Then:
```
> check my gmail
```

**Expected logs**:
```
[MCP] Query-based tool selection: 215 → 20
[MCP]   Core: 3, Query-matched: 5, Other: 12
[Brain] Calling tool: gmail_fetch_emails
```

### Test Calendar Tool Search

```
> what's on my calendar today?
```

**Expected logs**:
```
[MCP] Query-based tool selection: 215 → 20
[MCP]   Core: 3, Query-matched: 4, Other: 13
[Brain] Calling tool: googlecalendar_events_list
```

## Limitations

1. **Keyword-based**: Only detects pre-defined keywords (gmail, calendar, etc.)
2. **No semantic search**: Doesn't understand "check my inbox" = "gmail"
3. **Fixed keyword list**: Need to manually add new keywords for new tools

## Future Enhancements

1. **Semantic search**: Use embeddings to match query → tools
2. **Learning**: Track which tools are used together
3. **User preferences**: Remember frequently used tools
4. **Multi-keyword**: Better handling of "gmail and calendar"

## Troubleshooting

**AI still not using tools?**

1. Check keywords: `grep keywords core/mcp_client.py` (line ~460)
2. Check logs: `INKLING_DEBUG=1` to see query-matched count
3. Increase max_tools: `max_tools: 30` in config
4. Verify tool exists: Check if tool appears in "Query-matched" count

**No query-matched tools?**

- Query doesn't contain recognized keywords
- Add keyword to `keywords` list in `get_tools_for_query()`

---

**Summary**: Dynamic tool search ensures relevant tools are always available when needed, solving the "tool limit" problem elegantly. 🎉
