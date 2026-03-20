# Agent Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python FastAPI agent backend that runs autonomous coding tasks inside Docker containers via iterative LLM tool calling.

**Architecture:** FastAPI server creates an AgentController per task. The controller loops: call LLM → parse tool call → execute in Docker sandbox → observe result → repeat until done. Events stream to clients via WebSocket.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, httpx, docker SDK, pydantic, click, rich, pytest

**Spec:** `docs/superpowers/specs/2026-03-20-agent-backend-design.md`

---

## File Map

```
src/bolthands/
  __init__.py
  config.py                  # Config from env vars (pydantic-settings)
  events/
    __init__.py
    actions.py               # Action pydantic models
    observations.py          # Observation pydantic models
  tools/
    __init__.py
    registry.py              # Tool registration + routing
    bash.py                  # execute_bash
    read_file.py             # read_file
    write_file.py            # write_file
    edit_file.py             # edit_file (str_replace)
    search_files.py          # search_files (grep)
    think.py                 # think (reasoning, no execution)
    finish.py                # finish (stop loop)
  sandbox/
    __init__.py
    container.py             # Docker container lifecycle
    executor.py              # Run commands in container
  llm/
    __init__.py
    client.py                # Async OpenAI-compatible HTTP client
    parser.py                # Extract tool calls from LLM responses
    prompts.py               # Composable system prompt builder
  agent/
    __init__.py
    state.py                 # State machine enum
    controller.py            # Main agent loop
  server/
    __init__.py
    app.py                   # FastAPI endpoints + WebSocket
  cli/
    __init__.py
    main.py                  # CLI entry point
tests/
  __init__.py
  test_events.py
  test_tools.py
  test_parser.py
  test_controller.py
  test_server.py
```

Build order: events → tools → sandbox → llm → agent → server → cli. Each layer depends only on layers below it.

---

### Task 1: Project setup and event models

**Files:**
- Create: `src/bolthands/__init__.py`
- Create: `src/bolthands/config.py`
- Create: `src/bolthands/events/__init__.py`
- Create: `src/bolthands/events/actions.py`
- Create: `src/bolthands/events/observations.py`
- Create: `tests/test_events.py`
- Modify: `pyproject.toml` (add new dependencies)

- [ ] **Step 1: Update pyproject.toml with agent backend dependencies**

Add to `[project] dependencies`:
```
fastapi>=0.115
uvicorn>=0.34
websockets>=14.0
docker>=7.0
```

Add to `[project.optional-dependencies] dev`:
```
httpx[http2]>=0.27
```

Change `[project.scripts]` to:
```
bolthands = "bolthands.cli.main:main"
```

- [ ] **Step 2: Create config.py**

Pydantic-settings model reading from env vars with BOLTHANDS_ prefix. Fields: llm_url, max_iterations, max_output_length, stuck_threshold, sandbox_memory, sandbox_image. All with defaults from the spec.

- [ ] **Step 3: Create events/actions.py**

Pydantic BaseModel subclasses. Each action has a `type` field (literal string) for discrimination:
- `CmdRunAction(type="cmd_run", command: str, timeout: int = 30)`
- `FileReadAction(type="file_read", path: str, max_lines: int | None = None)`
- `FileWriteAction(type="file_write", path: str, content: str)`
- `FileEditAction(type="file_edit", path: str, old_str: str, new_str: str)`
- `SearchFilesAction(type="search_files", pattern: str, path: str = ".", max_results: int = 20)`
- `ThinkAction(type="think", thought: str)`
- `FinishAction(type="finish", message: str)`
- `Action = CmdRunAction | FileReadAction | ... ` (Union type alias)

- [ ] **Step 4: Create events/observations.py**

Same pattern:
- `CmdOutputObservation(type="cmd_output", stdout: str, stderr: str, exit_code: int)`
- `FileContentObservation(type="file_content", path: str, content: str, exists: bool)`
- `FileWriteObservation(type="file_write_result", path: str, success: bool, error: str | None = None)`
- `FileEditObservation(type="file_edit_result", path: str, success: bool, error: str | None = None)`
- `SearchResultObservation(type="search_result", matches: list[str], total_count: int)`
- `ThinkObservation(type="think_result", thought: str)`
- `ErrorObservation(type="error", error_type: str, message: str)`
- `Observation = ...` (Union type alias)

