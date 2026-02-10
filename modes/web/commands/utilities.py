"""Utility commands (thoughts, find, memory, settings, backup, journal)."""
from pathlib import Path
from typing import Dict, Any

from . import CommandHandler


class UtilityCommands(CommandHandler):
    """Handlers for utility commands (/thoughts, /find, /memory, /settings, /backup, /journal)."""

    def thoughts(self) -> Dict[str, Any]:
        """Show recent autonomous thoughts."""
        log_path = Path("~/.inkling/thoughts.log").expanduser()
        if not log_path.exists():
            return {
                "response": "No thoughts yet. Thoughts are generated automatically over time.",
                "face": self.personality.face,
            }

        lines = log_path.read_text().strip().splitlines()
        recent = lines[-10:]

        output = [f"**Recent Thoughts** ({len(recent)} of {len(lines)})\n"]
        for line in recent:
            parts = line.split(" | ", 1)
            if len(parts) == 2:
                ts, thought = parts
                output.append(f"`{ts}` {thought}")
            else:
                output.append(line)

        if self.personality.last_thought:
            output.append(f"\n*Latest: {self.personality.last_thought}*")

        return {
            "response": "\n".join(output),
            "face": self.personality.face,
        }

    def find(self, args: str = "") -> Dict[str, Any]:
        """Search tasks by keyword."""
        if not args.strip():
            return {"response": "Usage: `/find <keyword>`", "face": self.personality.face}

        if not self.task_manager:
            return {"response": "Task manager not available.", "face": self.personality.face, "error": True}

        query = args.strip().lower()
        all_tasks = self.task_manager.list_tasks()
        matches = [
            t for t in all_tasks
            if query in t.title.lower()
            or (t.description and query in t.description.lower())
            or any(query in tag.lower() for tag in t.tags)
        ]

        if not matches:
            return {"response": f"No tasks found matching '{args.strip()}'.", "face": self.personality.face}

        status_icons = {"pending": "📋", "in_progress": "⏳", "completed": "✅", "cancelled": "❌"}
        output = [f"**Search Results** ({len(matches)} matches)\n"]
        for task in matches:
            icon = status_icons.get(task.status.value, "·")
            tags = " ".join(f"#{t}" for t in task.tags) if task.tags else ""
            output.append(f"{icon} `{task.id[:8]}` **{task.title}** [{task.priority.value}]")
            if task.description:
                output.append(f"   {task.description[:80]}")
            if tags:
                output.append(f"   {tags}")

        return {
            "response": "\n".join(output),
            "face": self.personality.face,
        }

    def memory(self) -> Dict[str, Any]:
        """Show memory stats and recent entries."""
        from core.memory import MemoryStore

        store = self.memory_store or MemoryStore()
        owns_store = self.memory_store is None
        try:
            if owns_store:
                store.initialize()

            total = store.count()
            user_count = store.count(MemoryStore.CATEGORY_USER)
            pref_count = store.count(MemoryStore.CATEGORY_PREFERENCE)
            fact_count = store.count(MemoryStore.CATEGORY_FACT)
            event_count = store.count(MemoryStore.CATEGORY_EVENT)

            output = ["**Memory Store**\n"]
            output.append(f"Total: **{total}** memories")
            output.append(f"  User info: {user_count}")
            output.append(f"  Preferences: {pref_count}")
            output.append(f"  Facts: {fact_count}")
            output.append(f"  Events: {event_count}")

            recent = store.recall_recent(limit=5)
            if recent:
                output.append("\n**Recent:**")
                for mem in recent:
                    output.append(f"  `[{mem.category}]` {mem.key}: {mem.value[:60]}")

            important = store.recall_important(limit=3)
            if important:
                output.append("\n**Most Important:**")
                for mem in important:
                    output.append(f"  ★{mem.importance:.1f} `[{mem.category}]` {mem.key}: {mem.value[:60]}")

            return {
                "response": "\n".join(output),
                "face": self.personality.face,
            }
        finally:
            if owns_store:
                store.close()

    def settings(self) -> Dict[str, Any]:
        """Show current settings (redirects to settings page in web mode)."""
        return {
            "response": "Visit the [Settings](/settings) page to view and change settings.",
            "face": self.personality.face,
        }

    def backup(self) -> Dict[str, Any]:
        """Create a backup of Inkling data."""
        import shutil
        from datetime import datetime

        data_dir = Path("~/.inkling").expanduser()
        if not data_dir.exists():
            return {"response": "No data directory found.", "face": self.personality.face, "error": True}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"inkling_backup_{timestamp}"
        backup_path = data_dir.parent / f"{backup_name}.tar.gz"

        try:
            shutil.make_archive(
                str(data_dir.parent / backup_name),
                'gztar',
                root_dir=str(data_dir.parent),
                base_dir='.inkling'
            )
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            return {
                "response": f"Backup created!\n\n**File:** `{backup_path}`\n**Size:** {size_mb:.1f} MB",
                "face": "happy",
            }
        except Exception as e:
            return {"response": f"Backup failed: {e}", "face": self.personality.face, "error": True}

    def journal(self) -> Dict[str, Any]:
        """Show recent journal entries."""
        journal_path = Path("~/.inkling/journal.log").expanduser()
        if not journal_path.exists():
            return {
                "response": "No journal entries yet. Journal entries are written daily by the heartbeat system.",
                "face": self.personality.face,
            }

        lines = journal_path.read_text().strip().splitlines()
        recent = lines[-10:]

        output = [f"**Journal** ({len(recent)} of {len(lines)} entries)\n"]
        for line in recent:
            parts = line.split(" | ", 1)
            if len(parts) == 2:
                ts, entry = parts
                output.append(f"`{ts}` {entry}")
            else:
                output.append(line)

        return {
            "response": "\n".join(output),
            "face": self.personality.face,
        }
