#!/usr/bin/env python3
"""Quick test of Composio MCP connection"""
import requests
import json

def test_composio():
    url = "https://backend.composio.dev/v3/mcp/658b6781-0d17-4893-b235-ffe4bf067bc4/mcp?user_id=pg-test-5b5d52dc-e9c6-46a3-aedf-bd7bb14b0cb2"
    
    print("Testing Composio MCP connection...")
    print(f"URL: {url[:70]}...")
    
    # Test: List tools
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list"
    }
    
    print("\n1. Fetching tool list...")
    resp = requests.post(url, json=payload, timeout=10)
    print(f"   Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        tools = data.get("result", {}).get("tools", [])
        print(f"   ✅ Found {len(tools)} tools")
        
        # Show Gmail tools
        gmail_tools = [t for t in tools if "gmail" in t.get("name", "").lower()]
        print(f"\n2. Gmail tools found: {len(gmail_tools)}")
        for tool in gmail_tools[:5]:
            print(f"   - {tool.get('name')}: {tool.get('description', '')[:60]}...")
        
        # Show Calendar tools
        cal_tools = [t for t in tools if "calendar" in t.get("name", "").lower()]
        print(f"\n3. Calendar tools found: {len(cal_tools)}")
        for tool in cal_tools[:5]:
            print(f"   - {tool.get('name')}: {tool.get('description', '')[:60]}...")
        
        print(f"\n✅ Composio is working! Dynamic search will now find these tools.")
        return True
    else:
        print(f"   ❌ Error: {resp.text[:200]}")
        return False

if __name__ == "__main__":
    result = test_composio()
    exit(0 if result else 1)