- [ ] **Step 5: Write test_events.py**

Test that each action/observation serializes to JSON and deserializes back. Test that discriminated union works (parse from dict with `type` field).

- [ ] **Step 6: Run tests, verify pass**

Run: `pytest tests/test_events.py -v`

- [ ] **Step 7: Commit**

```
git add src/bolthands/ tests/test_events.py pyproject.toml
git commit -m "feat: add event models and project config"
```

---

### Task 2: Tool registry and all tool implementations

**Files:**
- Create: `src/bolthands/tools/__init__.py`
- Create: `src/bolthands/tools/registry.py`
- Create: `src/bolthands/tools/bash.py`
- Create: `src/bolthands/tools/read_file.py`
- Create: `src/bolthands/tools/write_file.py`
- Create: `src/bolthands/tools/edit_file.py`
- Create: `src/bolthands/tools/search_files.py`
- Create: `src/bolthands/tools/think.py`
- Create: `src/bolthands/tools/finish.py`
- Create: `tests/test_tools.py`

- [ ] **Step 1: Create registry.py**

`ToolRegistry` class:
- `register(name: str, schema_fn, execute_fn)` — register a tool
- `schemas() -> list[dict]` — return all OpenAI function calling schemas
- `get(name: str)` — return (schema, execute) for a tool
- `async execute(name: str, args: dict, executor) -> Observation` — route to handler

- [ ] **Step 2: Create each tool file**

Each tool file has the same structure:
```python
SCHEMA = {"type": "function", "function": {"name": "...", ...}}

def schema() -> dict:
    return SCHEMA

async def execute(args: dict, executor) -> Observation:
    ...
```

bash.py: calls `executor.run(args["command"], timeout=args.get("timeout", 30))`, returns CmdOutputObservation
read_file.py: calls `executor.run(f"cat {path}")` (with max_lines via `head -n`), returns FileContentObservation
write_file.py: calls `executor.run(f"cat > {path} << 'BOLTHANDS_EOF'\n{content}\nBOLTHANDS_EOF")`, returns FileWriteObservation
edit_file.py: calls executor to read file, does Python str.replace on old_str→new_str, writes back. Returns FileEditObservation.
search_files.py: calls `executor.run(f"grep -rn {pattern} {path} | head -n {max_results}")`, returns SearchResultObservation
think.py: no execution — just returns ThinkObservation(thought=args["thought"])
finish.py: no execution — returns None (controller handles finish specially)

- [ ] **Step 3: Create __init__.py that auto-registers all tools**

```python
from .registry import ToolRegistry
from . import bash, read_file, write_file, edit_file, search_files, think, finish

def create_registry() -> ToolRegistry:
    reg = ToolRegistry()
    for mod in [bash, read_file, write_file, edit_file, search_files, think, finish]:
        reg.register(mod.SCHEMA["function"]["name"], mod.schema, mod.execute)
    return reg
```

- [ ] **Step 4: Write test_tools.py**

Test each tool:
- Schema is valid JSON with required fields (name, description, parameters)
- Registry contains all 7 tools
- Registry.schemas() returns 7 schemas
- Each tool's execute returns the correct observation type (mock the executor)
- edit_file correctly replaces old_str with new_str
- think returns thought without calling executor
- finish returns None

- [ ] **Step 5: Run tests, verify pass**

Run: `pytest tests/test_tools.py -v`

- [ ] **Step 6: Commit**

```
git add src/bolthands/tools/ tests/test_tools.py
git commit -m "feat: add tool registry with 7 tools"
```

---

### Task 3: Docker sandbox

**Files:**
- Create: `src/bolthands/sandbox/__init__.py`
- Create: `src/bolthands/sandbox/container.py`
- Create: `src/bolthands/sandbox/executor.py`

- [ ] **Step 1: Create container.py**

`SandboxContainer` class:
- `__init__(image, workspace_dir, memory_limit="4g")`
- `async create()` — docker client.containers.create() wrapped in to_thread
- `async start()`
- `async stop()`
- `async remove()`
- `async is_running() -> bool`
- Context manager support (`__aenter__`/`__aexit__` for auto cleanup)

