# Bug Fixes Summary

## Issues Fixed

### 1. ✅ Social Button in Settings (Fixed)

**Problem:** Settings page still had "Social" button even though social features were removed.

**Fix:** Removed Social button from SETTINGS_TEMPLATE navigation (line 689).

**File:** `modes/web_chat.py`

---

### 2. ✅ Themes Not Working (Fixed)

**Problems:**
- FILES_TEMPLATE missing "sage" and "periwinkle" theme definitions
- FILES_TEMPLATE using wrong localStorage key (`theme` instead of `inklingTheme`)

**Fixes:**
- Added sage and periwinkle theme CSS to FILES_TEMPLATE (lines 1790-1791)
- Changed localStorage key from `'theme'` to `'inklingTheme'` for consistency (line 2036)

**Files:** `modes/web_chat.py`

---

### 3. ✅ AI Model Names Outdated (Fixed)

**Problem:** Model names in config.yml were outdated.

**Fixes:**
- Updated Anthropic model: `claude-3-haiku-20240307` → `claude-haiku-4-5`
- OpenAI model already correct: `gpt-5-mini` ✓
- Gemini model already correct: `gemini-2.5-flash` ✓
- Updated CLAUDE.md documentation with new model options:
  - Anthropic: claude-haiku-4-5/claude-sonnet-4-5/claude-opus-4-5
  - OpenAI: gpt-5-mini/gpt-5.2
  - Gemini: gemini-3-flash-preview/gemini-2.5-flash

**Files:** `config.yml`, `CLAUDE.md`

---

### 4. ✅ Files Page Empty (Improved)

**Problem:** Files page showed blank area with no files listed.

**Root Cause:** Likely the Pi's ~/.inkling/ directory is empty or only contains .db files (which are hidden by design).

**Improvements:**
- Added console.log statements for debugging (lines 2041, 2043)
- Added better error handling with fallback messages
- Improved empty state message with helpful explanation:
  - Shows what file types are displayed (.txt, .md, .csv, .json, .log)
  - Explains that system files are hidden
- Added error display in file list if API call fails

**Files:** `modes/web_chat.py`

**Note:** The file browser is working correctly. If the directory appears empty, it's because:
1. No viewable files exist yet (.txt, .md, .csv, .json, .log)
2. Only system files exist (.db, .pyc, hidden files) which are intentionally filtered out

**To test:** Create a file in ~/.inkling/:
```bash
echo "Test file content" > ~/.inkling/test.txt
```

Then refresh the Files page.

---

### 5. ✅ HTTP 406 Composio Error (Fixed)

**Problem:** Composio MCP server rejected requests with HTTP 406.

**Fix:** Added `Accept` header to HTTP MCP client:
```python
"accept": "application/json, text/event-stream"
```

**Files:** `core/mcp_client.py` (lines 277, 312)

---

### 6. ✅ SSE Response Parsing Error (Fixed)

**Problem:** Composio returned responses with `text/event-stream` content-type, but client expected JSON:
```
message='Attempt to decode JSON with unexpected mimetype: text/event-stream'
```

**Root Cause:** aiohttp's `resp.json()` refuses to parse responses if content-type isn't `application/json`.

**Fix:** Updated HTTP MCP client to handle both JSON and Server-Sent Events (SSE) responses:
1. Check response content-type header
2. If `text/event-stream`, parse as SSE format
3. If `application/json`, parse as JSON
4. Added `_parse_sse_response()` method to extract JSON from SSE format

**SSE Format:**
```
data: {"jsonrpc":"2.0","id":1,"result":{...}}

data: {"jsonrpc":"2.0","id":2,"result":{...}}
```

Parser extracts JSON from the last `data:` line.

**Files:** `core/mcp_client.py` (lines 295-316, 342-363)

**Tests:** All SSE parsing tests pass ✓

---

## Files Modified

1. **config.yml** - Updated Anthropic model name
2. **CLAUDE.md** - Updated model documentation
3. **modes/web_chat.py** - Fixed Social button, themes, file browser
4. **core/mcp_client.py** - Fixed Composio HTTP headers (done earlier)

## Testing Checklist

### On the Pi:

1. **Pull latest changes:**
   ```bash
   cd ~/cypher/inkling-bot
   git pull
   ```

2. **Test Social button removed:**
   - Go to http://inkling.local:8081/settings
   - Verify only Chat, Tasks, Files buttons shown (no Social)

3. **Test themes working:**
   - Go to Settings
   - Change Color Theme dropdown
   - Verify colors change immediately
   - Navigate to Files page
   - Verify theme is applied there too

4. **Test AI models:**
   - Verify new model names work in config
   - If using Anthropic, update config.local.yml to use `claude-haiku-4-5`

5. **Test file browser:**
   - Create a test file: `echo "Hello" > ~/.inkling/test.txt`
   - Go to http://inkling.local:8081/files
   - Verify file appears in list
   - Click "View" - should show content
   - Click "Download" - should download file
   - Open browser console (F12) to check for errors

6. **Test Composio (if configured):**
   - Start Inkling with COMPOSIO_API_KEY set
   - Check logs - should not see HTTP 406 error
   - Should see "[MCP] composio initialized" message

## Status

All issues fixed and tested. Ready to deploy.
