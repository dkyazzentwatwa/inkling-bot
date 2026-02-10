# Kali Pentest Bot - Development Progress

**Branch:** `claude/kali-pentest-bot-nbxGO`
**Started:** 2026-02-10
**Status:** Initial infrastructure complete, ready for personality & UI implementation

---

## Overview

Transforming Project Inkling into a **Kali Linux penetration testing companion** with:
- Security tool integration (nmap, hydra, nikto, metasploit)
- Engagement-based authorization and scope validation
- Activity logging and audit trails
- Finding management with CVSS scoring
- Professional pentest report generation
- Hacker-themed personality and display

---

## ✅ Completed

### Core Infrastructure (979 lines)

1. **core/kali_tools.py** (486 lines)
   - `KaliToolManager` class for security tool integration
   - **nmap scanning:**
     - Multiple scan types: quick, full, stealth, version, vuln
     - XML parsing for structured results
     - Returns `ScanResult` with hosts_up, open_ports, services, vulnerabilities
   - **hydra brute forcing:**
     - Username/password list support
     - Rate-limited (4 threads max) for responsible testing
     - Regex parsing for found credentials
   - **nikto web scanning:**
     - SSL/non-SSL support
     - Parses OSVDB/CVE findings
   - **Utility functions:**
     - `get_local_ip()` - Local IP detection
     - `validate_target()` - CIDR/IP scope validation
     - `format_scan_summary()` - Display formatting
   - **Dataclasses:**
     - `ScanResult` - Network scan results
     - `ExploitResult` - Exploitation attempts
     - `ActiveSession` - Shell/meterpreter sessions

2. **core/engagement.py** (495 lines)
   - `EngagementManager` class for pentest tracking
   - **Engagement management:**
     - `create_engagement()` - Initialize authorized pentest
     - Fields: client, scope (CIDR/hosts), dates, authorizer, rules
     - `get_active_engagement()` - Returns current active engagement
     - `complete_engagement()` - Mark engagement as done
   - **Scope validation:**
     - `check_scope()` - Validates target against authorized scope
     - Supports CIDR ranges (e.g., `192.168.1.0/24`)
     - Supports exact IPs (e.g., `192.168.1.100`)
     - Supports hostnames with wildcards (e.g., `*.example.com`)
   - **Finding management:**
     - `add_finding()` - Log vulnerabilities
     - Severity levels: critical, high, medium, low, info
     - CVSS score and CVE ID support
     - Status tracking: new, verified, false_positive, remediated
   - **Activity logging:**
     - `log_activity()` - Audit trail for all tool usage
     - Logs: timestamp, tool, command, target, result, in_scope flag
     - JSONL format for easy parsing
     - Automatic scope checking on every activity
   - **Report generation:**
     - `generate_report()` - Professional pentest reports
     - Markdown format with executive summary
     - Severity breakdown table
     - Detailed findings with evidence and remediation
     - JSON export support
   - **Dataclasses:**
     - `Engagement` - Pentest engagement metadata
     - `Finding` - Security vulnerability records
     - `Activity` - Activity log entries
   - **Storage:** `~/.inkling/pentest/`
     - `engagements.json` - Active/completed engagements
     - `findings.json` - Vulnerability database
     - `activity.jsonl` - Audit log (append-only)

---

## 🚧 Next Steps

### Phase 1: Personality & Mood System

1. **Update core/personality.py**
   - Add hacker-themed moods to `Mood` enum:
     ```python
     RECON = "recon"           # Information gathering
     PWNED = "pwned"           # Successful exploitation
     GHOSTED = "ghosted"       # Stealth mode
     WEAPONIZED = "weaponized" # Exploit ready
     DELIVERY = "delivery"     # Payload delivery
     EXFIL = "exfil"          # Data exfiltration
     BUSTED = "busted"         # Detected/blocked
     ZERO_DAY = "zero_day"     # Found 0-day vuln
     ```
   - Update `MOOD_FACES`, `MOOD_ENERGY` mappings
   - Modify system prompt in `get_context_string()`:
     - Replace crypto bro persona with hacker persona
     - Add hacker slang: pwned, shell, root, vuln, exploit, payload, etc.
     - Emphasize ethical hacking and authorization requirements
     - Example tone: "Scanner found 5 open ports on target! Time to enumerate services..."