Uses `docker.from_env()` for the client. Container config: working_dir="/workspace", volumes={workspace: {"bind": "/workspace", "mode": "rw"}}, network_mode="host", mem_limit=memory_limit.

- [ ] **Step 2: Create executor.py**

`SandboxExecutor` class:
- `__init__(container: SandboxContainer)`
- `async run(command: str, timeout: int = 30) -> tuple[str, str, int]` — returns (stdout, stderr, exit_code)

Wraps `container._container.exec_run()` in `asyncio.to_thread()`. Decodes output bytes to str. Truncates output to max_output_length if configured.

- [ ] **Step 3: No unit tests for sandbox (needs Docker)**

Sandbox tests are integration tests. They'll be marked with `@pytest.mark.integration` and skipped by default. We'll add a basic smoke test later.

- [ ] **Step 4: Commit**

```
git add src/bolthands/sandbox/
git commit -m "feat: add Docker sandbox container and executor"
```

---

### Task 4: LLM client and response parser

**Files:**
- Create: `src/bolthands/llm/__init__.py`
- Create: `src/bolthands/llm/client.py`
- Create: `src/bolthands/llm/parser.py`
- Create: `src/bolthands/llm/prompts.py`
- Create: `tests/test_parser.py`

- [ ] **Step 1: Create client.py**

`LLMClient` class:
- `__init__(base_url, timeout=120, max_retries=3)`
- `async chat(messages: list[dict], tools: list[dict] | None, temperature=0.1) -> dict` — POST to /chat/completions, return message dict
- Retry logic: on httpx.TimeoutException or status 500/502/503, retry with 2/4/8s backoff. On ConnectionRefused, raise immediately.

- [ ] **Step 2: Create parser.py**

`parse_response(message: dict) -> Action | None`:
- If message has `tool_calls` array: extract first tool call's name + arguments, map to Action type
- Elif message `content` contains `<tool_call>` tags: regex extract JSON, map to Action
- Elif message has plain text content: return None (agent just wants to talk)
- Tool name → Action type mapping: "execute_bash"→CmdRunAction, "read_file"→FileReadAction, etc.

- [ ] **Step 3: Create prompts.py**

`build_system_prompt(tool_schemas: list[dict], workspace_info: str = "") -> str`:
- Concatenates base instructions + tool descriptions + workspace context
- Base: "You are BoltHands, an autonomous coding agent. You solve tasks by reading files, running commands, and iterating on errors. Always read before editing. Test after changes. Use finish when done."
- Tools section generated from schemas
- Workspace section optional (file listing, etc.)

- [ ] **Step 4: Write test_parser.py**

Test cases:
- Parse native tool_calls format (OpenAI style) → correct Action
- Parse inline `<tool_call>` XML format → correct Action
- Parse plain text response → None
- Parse response with multiple tool calls → first one extracted
- Parse malformed JSON in tool call → raises or returns None
- Each tool name maps to correct Action subclass

- [ ] **Step 5: Run tests, verify pass**

Run: `pytest tests/test_parser.py -v`

- [ ] **Step 6: Commit**

```
git add src/bolthands/llm/ tests/test_parser.py
git commit -m "feat: add LLM client, parser, and prompt builder"
```

---

### Task 5: Agent state machine and controller

**Files:**
- Create: `src/bolthands/agent/__init__.py`
- Create: `src/bolthands/agent/state.py`
- Create: `src/bolthands/agent/controller.py`
- Create: `tests/test_controller.py`

- [ ] **Step 1: Create state.py**

`AgentState` enum: IDLE, RUNNING, PAUSED, FINISHED, ERROR

`AgentStatus` pydantic model: state, iteration, max_iterations, last_action_type, error_message, task_id

- [ ] **Step 2: Create controller.py**

`AgentController` class:
- `__init__(config, llm_client, tool_registry, sandbox_image, workspace_dir)`
- `async run(task: str) -> AgentStatus` — the main loop from the spec
- `cancel()` — set state to ERROR, stop sandbox
- `_is_stuck(action, history) -> bool` — check if same action repeated N times
- `_truncate_history(history) -> list` — drop oldest pairs if > 50 messages
- Event callback: `on_event: Callable[[dict], None] | None` — called with WebSocket event envelope

