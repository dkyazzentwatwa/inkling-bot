#!/usr/bin/env python3
"""
Test script for Task Manager functionality.

Tests:
1. Task CRUD operations
2. Task queries (overdue, due soon, stats)
3. Personality integration
4. Heartbeat behaviors
"""

import sys
import time
import asyncio
from datetime import datetime, timedelta

# Import task manager
from core.tasks import TaskManager, TaskStatus, Priority
from core.personality import Personality, Mood
from core.heartbeat import Heartbeat, HeartbeatConfig
from core.progression import LevelCalculator


def print_section(title):
    """Print a test section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_task_crud():
    """Test basic task CRUD operations."""
    print_section("TEST 1: Task CRUD Operations")

    # Initialize task manager
    tm = TaskManager()

    # Create tasks
    print("Creating tasks...")
    task1 = tm.create_task(
        title="Write documentation",
        description="Document the task manager features",
        priority=Priority.HIGH,
        tags=["docs", "urgent"]
    )
    print(f"✓ Created task: {task1.title} (ID: {task1.id[:8]}...)")

    task2 = tm.create_task(
        title="Fix bug in display",
        description="E-ink display flickers",
        priority=Priority.URGENT,
        due_date=time.time() + 86400,  # Due tomorrow
        tags=["bug", "display"]
    )
    print(f"✓ Created task: {task2.title} (ID: {task2.id[:8]}...)")

    task3 = tm.create_task(
        title="Learn Python",
        description="Complete Python tutorial",
        priority=Priority.LOW,
        project="Learning",
        tags=["learning", "research"]
    )
    print(f"✓ Created task: {task3.title} (ID: {task3.id[:8]}...)")

    # Create an overdue task (due yesterday)
    task4 = tm.create_task(
        title="Overdue task",
        description="This should be overdue",
        priority=Priority.MEDIUM,
        due_date=time.time() - 86400  # Due yesterday
    )
    print(f"✓ Created overdue task: {task4.title} (ID: {task4.id[:8]}...)")

    # List all tasks
    print("\nListing all tasks:")
    all_tasks = tm.list_tasks()
    for t in all_tasks:
        status_icon = "⏳" if t.status == TaskStatus.PENDING else "✅"
        priority_icon = {"low": "🟢", "medium": "🟡", "high": "🟠", "urgent": "🔴"}[t.priority.value]
        print(f"  {status_icon} {priority_icon} {t.title}")

    # Update task
    print("\nUpdating task status...")
    task1.status = TaskStatus.IN_PROGRESS
    tm.update_task(task1)
    print(f"✓ Task '{task1.title}' now in progress")

    # Complete task
    print("\nCompleting task...")
    completed = tm.complete_task(task2.id)
    print(f"✓ Task '{completed.title}' completed at {datetime.fromtimestamp(completed.completed_at).strftime('%H:%M:%S')}")

    return tm


def test_task_queries(tm):
    """Test task query operations."""
    print_section("TEST 2: Task Queries")

    # Get overdue tasks
    print("Checking for overdue tasks:")
    overdue = tm.get_overdue_tasks()
    if overdue:
        for t in overdue:
            days_overdue = abs(t.days_until_due)
            print(f"  ⚠️  {t.title} (overdue by {days_overdue} days)")
    else:
        print("  ✓ No overdue tasks")

    # Get tasks due soon
    print("\nTasks due within 3 days:")
    due_soon = tm.get_due_soon(days=3)
    if due_soon:
        for t in due_soon:
            days = t.days_until_due
            print(f"  📅 {t.title} (due in {days} days)")
    else:
        print("  ✓ No tasks due soon")

    # Get stats
    print("\nTask Statistics:")
    stats = tm.get_stats()
    print(f"  Total tasks: {stats['total']}")
    print(f"  Pending: {stats['pending']}")
    print(f"  In Progress: {stats['in_progress']}")
    print(f"  Completed: {stats['completed']}")
    print(f"  Overdue: {stats['overdue']}")
    print(f"  Due Soon: {stats['due_soon']}")
    print(f"  30-day Completion Rate: {stats['completion_rate_30d']:.1%}")

    # Filter by tags
    print("\nFiltering by tag 'learning':")
    learning_tasks = tm.list_tasks(tags=["learning"])
    for t in learning_tasks:
        print(f"  📚 {t.title}")

    # Filter by priority
    print("\nHigh/Urgent priority tasks:")
    urgent_tasks = [t for t in tm.list_tasks() if t.priority in [Priority.HIGH, Priority.URGENT]]
    for t in urgent_tasks:
        status = "✅" if t.status == TaskStatus.COMPLETED else "⏳"
        print(f"  {status} {t.title} ({t.priority.value})")


def test_personality_integration(tm):
    """Test personality integration with tasks."""
    print_section("TEST 3: Personality Integration")

    # Initialize personality
    personality = Personality(name="Inkling")
    print(f"Initial mood: {personality.mood.current.value} {personality.face}")
    print(f"Initial level: {personality.progression.level}")
    xp_to_next = LevelCalculator.xp_to_next_level(personality.progression.xp)
    print(f"Initial XP: {personality.progression.xp} (need {xp_to_next} more for level {personality.progression.level + 1})")

    # Test task creation event
    print("\nCreating an urgent task...")
    result = personality.on_task_event(
        "task_created",
        {"priority": "urgent", "title": "Emergency fix"}
    )
    if result and result.get("message"):
        print(f"  Response: {result['message']}")
    print(f"  Mood: {personality.mood.current.value} {personality.face}")
    if result and result.get("xp_awarded"):
        print(f"  XP awarded: +{result['xp_awarded']}")

    # Test task completion
    print("\nCompleting a high-priority task...")
    result = personality.on_task_event(
        "task_completed",
        {"priority": "high", "was_on_time": True, "title": "Important task"}
    )
    if result and result.get("message"):
        print(f"  Response: {result['message']}")
    print(f"  Mood: {personality.mood.current.value} {personality.face}")
    if result and result.get("xp_awarded"):
        print(f"  XP awarded: +{result['xp_awarded']}")
        xp_to_next = LevelCalculator.xp_to_next_level(personality.progression.xp)
        print(f"  Total XP: {personality.progression.xp} (need {xp_to_next} more for next level)")

    # Test overdue reminder
    print("\nChecking overdue task...")
    overdue_tasks = tm.get_overdue_tasks()
    if overdue_tasks:
        task = overdue_tasks[0]
        result = personality.on_task_event(
            "task_overdue",
            {"title": task.title, "priority": task.priority.value}
        )
        if result and result.get("message"):
            print(f"  Response: {result['message']}")


async def test_heartbeat_behaviors(tm):
    """Test heartbeat task behaviors."""
    print_section("TEST 4: Heartbeat Task Behaviors")

    # Initialize personality and heartbeat
    personality = Personality(name="Inkling")
    config = HeartbeatConfig(
        tick_interval_seconds=1,  # Fast for testing
        enable_mood_behaviors=True,
        enable_maintenance=True,
    )

    heartbeat = Heartbeat(
        personality=personality,
        task_manager=tm,
        config=config
    )

    messages_received = []

    async def message_callback(message, face):
        """Capture heartbeat messages."""
        messages_received.append((message, face))
        print(f"  💬 {message} {face}")

    heartbeat.on_message(message_callback)

    print("Testing overdue task reminder behavior...")
    print("(Setting mood to trigger behavior)")

    # Manually trigger the overdue behavior
    result = await heartbeat._behavior_remind_overdue()
    if result:
        print(f"  ✓ Reminder generated: {result}")
    else:
        print("  ℹ️  No overdue tasks or behavior didn't trigger")

    # Test task suggestion
    print("\nTesting task suggestion behavior...")
    personality.mood.set_mood(Mood.CURIOUS, 0.8)
    result = await heartbeat._behavior_suggest_task()
    if result:
        print(f"  ✓ Suggestion generated: {result}")
    else:
        print("  ℹ️  No suggestions (no matching tasks)")

    # Test celebration
    print("\nTesting streak celebration...")
    # Complete a few tasks for streak testing
    for i in range(3):
        task = tm.create_task(
            title=f"Quick task {i+1}",
            priority=Priority.LOW
        )
        tm.complete_task(task.id)

    result = await heartbeat._behavior_celebrate_streak()
    if result:
        print(f"  ✓ Celebration generated: {result}")
    else:
        print("  ℹ️  No celebration (need more completions or daily streak)")


def test_web_ui_ready(tm):
    """Test that web UI can access task data."""
    print_section("TEST 5: Web UI Readiness")

    print("Checking if task data is accessible for web UI...")

    # Simulate web UI API calls
    all_tasks = tm.list_tasks()
    print(f"  ✓ Can list all tasks: {len(all_tasks)} tasks")

    stats = tm.get_stats()
    print(f"  ✓ Can get stats: {stats['total']} total, {stats['completed']} completed")

    pending = tm.list_tasks(status=TaskStatus.PENDING)
    in_progress = tm.list_tasks(status=TaskStatus.IN_PROGRESS)
    completed = tm.list_tasks(status=TaskStatus.COMPLETED)

    print(f"\n  Kanban board preview:")
    print(f"    📝 Pending: {len(pending)}")
    print(f"    🔄 In Progress: {len(in_progress)}")
    print(f"    ✅ Completed: {len(completed)}")

    print("\n  ✓ Web UI should be able to display all task data")
    print("  ℹ️  To test web UI: python main.py --mode web")
    print("  ℹ️  Then visit: http://localhost:8081/tasks")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  🧪 TASK MANAGER TEST SUITE")
    print("="*60)

    # Test 1: CRUD
    tm = test_task_crud()

    # Test 2: Queries
    test_task_queries(tm)

    # Test 3: Personality
    test_personality_integration(tm)

    # Test 4: Heartbeat (async)
    await test_heartbeat_behaviors(tm)

    # Test 5: Web UI
    test_web_ui_ready(tm)

    print("\n" + "="*60)
    print("  ✅ ALL TESTS COMPLETED")
    print("="*60)
    print("\nNext steps:")
    print("  1. Run 'python main.py --mode web' to test the web UI")
    print("  2. Visit http://localhost:8081/tasks for Kanban board")
    print("  3. Visit http://localhost:8081/settings to configure")
    print("  4. Chat with Inkling and ask it to manage tasks via AI")
    print()


if __name__ == "__main__":
    asyncio.run(main())