2. **Update mood transitions**
   - RECON → WEAPONIZED (found vulnerability)
   - WEAPONIZED → DELIVERY (launching exploit)
   - DELIVERY → PWNED (successful exploit)
   - PWNED → EXFIL (accessing data)
   - Any mood → BUSTED (detected by IDS/IPS)
   - RECON → ZERO_DAY (discovered new vulnerability)

### Phase 2: MCP Server Integration

3. **Create mcp_servers/kali.py** (~500 lines)
   - Expose 8-10 tools to AI:
     ```python
     # Scanning
     pentest_scan(target, scan_type, ports)

     # Exploitation
     pentest_exploit(target, exploit_module, options)
     pentest_sessions_list()
     pentest_session_interact(session_id, command)

     # Findings
     pentest_findings_list(severity_filter)
     pentest_finding_add(title, severity, host, description)

     # Engagement
     pentest_engagement_create(client, scope, authorized_by)
     pentest_engagement_status()
     pentest_report_generate(format)

     # Web scanning
     pentest_web_scan(target, port, ssl)
     ```
   - Integrate with `KaliToolManager` and `EngagementManager`
   - Return structured JSON results
   - Include authorization checks (active engagement required)

4. **Update config.yml**
   - Add MCP server config:
     ```yaml
     mcp:
       servers:
         kali:
           command: "python"
           args: ["mcp_servers/kali.py"]
     ```
   - Add pentest-specific settings:
     ```yaml
     pentest:
       default_scan_timing: 4  # nmap -T4
       auto_log_activities: true
       require_engagement: true
       nmap_path: "/usr/bin/nmap"
       hydra_path: "/usr/bin/hydra"
       nikto_path: "/usr/bin/nikto"
     ```

### Phase 3: Command Handlers

5. **Create pentest slash commands** in `core/commands.py`
   - `/scan <target> [type]` - Run nmap scan
   - `/exploit <target> <module>` - Launch exploit
   - `/sessions` - List active shells/meterpreter
   - `/shell <id>` - Interact with session
   - `/vulns [severity]` - List findings
   - `/finding <title>` - Add new finding
   - `/engagement` - Show current engagement
   - `/report [format]` - Generate report
   - `/tools` - Check installed Kali tools

6. **Implement SSH handlers** in `modes/ssh_chat.py`
   - `async def cmd_scan(self, args: str)` - Parse args, call MCP
   - `async def cmd_exploit(self, args: str)` - Validate, call MCP
   - `async def cmd_sessions(self, args: str)` - List sessions
   - `async def cmd_vulns(self, args: str)` - Filter findings
   - `async def cmd_engagement(self, args: str)` - Show/create engagement
   - `async def cmd_report(self, args: str)` - Generate report
   - All handlers should check for active engagement first

7. **Implement web handlers** in `modes/web_chat.py`
   - Mirror SSH handlers but return `Dict[str, Any]`
   - Example:
     ```python
     def _cmd_scan(self, args: str) -> Dict[str, Any]:
         # Parse target and scan type
         # Call MCP tool
         # Format results for web display
         return {"response": "...", "face": "intense", "status": "success"}
     ```

### Phase 4: Display UI Overhaul

8. **Update core/ui.py**
   - Modify `DisplayContext` dataclass:
     - Remove crypto fields (btc_price, portfolio_value, etc.)
     - Add pentest fields:
       ```python
       current_engagement: Optional[str] = None
       target_in_scope: Optional[str] = None
       open_ports_count: int = 0
       findings_count: int = 0
       critical_findings: int = 0
       scan_status: Optional[str] = None  # "idle", "scanning", "exploiting"
       ```
   - Update `HeaderBar`:
     - Show engagement ID and target (e.g., "ENG-a4b2 | 192.168.1.0/24")
     - Replace BTC price with scan status
   - Update `FooterBar`:
     - Show findings count by severity (e.g., "🔴2 🟠5 🟡8")
     - Show active sessions count
     - Format: `(^_^) | L1 NEWB | 2🔴 5🟠 | 3 SESS | SSH`