The controller owns the sandbox lifecycle: creates it at start of run(), tears it down in a finally block.

- [ ] **Step 3: Write test_controller.py**

Mock the LLM client to return canned responses. Mock the executor to return canned outputs. Test:
- Single tool call → finish: agent runs one bash, then finishes (2 iterations)
- Multi-step: agent reads file → edits → runs test → finishes (4 iterations)
- Error recovery: first attempt fails (exit_code=1), agent retries with fix, succeeds
- Max iterations: agent hits limit, transitions to ERROR
- Stuck detection: same action 3 times → ERROR
- Finish action: agent calls finish → state=FINISHED
- LLM error: connection refused → ERROR immediately
- History truncation: 60 messages → oldest pairs dropped

- [ ] **Step 4: Run tests, verify pass**

Run: `pytest tests/test_controller.py -v`

- [ ] **Step 5: Commit**

```
git add src/bolthands/agent/ tests/test_controller.py
git commit -m "feat: add agent state machine and controller loop"
```

---

### Task 6: FastAPI server with WebSocket

**Files:**
- Create: `src/bolthands/server/__init__.py`
- Create: `src/bolthands/server/app.py`
- Create: `tests/test_server.py`

- [ ] **Step 1: Create app.py**

FastAPI app with:
- `POST /task` — create AgentController, start background task, return task_id
- `GET /task/{task_id}/status` — return current AgentStatus
- `DELETE /task/{task_id}` — cancel task, cleanup sandbox
- `WebSocket /ws/{task_id}` — stream events as JSON, close on task completion
- `@app.on_event("shutdown")` — stop all running tasks and containers
- Store active tasks in a dict: `{task_id: (controller, asyncio_task)}`

- [ ] **Step 2: Write test_server.py**

Use FastAPI TestClient (httpx):
- POST /task returns 200 with task_id
- GET /task/{id}/status returns current state
- DELETE /task/{id} returns 200
- GET /task/nonexistent returns 404
- Mock the controller so no real Docker/LLM needed

- [ ] **Step 3: Run tests, verify pass**

Run: `pytest tests/test_server.py -v`

- [ ] **Step 4: Commit**

```
git add src/bolthands/server/ tests/test_server.py
git commit -m "feat: add FastAPI server with WebSocket streaming"
```

---

### Task 7: CLI entry point

**Files:**
- Create: `src/bolthands/cli/__init__.py`
- Create: `src/bolthands/cli/main.py`

- [ ] **Step 1: Create main.py**

Click CLI with:
- `bolthands run TASK --image IMAGE --llm-url URL` — create controller, run task, print events with rich formatting
- `bolthands serve --port PORT` — start the FastAPI server with uvicorn
- Events printed as: `[iteration] TOOL_NAME(args) → result` with colors (green=success, red=error, yellow=warning)

- [ ] **Step 2: Manual test**

Run: `bolthands serve --port 9000` — verify server starts
Run: `bolthands run "echo hello" --image python:3.12-slim` — verify it works end-to-end (requires Docker + LLM running)

- [ ] **Step 3: Commit**

```
git add src/bolthands/cli/
git commit -m "feat: add CLI with run and serve commands"
```

---

### Task 8: Integration test and final wiring

**Files:**
- Modify: all `__init__.py` files for clean imports
- Create: `tests/test_integration.py` (marked @pytest.mark.integration)

- [ ] **Step 1: Wire up all __init__.py exports**

Each package exports its key classes for clean import paths:
- `from bolthands.agent import AgentController`
- `from bolthands.tools import create_registry`
- `from bolthands.llm import LLMClient`
- etc.

- [ ] **Step 2: Write integration test**

`@pytest.mark.integration` — skipped by default, run with `pytest -m integration`:
- Create a real Docker container with python:3.12-slim
- Execute a bash command
- Read a file
- Write a file
- Edit a file
- Search files
- Verify all operations work end-to-end

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v --ignore=tests/test_integration.py`
Expected: all unit tests pass

- [ ] **Step 4: Final commit and push**

```
git add .
git commit -m "feat: complete agent backend with integration tests"
git push origin main
```
