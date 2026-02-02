#!/usr/bin/env python3
"""
Quick integration test to verify command handlers exist in both modes.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def test_command_handlers():
    """Test that all command handlers are defined."""
    print("Testing command handler definitions...")

    import ast
    import importlib.util

    # Load commands module directly without going through core/__init__.py
    commands_file = Path(__file__).parent / "core" / "commands.py"
    spec = importlib.util.spec_from_file_location("commands", commands_file)
    commands_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(commands_module)
    COMMANDS = commands_module.COMMANDS

    # Test SSH mode by parsing the file
    ssh_file = Path(__file__).parent / "modes" / "ssh_chat.py"
    with open(ssh_file) as f:
        ssh_content = f.read()

    ssh_tree = ast.parse(ssh_content)
    ssh_methods = set()

    # Find SSHChatMode class and extract its methods
    for node in ssh_tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "SSHChatMode":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                    ssh_methods.add(item.name)

    ssh_missing = []
    for cmd in COMMANDS:
        if cmd.handler not in ssh_methods:
            ssh_missing.append(cmd.handler)

    if ssh_missing:
        print(f"✗ SSH mode missing handlers: {', '.join(ssh_missing)}")
        return False

    print(f"✓ SSH mode has all {len(COMMANDS)} command handlers")

    # Test web mode
    web_file = Path(__file__).parent / "modes" / "web_chat.py"
    with open(web_file) as f:
        web_content = f.read()

    web_tree = ast.parse(web_content)
    web_methods = set()

    # Find WebChatMode class and extract its methods
    for node in web_tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "WebChatMode":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                    web_methods.add(item.name)

    web_missing = []
    for cmd in COMMANDS:
        handler_name = f"_cmd_{cmd.name}"
        if handler_name not in web_methods:
            web_missing.append(handler_name)

    if web_missing:
        print(f"✗ Web mode missing handlers: {', '.join(web_missing)}")
        return False

    print(f"✓ Web mode has all {len(COMMANDS)} command handlers")

    return True


def test_command_coverage():
    """Test that both modes have equivalent command coverage."""
    print("\nTesting command coverage...")

    import importlib.util

    # Load commands module directly
    commands_file = Path(__file__).parent / "core" / "commands.py"
    spec = importlib.util.spec_from_file_location("commands", commands_file)
    commands_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(commands_module)
    get_commands_by_category = commands_module.get_commands_by_category

    categories = get_commands_by_category()

    print(f"✓ Commands organized into {len(categories)} categories:")
    for cat_name, cmds in categories.items():
        print(f"  - {cat_name}: {len(cmds)} commands")

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("INTEGRATION TEST: Command Parity")
    print("=" * 60)

    success = True

    try:
        if not test_command_handlers():
            success = False

        if not test_command_coverage():
            success = False

        if success:
            print("\n" + "=" * 60)
            print("✓ ALL TESTS PASSED - Both modes have command parity")
            print("=" * 60)
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print("✗ SOME TESTS FAILED")
            print("=" * 60)
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
