# 📚 Inkling Documentation

Welcome to the Inkling documentation! This directory contains comprehensive guides for using and developing Inkling.

## 📁 Documentation Structure

### 📘 [guides/](guides/) - User Guides & Tutorials

Getting started, feature guides, and how-tos for users:
- **[Setup Guide](guides/SETUP.md)** - Hardware assembly and software installation
- **[Usage Guide](guides/USAGE.md)** - Complete feature walkthrough
- **[Updating & Auto-Boot](guides/UPDATING_AND_AUTOBOOT.md)** - Safe updates and automatic startup
- **[Web UI Guide](guides/WEB_UI.md)** - Browser interface documentation
- **[Web Commands](guides/WEB_COMMANDS.md)** - Web-specific commands
- **[Autonomous Mode](guides/AUTONOMOUS_MODE.md)** - Heartbeat system and autonomous behaviors
- **[Leveling System](guides/LEVELING_SYSTEM.md)** - XP, progression, and prestige mechanics
- **[AI Providers](guides/AI_PROVIDERS.md)** - Configuring Anthropic, OpenAI, Gemini
- **[Social Guide](guides/SOCIAL_GUIDE.md)** - Social features (deprecated)
- **[Troubleshooting](guides/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Filesystem MCP](guides/FILESYSTEM_MCP.md)** - File operations via MCP
- **[YAML Fix Guide](guides/YAML_FIX_GUIDE.md)** - Config file troubleshooting

### 🔧 [implementation/](implementation/) - Implementation Notes

Technical implementation details, changelogs, and feature summaries:
- **[Implementation Summary](implementation/IMPLEMENTATION_SUMMARY.md)** - Recent feature implementations
- **[Final Summary](implementation/FINAL_SUMMARY.md)** - Complete feature overview
- **[Changes](implementation/CHANGES.md)** - Changelog and version history
- **[Bugfixes Summary](implementation/BUGFIXES_SUMMARY.md)** - Bug fix documentation
- **[Rate Limit Fix](implementation/RATE_LIMIT_FIX.md)** - AI rate limiting implementation
- **[SD Card Implementation](implementation/SD_CARD_IMPLEMENTATION.md)** - Multiple storage locations
- **[Task Manager Implementation](implementation/TASK_MANAGER_IMPLEMENTATION.md)** - Task system details
- **[Task Manager Quickstart](implementation/TASK_MANAGER_QUICKSTART.md)** - Quick setup guide
- **[Task Manager Test Report](implementation/TASK_MANAGER_TEST_REPORT.md)** - Test results
- **[Task Manager Enabled](implementation/TASK_MANAGER_ENABLED.md)** - Enabling task features
- **[AI Settings Implementation](implementation/AI_SETTINGS_IMPLEMENTATION.md)** - AI config details
- **[Composio Integration](implementation/COMPOSIO_INTEGRATION.md)** - MCP app integrations
- **[Settings UI Plan](implementation/SETTINGS_UI_PLAN.md)** - Settings page design

### 📖 [reference/](reference/) - Technical Reference

API documentation and technical specifications:
- **[API Reference](reference/API.md)** - Cloud backend API documentation
- **[Faces Reference](reference/FACES_REFERENCE.md)** - Available face expressions
- **[Documentation Summary](reference/DOCUMENTATION_SUMMARY.md)** - Doc structure overview

### 🛠️ [development/](development/) - Development Guides

Contributing, testing, and development workflows:
- **[Contributing Guide](development/CONTRIBUTING.md)** - How to contribute to Inkling
- **[Testing Guide](development/TESTING_GUIDE.md)** - Running tests and validation
- **[Verification Checklist](development/VERIFICATION_CHECKLIST.md)** - Pre-commit checks

## 🚀 Quick Links

### For Users

**Getting Started:**
- [Installation](guides/SETUP.md#installation)
- [First Run](guides/USAGE.md#first-run)
- [Web Interface](guides/WEB_UI.md#getting-started)
- [Slash Commands](../README.md#slash-commands-both-ssh-and-web)

**Features:**
- [Task Management](implementation/TASK_MANAGER_QUICKSTART.md)
- [Multiple Storage Locations](implementation/SD_CARD_IMPLEMENTATION.md)
- [Autonomous Behaviors](guides/AUTONOMOUS_MODE.md)
- [Leveling System](guides/LEVELING_SYSTEM.md)

### For Developers

**Development:**
- [Project Structure](../README.md#project-structure)
- [Running Tests](development/TESTING_GUIDE.md)
- [Contributing](development/CONTRIBUTING.md)
- [API Reference](reference/API.md)

**Implementation Notes:**
- [Recent Changes](implementation/CHANGES.md)
- [Feature Implementations](implementation/)
- [Bug Fixes](implementation/BUGFIXES_SUMMARY.md)

## 🗂️ Document Index

### User Guides
| Document | Audience | Topics Covered |
|----------|----------|----------------|
| **Setup Guide** | Beginners | Hardware assembly, OS setup, installation |
| **Usage Guide** | Users | Commands, modes, basic features |
| **Web UI Guide** | Users | Browser interface, settings, themes |
| **Autonomous Mode** | Advanced users | Heartbeat configuration, behaviors |
| **Leveling System** | Users | XP mechanics, achievements, prestige |
| **AI Providers** | Users | Configuring API keys and models |
| **Troubleshooting** | Everyone | Error messages, common fixes |

### Technical Documentation
| Document | Audience | Topics Covered |
|----------|----------|----------------|
| **API Reference** | Developers | Cloud backend endpoints |
| **Implementation Summary** | Developers | Feature implementation details |
| **Contributing Guide** | Contributors | Development workflow |
| **Testing Guide** | Developers | Test suite and validation |

## 🆘 Need Help?

1. **Check [Troubleshooting Guide](guides/TROUBLESHOOTING.md)** - Common issues and fixes
2. **Read relevant docs** - Use the index above to find specific topics
3. **Search closed issues** - Someone may have had the same problem
4. **Open a new issue** - Include logs and reproduction steps

## 📝 Contributing to Documentation

Found a typo? Want to clarify something? Documentation contributions are welcome!

### Quick Edits

For small fixes (typos, clarifications):
1. Click "Edit" on the file in GitHub
2. Make your changes
3. Submit a pull request

### Major Changes

For new guides or substantial rewrites:
1. Open an issue to discuss the change
2. Fork the repository
3. Create a new branch: `git checkout -b docs/your-topic`
4. Write your documentation
5. Submit a pull request

### Documentation Style Guide

- **Use clear headers** - Make it easy to scan
- **Include code examples** - Show, don't just tell
- **Add emojis sparingly** - One per section header max
- **Link between docs** - Help users navigate
- **Keep it current** - Update when features change
- **Place in correct directory**:
  - User-facing guides → `guides/`
  - Implementation notes → `implementation/`
  - API/reference → `reference/`
  - Development workflows → `development/`

## 📄 License

Documentation is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Code examples in documentation follow the project's MIT license.

---

<div align="center">

**[← Back to Main README](../README.md)**

</div>
