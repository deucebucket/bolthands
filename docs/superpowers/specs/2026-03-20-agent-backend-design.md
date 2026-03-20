# BoltHands Agent Backend — Design Spec

**Date:** 2026-03-20
**Goal:** Python FastAPI server running an autonomous coding agent inside Docker containers with iterative tool calling via local LLM.

---

## Overview

The agent backend is the core engine of BoltHands. It receives a task, runs an autonomous loop (prompt LLM, call tool, run in Docker, observe result, repeat), and streams progress to clients via WebSocket.

## Module Structure

```
src/bolthands/
  server/
    app.py              # FastAPI app: POST /task, GET /status, WS /ws
  agent/
    controller.py        # Main agent loop
    state.py             # State machine (idle/running/paused/finished/error)
  sandbox/
    container.py         # Docker container lifecycle
    executor.py          # Run commands inside container
  tools/
    registry.py          # Tool registration, schema generation, routing
    bash.py              # execute_bash tool
    read_file.py         # read_file tool
    write_file.py        # write_file tool
    search_files.py      # search_files tool
    finish.py            # finish tool (signal completion)
  llm/
    client.py            # Async OpenAI-compatible client
    parser.py            # Extract tool calls from LLM responses
    prompts.py           # Composable system prompt builder
  events/
    actions.py           # Action pydantic models
    observations.py      # Observation pydantic models
  cli/
    main.py              # Interactive CLI for testing
```

## Components

### 1. Server (server/app.py)

FastAPI application with three endpoints:

- POST /task: Submit a task. Body: {"task": "description", "sandbox_image": "python:3.12"}. Returns {"task_id": "uuid"}.
- GET /task/{task_id}/status: Poll task status. Returns state, current step, iteration count.
- WebSocket /ws/{task_id}: Stream real-time events (actions, observations, state changes) as JSON.

Server creates an AgentController per task, runs it in a background asyncio task, and streams events through the WebSocket.

### 2. Agent Controller (agent/controller.py)

The core loop:

1. Set state to RUNNING
2. Add user task to message history
3. While running and under iteration limit:
   a. Check stuck detection (same action repeated 3+ times)
   b. Call LLM with history + tool schemas
   c. Parse response into Action
   d. If finish action, set state to FINISHED and break
   e. Execute action in sandbox via tool registry
   f. Get observation (stdout/stderr/file content/error)
   g. Append action + observation to history
   h. Emit event to WebSocket
   i. Increment iteration counter

Configuration:
- max_iterations: 25 (default)
- max_output_length: 10000 chars (truncate tool output to prevent context overflow)
- stuck_threshold: 3 (same action repeated 3 times = stuck)

### 3. Agent State (agent/state.py)

Enum-based state machine:

IDLE -> RUNNING -> FINISHED
                -> ERROR
                -> PAUSED -> RUNNING

State transitions emit events to the WebSocket. State includes: current phase, iteration count, last action type, error message if applicable.

### 4. Sandbox (sandbox/container.py, sandbox/executor.py)

container.py: Docker container lifecycle:
- create(image, workspace_dir): Create container with workspace mounted
- start(): Start container
- stop(): Stop container
- remove(): Remove container
- is_running(): Health check

Container config:
- Working dir: /workspace
- Host workspace mounted as bind mount (read-write)
- Network: host mode (agent can access local services)
- Memory limit: configurable (default 4GB)
- No GPU needed (only the LLM server uses GPU)

executor.py: Run commands inside the container:
- run(command, timeout=30): Run command, return stdout + stderr + exit code
- read_file(path): Read file contents from container filesystem
- write_file(path, content): Write file to container filesystem
- search_files(pattern, path): Grep for pattern in files

Uses docker SDK's exec_run under the hood. All commands run as non-root user inside the container.

### 5. Tools (tools/*.py)

Each tool file exports:
- schema(): OpenAI function calling schema dict
- execute(args, sandbox): Returns Observation