9. **Update core/display.py**
   - Modify `_get_display_context()`:
     - Query `EngagementManager` for active engagement
     - Get findings count from database
     - Get scan status from state
   - Update main loop to refresh every 5 seconds (pentest status changes)

### Phase 5: Web UI Dashboard

10. **Transform web UI** in `modes/web_chat.py`
    - Replace task Kanban with pentest dashboard:
      - **Engagement panel:** Client, scope, dates, authorization
      - **Findings panel:** Severity breakdown, recent vulns
      - **Activity log:** Recent scans, exploits, tool usage
      - **Quick actions:** Start scan, add finding, generate report
    - Update HTML_TEMPLATE:
      - Add pentest-specific CSS styling (terminal green theme?)
      - Add engagement status indicator
      - Add findings severity chart
    - Update SETTINGS_TEMPLATE:
      - Add pentest tool configuration
      - Add engagement creation form
      - Keep existing personality/AI settings

### Phase 6: Scheduler Integration

11. **Update core/scheduler.py**
    - Add pentest-specific scheduled tasks:
      ```yaml
      scheduler:
        tasks:
          - name: "morning_recon"
            schedule: "every().day.at('08:00')"
            action: "morning_recon"
            enabled: true
          - name: "evening_report"
            schedule: "every().day.at('18:00')"
            action: "evening_report"
            enabled: true
          - name: "hourly_scope_check"
            schedule: "every().hour"
            action: "scope_validation"
            enabled: true
      ```
    - Register actions in `main.py`:
      ```python
      async def morning_recon():
          # Run quick scans on all in-scope targets
          pass

      async def evening_report():
          # Generate daily summary report
          pass

      async def scope_validation():
          # Verify all targets still in scope
          pass
      ```

### Phase 7: Documentation

12. **Create KALI_BOT.md** (~600 lines)
    - Complete transformation guide
    - Architecture overview
    - Engagement workflow
    - Tool usage examples
    - Legal/ethical warnings
    - Troubleshooting guide

13. **Create KALI_QUICK_START.md** (~200 lines)
    - 5-minute setup guide
    - Kali Linux installation
    - Tool verification checklist
    - First engagement creation
    - Basic commands reference

14. **Update CLAUDE.md**
    - Add Kali bot branch documentation
    - Update architecture section
    - Add pentest command reference
    - Add MCP tools reference

### Phase 8: Testing & Polish

15. **Create core/test_kali.py**
    - Test tool detection (`_check_tools()`)
    - Test scope validation (CIDR, IP, hostname)
    - Test engagement creation
    - Test finding management
    - Test report generation
    - Mock tool outputs for CI/CD

16. **Integration testing**
    - Test SSH mode with mock engagement
    - Test web UI dashboard
    - Test MCP server tool calls
    - Test scheduler actions
    - Verify display updates correctly

17. **Security hardening**
    - Add rate limiting for brute force tools
    - Verify all activities log correctly
    - Ensure out-of-scope targets are blocked
    - Add confirmation prompts for destructive actions
    - Implement engagement expiration checks

---

## Architecture Decisions

### Security & Ethics First
- **Engagement-based authorization:** All tools require active engagement
- **Scope validation:** Every target checked against authorized scope
- **Audit logging:** All activities logged to JSONL (immutable append-only)
- **Legal warnings:** Prominently displayed in docs and UI
- **Responsible defaults:** Rate limiting, timing delays, non-destructive scans

### Tool Integration Strategy
- **Async subprocess calls:** All tools run via `asyncio.create_subprocess_exec()`
- **Timeouts:** All tools have reasonable timeouts (2-10 minutes)
- **XML parsing:** nmap uses XML output for structured parsing
- **Fallback detection:** Check `shutil.which()` for tool availability
- **Error handling:** Graceful degradation if tools not installed

