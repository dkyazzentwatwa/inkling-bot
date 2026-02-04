# Developer Assistant Guide

Use Inkling as a coding companion for GitHub integration, code review reminders, and development workflow support.

## Overview

Inkling as a developer assistant helps you:
- Track pull requests and issues
- Get code review reminders
- Manage development tasks
- Monitor CI/CD status
- Stay organized during sprints

## Setup

### Enable GitHub via Composio

1. Get Composio API key from [app.composio.dev](https://app.composio.dev)
2. Connect GitHub in Composio dashboard
3. Configure in Inkling:

```yaml
mcp:
  enabled: true
  servers:
    composio:
      transport: "http"
      url: "https://backend.composio.dev/v3/mcp"
      headers:
        x-api-key: "${COMPOSIO_API_KEY}"
```

### Developer Personality

```yaml
personality:
  curiosity: 0.6      # Interested in your work
  cheerfulness: 0.5   # Professional
  verbosity: 0.5      # Balanced detail
  playfulness: 0.3    # Minimal jokes
  empathy: 0.6        # Understanding of deadlines
  independence: 0.7   # Proactive reminders
```

### Task Management

```yaml
mcp:
  servers:
    tasks:
      command: "python"
      args: ["mcp_servers/tasks.py"]
```

## GitHub Integration

### Pull Request Status

```
You: Show my open PRs

Inkling: 🔀 Your Open Pull Requests:

         1. #142 - Add dark mode support
            ✓ Tests passing | 2 approvals needed
            Updated 2 hours ago

         2. #138 - Fix memory leak in worker
            ⚠️ CI running | 1 approval
            Updated yesterday

         3. #135 - Update documentation
            ❌ Tests failing | 0 approvals
            Updated 3 days ago
```

### PR Details

```
You: What's the status of PR 142?

Inkling: 🔀 PR #142: Add dark mode support

         Status: Open (2 days old)
         Branch: feature/dark-mode → main

         Checks:
         ✓ Lint passed
         ✓ Unit tests passed
         ✓ Build succeeded

         Reviews:
         ✓ @alice: Approved
         ○ @bob: Changes requested
         ○ @charlie: Pending

         3 files changed, +245/-12
```

### Review Reminders

Inkling proactively reminds about reviews:

```
┌─────────────────────────────────────────┐
│ (o_o)  Inkling                  11:00   │
├─────────────────────────────────────────┤
│                                         │
│   You have 2 PRs waiting for review:    │
│   #156 from @alice (2 days)             │
│   #158 from @bob (1 day)                │
│                                         │
└─────────────────────────────────────────┘
```

### Create PR Tasks

```
You: I need to review Alice's PR

Inkling: 📋 Created task: "Review PR #156 from @alice"
         Priority: Medium

         Want me to show the PR diff?
```

## Issue Tracking

### View Issues

```
You: What issues are assigned to me?

Inkling: 🐛 Your Assigned Issues:

         1. #89 - Login timeout on slow networks
            Priority: High | Sprint 23

         2. #92 - Add export to CSV feature
            Priority: Medium | Sprint 23

         3. #95 - Update dependencies
            Priority: Low | Backlog
```

### Issue Details

```
You: Tell me about issue 89

Inkling: 🐛 Issue #89: Login timeout on slow networks

         Status: Open
         Assignee: You
         Labels: bug, high-priority, backend

         Description:
         Users on slow connections (< 1Mbps) experience
         timeouts during login. Need to increase timeout
         or add retry logic.

         Comments: 3
         Last activity: Yesterday
```

### Link Issues to Tasks

```
You: Create a task for issue 89

Inkling: 📋 Created task: "Fix #89 - Login timeout"
         Priority: High (from issue labels)
         Due: End of sprint (Friday)

         Tags: #bug #backend #issue-89
```

## CI/CD Monitoring

### Build Status

```
You: How's the build?

Inkling: 🏗️ CI/CD Status:

         main branch:
         ✓ Build #456 passed (10 min ago)

         Your branches:
         feature/dark-mode: ✓ Passing
         bugfix/timeout: ⏳ Running (2 min)

         Recent failures: None today 🎉
```

### Failed Build Alert

```
┌─────────────────────────────────────────┐
│ (@_@)  Inkling                  14:32   │
├─────────────────────────────────────────┤
│                                         │
│   ❌ Build failed on bugfix/timeout     │
│   Test: test_retry_logic                │
│   Check it out?                         │
│                                         │
└─────────────────────────────────────────┘
```

## Sprint Management

### Sprint Overview

```
You: Sprint status?

Inkling: 📊 Sprint 23 Status:

         Days remaining: 4

         Stories:
         ✓ 3 completed (15 points)
         🔄 2 in progress (8 points)
         ○ 2 not started (5 points)

         Velocity: 18/28 points (64%)
         On track for: 22-25 points

         Blockers: 1 (awaiting API from team B)
```

### Daily Development Tasks

```
You: What should I work on today?

Inkling: 🎯 Suggested Focus:

         1. 🔴 Review PR #156 (2 days waiting)
         2. 🔴 Fix failing tests on PR #135
         3. 🟡 Continue issue #89 (timeout fix)
         4. 🟢 Update dependencies (if time)

         You have standup at 9:30 AM.
```

## Code Review Workflow

### Review Checklist

```
You: I'm reviewing PR 156

Inkling: 📝 Review Checklist for PR #156:

         Code Quality:
         [ ] Follows style guide
         [ ] No obvious bugs
         [ ] Error handling present

         Testing:
         [ ] Tests included
         [ ] Edge cases covered
         [ ] CI passing

         Documentation:
         [ ] Comments where needed
         [ ] README updated if applicable

         Want me to track as you go?
```

### Submit Review

```
You: Done reviewing, it looks good

Inkling: 📝 Ready to approve PR #156?

         I'll help you compose the review:

         "Looks good! Clean implementation of
          the feature. Minor suggestion: consider
          adding a test for the edge case on line 45."

         Submit this review?
```

## Development Stats

### Weekly Summary

```
You: How was my week?

Inkling: 📈 Your Development Week:

         PRs:
         - 2 created
         - 3 reviewed
         - 1 merged

         Issues:
         - 1 closed
         - 2 in progress

         Commits: 23
         Lines: +1,245 / -432

         Focus time: 18 pomodoros (7.5h)

         Great productivity! 🚀
```

### Contribution Graph

```
You: Show my commits this week

Inkling: 📊 Commit Activity:

         Mon: ████████ (8)
         Tue: ██████████████ (14)
         Wed: ██████ (6)
         Thu: ████████████ (12)
         Fri: ████ (4 so far)

         Total: 44 commits
         Most active: Tuesday
```

## Integration Ideas

### Slack Notifications

Forward important updates to Slack:
- PR approved → notify
- Build failed → alert
- Mentioned in issue → ping

### Calendar Sync

Block time for:
- Code reviews
- Sprint planning
- Bug fixes

### IDE Integration

Consider connecting to your IDE for:
- Current file context
- Error highlighting
- Quick task creation

## Best Practices

### Morning Routine

1. Check overnight build status
2. Review pending PRs
3. Check sprint board
4. Plan day's tasks

### Before Lunch

1. Push work in progress
2. Update task status
3. Respond to PR comments

### End of Day

1. Create PRs for completed work
2. Update issue status
3. Note blockers
4. Plan tomorrow

### Weekly

1. Review sprint progress
2. Update documentation
3. Clear old branches
4. Celebrate shipped features!

## Troubleshooting

### GitHub Not Connecting

1. Verify Composio API key
2. Check GitHub is connected in Composio
3. Re-authorize if needed

### Missing PRs/Issues

1. Check repository access
2. Verify organization permissions
3. Ensure correct repo selected

### Stale Data

```
You: Refresh GitHub data

Inkling: 🔄 Refreshing...

         PRs: 3 open (was 4)
         Issues: 5 assigned (unchanged)
         Builds: Updated

         Last sync: Just now
```

## Next Steps

- [Task Management](../features/task-management.md) - Link issues to tasks
- [MCP Integration](../features/mcp-integration.md) - Advanced GitHub features
- [Daily Standup](daily-standup.md) - Morning dev routine
- [Focus & Pomodoro](focus-pomodoro.md) - Coding sessions