registry.py collects all tools:
- register(tool_module): Register a tool
- schemas(): Return list of all tool schemas
- execute(action, sandbox): Route action to correct tool handler

Tools:
- bash: Run shell command. Args: command (str), timeout (int, default 30). Returns stdout, stderr, exit_code.
- read_file: Read file. Args: path (str), max_lines (int, optional). Returns file content or error.
- write_file: Write file. Args: path (str), content (str). Returns success/error.
- search_files: Search files. Args: pattern (str), path (str, default "."), max_results (int, default 20). Returns matching lines with file:line format.
- finish: Signal completion. Args: message (str). Stops the agent loop.

### 6. LLM Client (llm/client.py)

Async HTTP client for OpenAI-compatible API (llama.cpp server):
- base_url defaults to http://localhost:8080/v1
- chat(messages, tools, temperature) sends POST to /chat/completions
- Returns the assistant message dict
- 120 second timeout for long generations
- Uses httpx.AsyncClient

### 7. LLM Parser (llm/parser.py)

Extracts actions from LLM responses:
- Native tool calls (message.tool_calls array): preferred path
- Inline tool_call XML tags: fallback for models without native tool calling support
- Returns an Action pydantic model

### 8. Prompt Builder (llm/prompts.py)

Composable system prompt from fragments:
- base: Core identity and behavior rules
- tools: Generated from tool schemas
- workspace: Current workspace context (file listing, etc.)

Prompt is assembled at each turn, not monolithic. Only relevant fragments included.

### 9. Events (events/actions.py, events/observations.py)

Pydantic models for type safety and serialization:

Actions:
- CmdRunAction(command, timeout)
- FileReadAction(path, max_lines)
- FileWriteAction(path, content)
- SearchFilesAction(pattern, path)
- FinishAction(message)

Observations:
- CmdOutputObservation(stdout, stderr, exit_code)
- FileContentObservation(path, content, exists)
- FileWriteObservation(path, success, error)
- SearchResultObservation(matches, total_count)
- ErrorObservation(error_type, message)

### 10. CLI (cli/main.py)

Interactive CLI for testing the agent without a frontend:

    bolthands run "Fix the bug in src/parser.py" --image python:3.12
    bolthands run "Create a React app with a todo list" --image node:20

Prints actions and observations to terminal in real-time. Uses click for argument parsing, rich for formatted output.

## Data Flow

```
CLI or Frontend
  |
  v  POST /task or WebSocket
FastAPI Server
  |
  v  creates
AgentController
  |
  +-> LLMClient.chat(history, tools)
  |     |
  |     v  HTTP to localhost:8080
  |   llama.cpp (BoltHands 9B)
  |     |
  |     v  response with tool_calls
  |   Parser.extract_action()
  |     |
  |     v  Action
  +-> ToolRegistry.execute(action, sandbox)
  |     |
  |     v  docker exec_run
  |   Sandbox Container
  |     |
  |     v  stdout/stderr
  |   Observation
  |     |
  |     v  append to history
  +-> Loop back to LLMClient.chat()
```

## Testing Strategy

All tests mock the LLM client and Docker (no real model or containers needed):

1. test_parser.py: Extract tool calls from various LLM output formats
2. test_controller.py: Full agent loop (single action, multi-step, error recovery, finish, stuck detection, max iterations)
3. test_tools.py: Tool schema validation, argument checking, routing
4. test_sandbox.py: Container lifecycle (integration test, needs Docker)
5. test_server.py: API endpoint tests with httpx test client

## Dependencies

- fastapi + uvicorn: HTTP server
- websockets: WebSocket support
- httpx: Async HTTP client for LLM
- docker: Docker SDK for Python
- pydantic: Data models
- click: CLI
- rich: Terminal formatting
- pytest + pytest-asyncio: Testing

## Out of Scope (for this spec)

- Frontend (separate spec)
- Context management / compaction (separate spec)
- Model training pipeline (already built)
- Multi-agent delegation
- File watching / hot reload