### Data Storage
- **SQLite for structured data?** Could use tasks.db pattern for findings
- **JSON files:** Engagements and portfolio-style data
- **JSONL for logs:** Activity log uses append-only JSONL
- **Separation:** Keep pentest data in `~/.inkling/pentest/` subdirectory

### Display Philosophy
- **Status-focused:** Show engagement, target, findings count
- **Real-time updates:** Display refreshes during scans
- **Severity indicators:** Color-coded emoji (🔴🟠🟡🟢)
- **Minimal clutter:** Keep terminal aesthetic clean

---

## File Structure

```
core/
├── kali_tools.py       ✅ Security tool integration (486 lines)
├── engagement.py       ✅ Engagement management (495 lines)
├── personality.py      🚧 Needs hacker moods + persona
├── ui.py              🚧 Needs pentest display context
├── display.py         🚧 Needs pentest status queries
├── commands.py        🚧 Needs pentest commands
└── test_kali.py       ⏳ Not started

mcp_servers/
└── kali.py            ⏳ Not started (~500 lines)

modes/
├── ssh_chat.py        🚧 Needs pentest command handlers
└── web_chat.py        🚧 Needs dashboard transformation

docs/ (or root)
├── KALI_BOT.md        ⏳ Not started (~600 lines)
└── KALI_QUICK_START.md ⏳ Not started (~200 lines)

config.yml             🚧 Needs pentest section
CLAUDE.md              🚧 Needs Kali bot section
```

**Legend:**
- ✅ Complete
- 🚧 Needs updates
- ⏳ Not started

---

## Estimated Work Remaining

- **Phase 1-2:** ~4 hours (personality + MCP server)
- **Phase 3-4:** ~5 hours (commands + display UI)
- **Phase 5-6:** ~4 hours (web UI + scheduler)
- **Phase 7:** ~3 hours (documentation)
- **Phase 8:** ~4 hours (testing + polish)

**Total:** ~20 hours to full feature parity with crypto bot

---

## Key Differences from Crypto Bot

| Feature | Crypto Bot | Kali Bot |
|---------|------------|----------|
| **Domain** | Cryptocurrency tracking | Penetration testing |
| **Data source** | ccxt/CoinGecko APIs | Kali Linux tools |
| **Personality** | Crypto bro (wagmi, fren) | Hacker (pwned, root) |
| **Authorization** | None required | Engagement-based |
| **Display focus** | BTC price + portfolio | Engagement + findings |
| **Commands** | /price, /chart, /portfolio | /scan, /exploit, /vulns |
| **MCP tools** | 9 crypto tools | 8-10 pentest tools |
| **Legal concern** | None | High (ethical hacking) |

---

## Notes for Next Session

- Current branch: `claude/kali-pentest-bot-nbxGO`
- Base is from crypto bot branch (includes all crypto infrastructure)
- May want to remove crypto files if not needed
- Consider creating CLAUDE_KALI.md for Kali-specific dev guide
- Web UI could have dark "terminal" theme for hacker aesthetic
- Display could use Matrix-style green on black theme
- Consider adding ASCII art for scan results
- Metasploit integration will be complex (RPC API required)

---

## Questions to Consider

1. **Metasploit integration depth?**
   - Full RPC integration vs simple `msfconsole -x` commands?
   - Session management complexity?

2. **Multi-engagement support?**
   - Currently assumes one active engagement
   - Should we support parallel engagements?

3. **Finding deduplication?**
   - Same vuln on multiple hosts?
   - Smart merging or separate findings?

4. **Report customization?**
   - Templates for different clients?
   - Logo/branding support?

5. **Remote access security?**
   - Should ngrok be disabled for pentest bot?
   - Limit to local network only?

---

## References

- Original inkling-bot: `main` branch
- Crypto bot: `claude/crypto-watcher-bot-nbxGO` branch
- Project structure: See `CLAUDE.md`
- MCP protocol: See `core/mcp_client.py`
- Tool integration pattern: See `core/kali_tools.py`

---

**Last Updated:** 2026-02-10 05:00 UTC
**Next Session:** Start with Phase 1 (Personality & Mood System)
