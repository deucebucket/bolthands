#!/usr/bin/env python3
"""Test the trained BoltHands 4B model's memU tool calling ability."""

import json
import httpx

URL = "http://localhost:8081/v1/chat/completions"

TOOLS = [
    {"type": "function", "function": {"name": "memu.store", "description": "Store a memory in memU", "parameters": {"type": "object", "properties": {"agent_id": {"type": "string"}, "user_id": {"type": "string"}, "content": {"type": "string"}, "role": {"type": "string", "enum": ["user", "assistant"]}}, "required": ["agent_id", "user_id", "content", "role"]}}},
    {"type": "function", "function": {"name": "memu.retrieve", "description": "Retrieve memories from memU via semantic search", "parameters": {"type": "object", "properties": {"agent_id": {"type": "string"}, "user_id": {"type": "string"}, "query": {"type": "string"}, "top_k": {"type": "integer"}}, "required": ["agent_id", "user_id", "query"]}}},
    {"type": "function", "function": {"name": "message.send", "description": "Send a message to a user", "parameters": {"type": "object", "properties": {"to": {"type": "string"}, "message": {"type": "string"}}, "required": ["to", "message"]}}},
    {"type": "function", "function": {"name": "memory_search", "description": "Search local memory files", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "file": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "session.send", "description": "Delegate to another agent", "parameters": {"type": "object", "properties": {"agent": {"type": "string"}, "message": {"type": "string"}}, "required": ["agent", "message"]}}},
]

TESTS = [
    ("Remember that my favorite color is blue", "memu.store"),
    ("What do you know about me?", "memu.retrieve"),
    ("Send deuce a message saying dinner is ready", "message.send"),
    ("Do you remember what I told you about movies?", "memu.retrieve"),
    ("Search the memory files for info about Spero", "memory_search"),
    ("Have the coder agent look at this bug", "session.send"),
]

SYSTEM = "You are BoltHands, an AI assistant with memory and messaging tools. Use tools when appropriate to store memories, recall information, send messages, or delegate tasks."

print("=" * 60)
print("TESTING BOLTHANDS 4B - MEMU TOOL CALLS")
print("=" * 60)

passed = 0
failed = 0

for i, (prompt, expected_tool) in enumerate(TESTS):
    print(f"\nTest {i+1}: \"{prompt}\"")
    print(f"  Expected: {expected_tool}")

    try:
        resp = httpx.post(URL, json={
            "model": "bolthands",
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "tools": TOOLS,
            "tool_choice": "auto",
            "temperature": 0.1,
            "max_tokens": 512,
        }, timeout=60)

        data = resp.json()
        choice = data["choices"][0]
        msg = choice["message"]

        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                fn = tc["function"]
                name = fn["name"]
                args = fn["arguments"]
                print(f"  Got: {name}({args})")
                if name == expected_tool:
                    print(f"  PASS")
                    passed += 1
                else:
                    print(f"  WRONG TOOL (expected {expected_tool}, got {name})")
                    failed += 1
        else:
            content = msg.get("content", "")
            if "<tool_call>" in content:
                print(f"  Got inline: {content[:200]}")
                if expected_tool in content:
                    print(f"  PARTIAL PASS (inline format)")
                    passed += 1
                else:
                    print(f"  WRONG TOOL (inline)")
                    failed += 1
            else:
                print(f"  Got text: {content[:200]}")
                print(f"  FAIL - no tool call")
                failed += 1

    except Exception as e:
        print(f"  ERROR: {e}")
        failed += 1

print(f"\n{'=' * 60}")
print(f"RESULTS: {passed}/{passed + failed} passed ({passed/(passed+failed)*100:.0f}%)")
print(f"{'=' * 60}")
