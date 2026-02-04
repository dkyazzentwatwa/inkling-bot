# 🤝 Contributing to Inkling

Thank you for your interest in contributing to Inkling! This guide will help you get started.

## 🌟 Ways to Contribute

### 🐛 Bug Reports

Found a bug? Please:

1. **Check existing issues** first to avoid duplicates
2. **Include detailed information**:
   - Inkling version (git commit hash)
   - Operating system and Python version
   - Hardware (Pi model, display type)
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages and logs
3. **Use the bug report template** when creating an issue

### 💡 Feature Requests

Have an idea? Great! Please:

1. **Search existing requests** to see if it's been suggested
2. **Describe the problem** you're trying to solve
3. **Explain your proposed solution**
4. **Consider alternatives** - why is this the best approach?
5. **Be open to discussion** - maintainers may have insights

### 📝 Documentation

Documentation is always appreciated:

- Fix typos or unclear explanations
- Add missing information
- Improve code examples
- Translate to other languages (future)
- Create tutorials or guides

### 🔧 Code Contributions

Ready to code? Follow the workflow below.

---

## 🚀 Development Workflow

### 1. Set Up Your Environment

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/inkling.git
cd inkling

# Add upstream remote
git remote add upstream https://github.com/original/inkling.git

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If it exists

# Install pre-commit hooks (if used)
pre-commit install
```

### 2. Create a Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes:
git checkout -b fix/issue-123-description
```

### 3. Make Your Changes

#### Code Style

- **Python**: Follow PEP 8
  - Use 4 spaces for indentation
  - Max line length: 100 characters
  - Use type hints where helpful
  - Add docstrings to functions/classes

- **TypeScript**: Follow project conventions
  - Use 2 spaces for indentation
  - Prefer `const` over `let`
  - Add JSDoc comments

- **Naming Conventions**:
  - `snake_case` for Python functions/variables
  - `PascalCase` for Python classes
  - `camelCase` for TypeScript/JavaScript

#### Testing

Write tests for new features:

```python
# tests/test_your_feature.py
import pytest
from core.your_module import your_function

def test_your_function():
    """Test that your_function works correctly."""
    result = your_function(input_data)
    assert result == expected_output
```

Run tests before committing:

```bash
# All tests
pytest

# Specific file
pytest tests/test_your_feature.py -xvs

# With coverage
pytest --cov=core --cov-report=html
```

#### Documentation

Update relevant docs:

- **README.md** - If changing user-facing features
- **docs/** - Add guides for new features
- **CHANGES.md** - Document your changes
- **Docstrings** - In-code documentation

### 4. Commit Your Changes

```bash
# Stage changes
git add .

# Commit with clear message
git commit -m "Add feature: brief description

- Detailed explanation of what changed
- Why it was changed
- Any breaking changes or migration notes

Fixes #123"
```

**Good commit messages:**
- Start with a verb (Add, Fix, Update, Remove)
- Be concise in first line (<50 chars)
- Add details in commit body if needed
- Reference issue numbers

**Examples:**
```
Add telegram encryption support

Implements X25519 key exchange for E2E encrypted messages.
Adds new endpoints for key distribution and message delivery.

Closes #45
```

```
Fix display refresh rate limiting

Enforces minimum interval between refreshes to prevent
e-ink burn-in. Adds separate limits for V3 (0.5s) and V4 (5s).

Fixes #78
```

### 5. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Open GitHub and create a Pull Request
# Fill out the PR template completely
```

**Pull Request Guidelines:**

- **Title**: Clear, descriptive summary
- **Description**:
  - What changes were made
  - Why they were necessary
  - How to test them
  - Screenshots if UI changes
- **Tests**: Ensure all tests pass
- **Documentation**: Update relevant docs
- **Breaking Changes**: Clearly mark and explain
- **Linked Issues**: Reference related issues

---

## 📋 Code Review Process

### What to Expect

1. **Automated Checks**: CI/CD runs tests and linters
2. **Maintainer Review**: Code review from project maintainers
3. **Feedback**: Constructive feedback and requested changes
4. **Iteration**: Address feedback and push updates
5. **Approval**: Once approved, maintainers will merge

### Review Criteria

Maintainers check for:

- ✅ **Functionality**: Does it work as intended?
- ✅ **Tests**: Are there tests? Do they pass?
- ✅ **Code Quality**: Is it readable, maintainable?
- ✅ **Documentation**: Are docs updated?
- ✅ **Breaking Changes**: Are they necessary and documented?
- ✅ **Performance**: Does it impact performance?
- ✅ **Security**: Any security implications?

### Responding to Feedback

- **Be patient** - Reviews take time
- **Ask questions** - If feedback is unclear, ask!
- **Be respectful** - Maintainers volunteer their time
- **Learn from it** - Feedback helps you grow
- **Push updates** - Address comments and push again

---

## 🎯 Contribution Ideas

Not sure where to start? Here are some ideas:

### Good First Issues

Look for issues tagged `good-first-issue`:

- Simple bug fixes
- Documentation improvements
- Test additions
- Code cleanup

### Needed Features

- [ ] Additional AI provider support (Groq, Together, etc.)
- [ ] More face expressions
- [ ] Additional social features
- [ ] Mobile app (React Native?)
- [ ] Voice interface
- [ ] MCP server integrations
- [ ] Improved web UI features

### Documentation Gaps

- Setup guides for specific hardware
- More detailed architecture docs
- Video tutorials
- Translation to other languages

---

## 🏗️ Architecture Guidelines

### Core Principles

1. **Modularity**: Keep components independent
2. **Simplicity**: Favor simple solutions over complex ones
3. **Offline-first**: Features should work without internet when possible
4. **Privacy**: Respect user data and minimize cloud dependencies
5. **Extensibility**: Make it easy to add new features

### Design Patterns

**Personality System:**
- Traits affect behavior probabilistically
- Mood state machine with smooth transitions
- Energy system influences interaction frequency

**Display Management:**
- Abstraction layer for different hardware
- Rate limiting to prevent damage
- Mock display for development

**AI Integration:**
- Multi-provider with automatic fallback
- Token budgeting and quota management
- Provider-agnostic interface

**Social Features:**
- Signature-based authentication
- End-to-end encryption for DMs
- Rate limiting and abuse prevention

---

## 🧪 Testing Guidelines

### Test Coverage

Aim for:
- **Core modules**: 80%+ coverage
- **API endpoints**: 100% coverage
- **UI components**: Integration tests

### Test Types

**Unit Tests:**
```python
def test_personality_mood_transition():
    """Test mood transitions work correctly."""
    personality = Personality()
    personality.mood.transition_to("happy")
    assert personality.mood.current == "happy"
```

**Integration Tests:**
```python
def test_brain_with_real_api():
    """Test Brain with actual API call."""
    brain = Brain(config)
    result = await brain.think("Hello!")
    assert result.content
    assert result.tokens_used > 0
```

**E2E Tests:**
```python
def test_full_chat_flow():
    """Test complete chat interaction."""
    # Setup
    # Execute
    # Verify
```

---

## 📦 Release Process

(For maintainers)

1. Update version in relevant files
2. Update CHANGES.md with release notes
3. Run full test suite
4. Create git tag: `git tag v1.2.3`
5. Push tag: `git push origin v1.2.3`
6. Create GitHub release with notes
7. Announce on social media / forums

---

## 🤔 Questions?

- **Read the docs**: Check existing documentation
- **Search issues**: Your question may be answered
- **Ask in discussions**: GitHub Discussions for Q&A
- **Join Discord**: (Future) Real-time chat with community

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

All documentation contributions are licensed under CC BY 4.0.

---

## 🙏 Thank You!

Every contribution, no matter how small, makes Inkling better.

Thank you for being part of the community! 🌙

---

<div align="center">

**[← Back to Documentation Index](README.md)**

**[← Back to Main README](../README.md)**

</div>
