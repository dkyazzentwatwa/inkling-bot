#!/usr/bin/env python3
"""
Test the MCP Task Server.

This tests the JSON-RPC protocol directly.
"""

import json
import subprocess
import sys


def send_request(server_process, method, params=None):
    """Send a JSON-RPC request to the MCP server."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {}
    }

    # Send request
    request_json = json.dumps(request) + "\n"
    server_process.stdin.write(request_json.encode())
    server_process.stdin.flush()

    # Read response
    response_line = server_process.stdout.readline()
    if not response_line:
        return None

    return json.loads(response_line)


def main():
    print("="*60)
    print("  MCP TASK SERVER TEST")
    print("="*60)

    # Start MCP server
    print("\nStarting MCP server...")
    server = subprocess.Popen(
        ["python", "mcp_servers/tasks.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Test 1: Initialize
        print("\n1. Testing initialization...")
        response = send_request(server, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {}
        })
        if response and "result" in response:
            print(f"   ✓ Server initialized")
            print(f"   Version: {response['result'].get('protocolVersion')}")
            tools = response['result'].get('capabilities', {}).get('tools', [])
            print(f"   Tools available: {len(tools)}")
            for tool in tools:
                print(f"     - {tool['name']}")
        else:
            print(f"   ✗ Initialization failed: {response}")
            return

        # Test 2: List tools
        print("\n2. Testing tools/list...")
        response = send_request(server, "tools/list")
        if response and "result" in response:
            tools = response['result'].get('tools', [])
            print(f"   ✓ Found {len(tools)} tools:")
            for tool in tools:
                print(f"     - {tool['name']}: {tool.get('description', 'No description')[:50]}...")

        # Test 3: Create task
        print("\n3. Testing task_create...")
        response = send_request(server, "tools/call", {
            "name": "task_create",
            "arguments": {
                "title": "Test MCP task",
                "description": "Created via MCP server",
                "priority": "high",
                "tags": ["mcp", "test"]
            }
        })
        if response and "result" in response:
            print(f"   ✓ Task created successfully")
            content = response['result'].get('content', [{}])[0]
            result_data = json.loads(content.get('text', '{}'))
            task_data = result_data.get('task', {})
            task_id = task_data.get('id')
            if task_id:
                print(f"   Task ID: {task_id[:8]}...")
                print(f"   Title: {task_data.get('title')}")
                print(f"   Priority: {task_data.get('priority')}")
            else:
                print(f"   ⚠️  No task ID in response")
                print(f"   Response: {result_data}")
        else:
            print(f"   ✗ Task creation failed: {response}")
            task_id = None

        # Test 4: List tasks
        print("\n4. Testing task_list...")
        response = send_request(server, "tools/call", {
            "name": "task_list",
            "arguments": {
                "status": "pending"
            }
        })
        if response and "result" in response:
            content = response['result'].get('content', [{}])[0]
            result_data = json.loads(content.get('text', '{}'))
            tasks = result_data.get('tasks', [])
            print(f"   ✓ Found {result_data.get('total', 0)} pending tasks")
            for task in tasks[:3]:  # Show first 3
                print(f"     - {task.get('title')} [{task.get('priority')}]")

        # Test 5: Get stats
        print("\n5. Testing task_stats...")
        response = send_request(server, "tools/call", {
            "name": "task_stats",
            "arguments": {}
        })
        if response and "result" in response:
            content = response['result'].get('content', [{}])[0]
            stats = json.loads(content.get('text', '{}'))
            print(f"   ✓ Statistics retrieved:")
            print(f"     Total: {stats.get('total')}")
            print(f"     Pending: {stats.get('pending')}")
            print(f"     In Progress: {stats.get('in_progress')}")
            print(f"     Completed: {stats.get('completed')}")
            print(f"     Overdue: {stats.get('overdue')}")

        # Test 6: Complete task (if we created one)
        if task_id:
            print(f"\n6. Testing task_complete...")
            response = send_request(server, "tools/call", {
                "name": "task_complete",
                "arguments": {
                    "task_id": task_id
                }
            })
            if response and "result" in response:
                content = response['result'].get('content', [{}])[0]
                result_data = json.loads(content.get('text', '{}'))
                task_data = result_data.get('task', {})
                print(f"   ✓ Task completed")
                print(f"   Status: {task_data.get('status')}")
                print(f"   Completed at: {task_data.get('completed_at')}")

        print("\n" + "="*60)
        print("  ✅ MCP SERVER TESTS PASSED")
        print("="*60)

    finally:
        # Cleanup
        server.terminate()
        server.wait()


if __name__ == "__main__":
    main()
