# Contributing Guide

How to contribute to Inkling - code style, testing, and pull request process.

## Getting Started

### 1. Fork and Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR_USERNAME/inkling-bot.git
cd inkling-bot
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install pytest pytest-asyncio pytest-cov black flake8
```

### 3. Create Feature Branch

```bash
git checkout -b feature/my-feature
# or
git checkout -b fix/bug-description
```

## Code Style

### Python Style

We follow PEP 8 with some preferences:

```python
# Good
def calculate_xp(base_amount: int, multiplier: float = 1.0) -> int:
    """
    Calculate XP with optional multiplier.
    
    Args:
        base_amount: Base XP value
        multiplier: Optional multiplier (default 1.0)
    
    Returns:
        Final XP amount
    """
    return int(base_amount * multiplier)

# Avoid
def calcXP(amt, mult=1.0):
    return int(amt * mult)
```

### Formatting

Use Black for auto-formatting:

```bash
# Format all files
black .

# Check without changing
black --check .
```

### Linting

Use Flake8 for linting:

```bash
flake8 core/ modes/ mcp_servers/
```

### Type Hints

Use type hints for function signatures:

```python
# Good
def get_mood(self) -> str:
    return self._mood

def set_traits(self, traits: Dict[str, float]) -> None:
    self._traits = traits

# Avoid
def get_mood(self):
    return self._mood
```

### Docstrings

Use Google-style docstrings:

```python
def award_xp(
    self,
    source: XPSource,
    base_amount: int,
    prompt: Optional[str] = None,
) -> Tuple[bool, int]:
    """
    Award XP from a source.
    
    Args:
        source: XP source type
        base_amount: Base XP amount (before multiplier)
        prompt: Optional user prompt (for anti-gaming)
    
    Returns:
        Tuple of (awarded: bool, actual_amount: int)
    
    Raises:
        ValueError: If base_amount is negative
    
    Example:
        >>> awarded, amount = tracker.award_xp(XPSource.CHAT, 10)
        >>> print(f"Awarded: {awarded}, Amount: {amount}")
    """
```

## Project Structure

```
inkling-bot/
├── main.py              # Entry point
├── config.yml           # Default config
├── requirements.txt     # Dependencies
├── CLAUDE.md           # AI assistant docs
├── core/               # Core modules
│   ├── brain.py        # AI providers
│   ├── personality.py  # Mood & traits
│   ├── progression.py  # XP & leveling
│   ├── tasks.py        # Task management
│   ├── memory.py       # Persistent conversation memory
│   ├── heartbeat.py    # Autonomous behaviors
│   ├── display.py      # E-ink abstraction
│   ├── ui.py           # UI components
│   ├── commands.py     # Command definitions
│   └── mcp_client.py   # MCP integration
├── modes/              # Operating modes
│   ├── ssh_chat.py     # Terminal mode
│   └── web_chat.py     # Web UI mode
├── mcp_servers/        # MCP tool servers
│   ├── tasks.py        # Task management tools
│   └── filesystem.py   # File operations
├── tests/              # Test files
│   └── test_*.py
└── reference/          # Documentation
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -xvs

# Run specific file
pytest tests/test_personality.py

# Run with coverage
pytest --cov=core --cov-report=html
```

### Writing Tests

```python
# tests/test_my_feature.py
import pytest
from core.my_module import MyClass

class TestMyClass:
    """Tests for MyClass."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.instance = MyClass()
    
    def test_basic_functionality(self):
        """Test basic operation."""
        result = self.instance.do_something()
        assert result == expected_value
    
    def test_edge_case(self):
        """Test edge case handling."""
        with pytest.raises(ValueError):
            self.instance.do_something(invalid_input)
    
    @pytest.mark.asyncio
    async def test_async_method(self):
        """Test async functionality."""
        result = await self.instance.async_method()
        assert result is not None
```

### Test Categories

```bash
# Unit tests (fast, isolated)
pytest tests/unit/

# Integration tests (slower, real dependencies)
pytest tests/integration/

# Skip slow tests
pytest -m "not slow"
```

## Making Changes

### Before Coding

1. Check existing issues for duplicates
2. Create an issue describing your change
3. Discuss approach if significant change
4. Get confirmation before large refactors

### While Coding

1. Keep changes focused (one feature/fix per PR)
2. Write tests for new functionality
3. Update documentation (CLAUDE.md, docstrings)
4. Run tests frequently

### Commit Messages

Format:
```
type: Short description (50 chars max)

Longer description if needed. Wrap at 72 characters.
Explain what and why, not how.

Fixes #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting (no code change)
- `refactor`: Code change (no new feature/fix)
- `test`: Adding tests
- `chore`: Maintenance

Examples:
```
feat: Add weather command

Adds /weather command that shows weather for a city.
Uses OpenWeatherMap API with caching.

Fixes #45
```

```
fix: Prevent XP farming with rate limiter

Users could spam messages to gain XP rapidly.
Added rate limiter with 100 XP/hour cap.

Fixes #67
```

## Pull Request Process

### 1. Prepare Your PR

```bash
# Update from main
git fetch origin
git rebase origin/main

# Run all checks
black --check .
flake8 core/ modes/
pytest

# Push your branch
git push -u origin feature/my-feature
```

### 2. Create PR

On GitHub:
1. Click "New Pull Request"
2. Select your branch
3. Fill in template:

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] Manual testing done

## Checklist
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] CLAUDE.md updated if needed
- [ ] No new warnings
```

### 3. Address Review

- Respond to all comments
- Make requested changes
- Push updates to same branch
- Re-request review when ready

### 4. Merge

Once approved:
- Squash and merge preferred
- Delete branch after merge
- Verify CI passes on main

## Areas for Contribution

### Good First Issues

- Add new slash commands
- Improve documentation
- Add unit tests
- Fix typos/grammar
- UI improvements

### Medium Complexity

- New personality moods
- Heartbeat behaviors
- MCP tool servers
- Config options

### Advanced

- New AI providers
- Display drivers
- Performance optimization
- Architecture changes

## Development Tips

### Debug Mode

```bash
INKLING_DEBUG=1 python main.py --mode ssh
```

Shows:
- AI provider calls
- Tool executions
- Mood changes
- Error details

### Mock Display

For development without hardware:
```yaml
display:
  type: "mock"
```

### Test API Calls

```python
# Quick test in Python REPL
from core.brain import Brain
from core.memory import MemoryStore

memory = MemoryStore()
memory.initialize()
brain = Brain(config, memory_store=memory, memory_config={"enabled": True})
result = await brain.think("Hello", "You are helpful.")
print(result.content)
```

### Inspect State

```bash
# In SSH mode
/stats     # Token usage
/mood      # Current mood
/level     # XP/progression
/system    # System stats
```

## Getting Help

- **Questions**: Open a Discussion
- **Bugs**: Open an Issue with reproduction steps
- **Features**: Open an Issue with use case
- **Chat**: [Discord/Slack link if available]

## Code of Conduct

1. Be respectful and inclusive
2. Focus on constructive feedback
3. Assume good intentions
4. Help others learn
5. Credit others' work

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

## Thank You!

Every contribution helps make Inkling better. Whether it's:
- Fixing a typo
- Adding a test
- Implementing a feature
- Improving documentation
- Reporting a bug
- Suggesting an idea

We appreciate your help!
