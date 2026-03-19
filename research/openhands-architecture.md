# OpenHands Architecture Deep Dive

> Research for BoltHands fork project. Based on All-Hands-AI/OpenHands repository analysis (March 2026).
> **Note**: OpenHands is mid-migration from V0 (legacy) to V1 (Software Agent SDK). V0 code is marked deprecated with April 1, 2026 removal date. This document covers V0 since it's the fully-documented, battle-tested version. V1 is still being built.

---

## 1. Agent System

### The CodeAct Agent

**Core file**: `openhands/agenthub/codeact_agent/codeact_agent.py`

The CodeAct agent (v2.2) implements the "CodeAct paradigm" -- unifying all agent actions into code execution rather than structured XML/JSON action formats. The agent extends a base `Agent` class and is the default (and only production) agent.

**Key attributes:**
- `pending_actions`: A `deque` that queues multiple actions from a single LLM response
- `tools`: List of `ChatCompletionToolParam` instances (OpenAI-format tool schemas)
- `conversation_memory`: `ConversationMemory` instance managing dialogue history
- `condenser`: Handles context compression
- `llm`: Language model instance from LLM registry

### The Action/Observation Loop

**Core loop file**: `openhands/controller/agent_controller.py`

The loop works like this:

```
User message → Agent Controller → agent.step(state) → Action
    → Runtime executes action → Observation
    → Agent Controller → agent.step(state) → next Action
    → ... repeat until AgentFinishAction or error/limit
```

**AgentController._step()** sequence:
1. Verify agent is in `RUNNING` state with no pending action awaiting observation
2. Sync budget across all LLM services, check iteration/token limits
3. Run stuck detection (`_is_stuck()`) -- detects infinite loops
4. Call `agent.step(self.state)` to get the next action
5. Run security analysis on risky actions
6. Add confirmed action to event stream
7. Wait for observation from runtime

**CodeActAgent.step()** sequence:
1. Return pending queued actions if any exist (single LLM call can produce multiple actions)
2. Check for `/exit` command
3. Invoke condenser on event history -- may return `CondensationAction` instead
4. Build message history via `_get_messages()`
5. Call LLM with messages + tool definitions
6. Parse response into actions via `response_to_actions()` (delegates to `function_calling.py`)
7. Queue all actions, return the first one

### Available Actions

**Action definitions**: `openhands/events/action/`

| Action Class | Tool Name | What It Does |
|---|---|---|
| `CmdRunAction` | `execute_bash` | Run a bash command in the sandbox shell |
| `IPythonRunCellAction` | `execute_ipython_cell` | Run Python code in Jupyter/IPython |
| `FileReadAction` | `str_replace_editor` (view) | Read a file with optional line range |
| `FileEditAction` | `str_replace_editor` (str_replace/create/insert) | Edit files via exact string replacement |
| `FileEditAction` | `edit_file` | LLM-based file editing (alternative) |
| `BrowseInteractiveAction` | `browser` | Browser automation via BrowserGym |
| `BrowseURLAction` | (direct) | Navigate to a URL |
| `AgentFinishAction` | `finish` | Signal task completion |
| `AgentThinkAction` | `think` | Log internal reasoning (not executed) |
| `CondensationAction` | `condensation_request` | Request context compression |
| `MCPAction` | (dynamic) | Model Context Protocol tool calls |
| `TaskTrackingAction` | `task_tracker` | Track task progress |
| `MessageAction` | (implicit) | Send text message to user |

**CmdRunAction fields:**
- `command` (str): The shell command
- `is_input` (bool): Whether this is input to a running process (vs new command)
- `timeout` (float): Hard timeout in seconds
- `blocking` (bool): Synchronous execution
- `is_static` (bool): Run in separate process
- `hidden` (bool): Skip LLM processing and event stream

**FileEditAction supports two modes:**
- **ACI-based**: `command` field with `old_str`/`new_str` for exact string replacement
- **LLM-based**: `content` with `start`/`end` line numbers for range replacement

### Available Observations

**Observation definitions**: `openhands/events/observation/`

| File | Observation Type |
|---|---|
| `commands.py` | Command execution output (stdout/stderr/exit code) |
| `files.py` | File read/write results |
| `browse.py` | Browser page content / accessibility tree |
| `error.py` | Error messages |
| `success.py` | Success confirmations |
| `agent.py` | Agent state observations |
| `delegate.py` | Delegation results from child agents |
| `loop_recovery.py` | Stuck loop detection results |
| `mcp.py` | MCP tool results |
| `task_tracking.py` | Task status updates |
| `file_download.py` | Downloaded file notifications |
| `reject.py` | Rejected action notifications |

### Tool Definitions

**Tool schemas**: `openhands/agenthub/codeact_agent/tools/`

Tools are defined as OpenAI-format `ChatCompletionToolParam` dicts. Key files:

- **`bash.py`**: `create_cmd_run_tool()` -- params: `command` (str), `is_input` (bool enum), `timeout` (number), `security_risk` (enum). Supports short/long descriptions. Documents persistent shell sessions, `&&` chaining, `C-c` interruption.
- **`str_replace_editor.py`**: `create_str_replace_editor_tool()` -- commands: view, create, str_replace, insert, undo_edit. Params: `path`, `file_text`, `old_str`/`new_str`, `insert_line`, `view_range`. Enforces exact whitespace matching.
- **`browser.py`**: `BrowserTool` -- uses BrowserGym's `HighLevelActionSet` with 15 functions: goto, go_back, go_forward, click, dblclick, hover, fill, select_option, press, focus, clear, upload_file, scroll, noop, drag_and_drop. Param: `code` (Python string).
- **`ipython.py`**: `IPythonTool` -- param: `code` (Python string). Supports `%pip` magic.
- **`finish.py`**: `FinishTool` -- signals task completion
- **`think.py`**: `ThinkTool` -- internal reasoning
- **`llm_based_edit.py`**: `LLMBasedFileEditTool` -- alternative to str_replace
- **`task_tracker.py`**: `TaskTrackerTool` -- task planning/tracking
- **`condensation_request.py`**: `CondensationRequestTool` -- request context compression

All tools include a `security_risk` parameter with predefined risk level enums.

### Function Calling Pipeline

**File**: `openhands/agenthub/codeact_agent/function_calling.py`

`response_to_actions()` converts LLM responses to Action objects:

1. Extract `thought` from `assistant_msg.content`
2. Iterate `assistant_msg.tool_calls`
3. Parse `tool_call.function.arguments` via `json.loads()`
4. Match `tool_call.function.name` against registered tools
5. Validate required arguments per tool type
6. Construct corresponding Action objects
7. Apply security risk levels via `set_security_risk()`
8. Attach metadata (tool_call_id, response reference)

---

## 2. Sandbox (Docker Runtime)

### Architecture

**Key files:**
- `openhands/runtime/impl/docker/docker_runtime.py` -- Container lifecycle management
- `openhands/runtime/action_execution_server.py` -- FastAPI server running INSIDE the container
- `openhands/runtime/impl/action_execution/action_execution_client.py` -- HTTP client on the host

The sandbox is a **two-process architecture**:
1. **Host side**: `DockerRuntime` (extends `ActionExecutionClient`) manages container lifecycle and sends HTTP requests
2. **Container side**: `ActionExecutionServer` (FastAPI) receives actions, executes them, returns observations

### Container Creation

`DockerRuntime` allocates ports from defined ranges:
- Execution server: 30000-39999
- VSCode: 40000-49999
- App ports: 50000-59999

Container launch:
```python
self.docker_client.containers.run(
    image=self.runtime_container_image,
    init=True,  # tini init for signal handling / zombie reaping
    command=command,
    entrypoint=[],
    network_mode=network_mode,
    ports=port_mapping,
    volumes=volumes,
    mounts=overlay_mounts,
    device_requests=device_requests  # GPU support
)
```

**Port safety**: File-based `PortLock` objects prevent race conditions in concurrent port allocation.

### Command Execution Inside Container

The ActionExecutionServer exposes these endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/alive` | GET | Health check (no auth) |
| `/server_info` | GET | Uptime, idle time, resources (no auth) |
| `/execute_action` | POST | Execute any action, return observation |
| `/list_files` | POST | Directory listing |
| `/upload_file` | POST | Upload file or zip archive |
| `/download_files` | GET | Download path as zip |
| `/update_mcp_server` | POST | Update MCP tool configs |
| `/vscode/connection_token` | GET | VSCode auth token |

**`/execute_action`** is the main endpoint. It:
1. Receives `{"action": {...}}` JSON
2. Deserializes to Action object
3. Routes to handler by type: `run()`, `read()`, `write()`, `edit()`, `run_ipython()`, `browse()`, `browse_interactive()`
4. Returns serialized Observation

**Command execution** (`run`): Uses `BashSession` -- a persistent tmux-based shell that maintains state (env vars, cwd) across invocations. Supports timeout, `is_input` for feeding running processes, and `is_static` for isolated subprocess execution.

**File reading** (`read`): Handles text files with line ranges, plus base64-encoded binary (images, PDFs, videos).

**File writing** (`write`): Preserves original file permissions/ownership when editing existing files.

**File editing** (`edit`): Uses `OHEditor` for structured edits (view, create, str_replace, insert, undo_edit). Auto-generates diffs.

**IPython** (`run_ipython`): Routes to JupyterPlugin, syncs working directory between bash and Jupyter.

**Browser** (`browse`/`browse_interactive`): BrowserEnv with BrowserGym. Handles file downloads to `/workspace/.downloads`.

### Volume Mounting

Three mount types:
1. **Standard bind mounts**: Host path → container path (read/write)
2. **Named volumes**: Docker-managed volumes for non-absolute paths
3. **Overlay mounts**: Read-only lower dir with per-container copy-on-write upper/work layers

### Security Model

- **API key auth**: `X-Session-API-Key` header on all endpoints except health checks
- **Port isolation**: File-based locking prevents port collisions
- **Network isolation**: Optional host network mode (with warnings)
- **Memory limits**: `RUNTIME_MAX_MEMORY_GB` enforced by MemoryMonitor
- **Action semaphore**: `threading.Semaphore(1)` ensures single-action execution
- **Security risk assessment**: Actions tagged with risk levels, analyzed before execution

### Container Lifecycle

States: `STARTING_RUNTIME` -> `BUILDING_RUNTIME` (if needed) -> `RUNTIME_STARTED` -> `READY`

- `connect()`: Initialize and wait (120s retry, 2s intervals)
- `pause()/resume()`: Stop/start with environment preservation
- `close()`: Cleanup with optional container removal, port lock release
- Global shutdown listener stops all `openhands-runtime-*` containers on exit

---

## 3. Frontend

### Tech Stack

- React + TypeScript (24.4% of codebase)
- Tailwind CSS
- Socket.IO for WebSocket communication
- React Query for data fetching
- i18n for internationalization

### Directory Structure

```
frontend/src/
  api/              -- API integration layer
  assets/           -- Static resources
  components/
    features/       -- 30 feature modules (see below)
    providers/      -- React context providers
    shared/         -- Reusable components
    ui/             -- Base UI building blocks
    v1/             -- V1-specific components
  constants/
  context/          -- React Context API
  contexts/
  hooks/            -- Custom React hooks (WebSocket, events, etc.)
  i18n/             -- Internationalization
  icons/
  mocks/
  routes/
  services/
  stores/           -- State management
  types/
  ui/               -- Reusable UI library
  utils/
  wrapper/          -- HOCs
```

### Feature Components

The 30 feature modules under `components/features/`:

| Module | Purpose |
|---|---|
| `chat` | Conversation UI (main interaction panel) |
| `conversation` | Conversation management |
| `conversation-panel` | Conversation list/sidebar |
| `terminal` | Terminal view |
| `browser` | Browser preview panel |
| `files` | File browser |
| `diff-viewer` | Code diff display |
| `trajectory` | Agent action trajectory view |
| `controls` | Agent controls (start/stop/pause) |
| `sidebar` | Main navigation sidebar |
| `settings` | Configuration UI |
| `auth` | Authentication |
| `user` | User profile |
| `onboarding` | New user onboarding |
| `alerts` | Notification system |
| `feedback` | User feedback |
| `suggestions` | Action suggestions |
| `markdown` | Markdown rendering |
| `images` | Image display |
| `context-menu` | Right-click menus |
| `home` | Landing page |
| `tips` | Help tips |
| `analytics` | Usage analytics |
| `guards` | Route guards |
| `served-host` | Served app preview |
| `payment` | Payment handling |
| `org` | Organization management |
| `device-verify` | Device verification |
| `waitlist` | Waitlist management |
| `microagent-management` | Skill/microagent CRUD |

### WebSocket Event Streaming

**Core hooks:**
- `use-websocket.ts` -- Connection management, reconnection logic
- `use-handle-ws-events.ts` -- Event dispatching and UI updates
- `use-unified-websocket-status.ts` -- Connection status monitoring
- `use-filtered-events.ts` -- Event filtering
- `use-handle-runtime-active.ts` -- Runtime status monitoring

**WebSocket connection** (`use-websocket.ts`):
- Generic typed hook `<T = string>` for message payloads
- Auto-reconnect after 3000ms on abnormal close (code != 1000)
- `WeakSet` tracks reconnect-eligible socket instances
- Configurable `maxAttempts` for reconnection
- Cleanup disables reconnection on unmount

**Event handling** (`use-handle-ws-events.ts`):
- Monitors `events` array from event store
- Processes only the MOST RECENT event (`events[events.length - 1]`)
- Two event categories: `ServerError` (has `error` property) and typed events (`event.type`)
- Special handling for `401` (session expiration) and "Agent reached maximum" messages
- Errors displayed via `displayErrorToast()`
- Max iteration triggers `AgentState.PAUSED`

**Transport**: Socket.IO over WebSocket (via `socketio.ASGIApp` on the backend). Events flow bidirectionally -- actions from frontend, observations from backend.

### Server-Side Frontend Integration

**File**: `openhands/server/listen.py`

- FastAPI with Socket.IO ASGI wrapper
- `LocalhostCORSMiddleware` restricts to localhost
- `InMemoryRateLimiter` at 10 req/s per client
- Static file serving from `./frontend/build` when `SERVE_FRONTEND=true`
- WebSocket at `/ws` endpoint

### The Conversation UI

The chat component renders events as a conversation thread. Each event (action or observation) is rendered based on its type. The "Unknown event" display issue occurs when the frontend receives an event type it doesn't have a renderer for -- it just shows raw JSON or a generic message.

### The Preview Panel Problem

The browser/preview panel (`served-host` feature) is designed to show web apps the agent builds. Problems:
- Doesn't auto-detect when an app starts serving
- Requires manual URL entry or port discovery
- Port mapping through Docker adds latency
- No hot-reload integration
- The accessibility tree (axtree) representation is lossy and hard to debug visually

---

## 4. LLM Integration

### LiteLLM Usage

**File**: `openhands/llm/llm.py`

OpenHands uses LiteLLM as a universal LLM adapter. The `LLM` class wraps `litellm.completion` with:

```python
self._completion = partial(
    litellm_completion,
    model=self.config.model,
    api_key=...,
    base_url=self.config.base_url,
    ...
)
```

**Key features:**
- Retry logic via `RetryMixin`: retries on `APIConnectionError`, `RateLimitError`, `ServiceUnavailableError`, `BadGatewayError`, timeout, internal server errors
- Configurable backoff: min/max wait, exponential multiplier
- Token counting via `litellm.token_counter` with custom tokenizer fallback
- Cost tracking via `litellm_completion_cost`
- Prompt/response logging to files when enabled

### Native vs Mock Function Calling

**Native** (when model supports it):
- Tools passed directly to LiteLLM
- Model handles function calling natively
- Used for: GPT-4, Claude, Gemini, etc.

**Mocked** (via prompting):
- Tool definitions converted to in-context examples in the system prompt
- Stop words used when model supports them
- Non-function-call responses converted back to function-call format
- Used for: models without native tool support
- Disabled for `openhands-lm` models via `tool_choice='none'`

### Provider-Specific Handling

| Provider | Special Handling |
|---|---|
| Azure | Uses `max_tokens` instead of `max_completion_tokens` |
| Gemini 2.5 Pro | Maps `reasoning_effort` to thinking budget tokens |
| Claude Opus/Sonnet 4.x | Cannot accept both `temperature` and `top_p`; prefers temperature |
| Claude Opus 4.1 | Disables extended thinking |
| Mistral/Gemini | Supports `safety_settings` configuration |
| AWS Bedrock | Accepts region and credential parameters |
| LiteLLM Proxy | Fetches model info via HTTP from proxy endpoints |
| OpenHands Provider | Rewrites `openhands/` prefix to litellm_proxy with appropriate base URL |
| Hugging Face | Default `top_p` set to 0.9 |

### System Prompt

**Template**: `openhands/agenthub/codeact_agent/prompts/system_prompt.j2`

Jinja2 template covering 8 operational categories:
1. **Role**: Assist users by executing commands and solving technical problems
2. **Efficiency**: Combine actions, use `find`/`grep` to minimize operations
3. **File System**: Locate files first, modify originals directly, avoid multiple versions
4. **Code Quality**: Understand codebases before changes, organize imports
5. **Version Control**: Configure git credentials, exercise caution
6. **Pull Requests**: Don't push unless asked, one PR per session
7. **Problem-Solving**: Explore -> analyze -> test -> implement -> verify
8. **Security**: Via `{% include 'security_risk_assessment.j2' %}`

**Additional prompt templates** (10 total in the prompts directory):
- `system_prompt_interactive.j2` -- Interactive mode variant
- `system_prompt_long_horizon.j2` -- Extended planning variant
- `system_prompt_tech_philosophy.j2` -- Technical philosophy guidance
- `in_context_learning_example.j2` -- Few-shot examples
- `microagent_info.j2` -- Loaded skill/microagent content
- `additional_info.j2` -- Supplementary context
- `user_prompt.j2` -- User message formatting

### Context Management (Condensers)

**Directory**: `openhands/memory/condenser/impl/`

11 condenser implementations in a pipeline architecture:

| Condenser | Strategy |
|---|---|
| `no_op_condenser.py` | Pass-through, no compression |
| `recent_events_condenser.py` | Keep first N + last M events, drop middle |
| `observation_masking_condenser.py` | Replace old observations with `<MASKED>` placeholder, keep recent N in full |
| `llm_summarizing_condenser.py` | Use LLM to summarize forgotten events into a condensation observation |
| `llm_attention_condenser.py` | Use LLM attention to prioritize important events |
| `amortized_forgetting_condenser.py` | Gradual memory decay |
| `browser_output_condenser.py` | Special handling for verbose browser output |
| `conversation_window_condenser.py` | Sliding window of recent conversation |
| `structured_summary_condenser.py` | Structured summaries preserving key info |
| `pipeline.py` | Chain multiple condensers together |

**LLM Summarizing Condenser** (the main one):
- Triggers when `len(view) > max_size` or unhandled condensation request
- Partitions events into head (always kept), middle (summarized), tail (recent, kept)
- Prompts LLM to preserve critical info, especially task tracking sections and exact task IDs
- Summary becomes `AgentCondensationObservation` replacing forgotten events
- Returns `Condensation` object with boundaries and placement offset

**Observation Masking Condenser**:
- `attention_window` parameter (default: 5)
- Events outside window get content replaced with `<MASKED>`
- Cheap way to reduce token count without LLM calls

**Pipeline**: Chains condensers together -- e.g., mask observations first, then summarize if still too long.

---

## 5. What Makes OpenHands Good

### The Autonomous Error Loop

This is the killer feature. The agent:
1. Writes code
2. Runs it in the sandbox
3. Gets the error
4. Reads the error
5. Fixes the code
6. Runs again
7. Repeats until it works or hits iteration limit

This is possible because:
- **Real shell**: The sandbox runs actual bash, not simulated commands
- **Real tools**: npm, pip, gcc, cargo -- whatever you need is actually installed
- **Persistent state**: The tmux-based BashSession maintains env vars, cwd, running processes
- **Error output**: Full stdout/stderr comes back, not truncated summaries

### Docker Sandbox (Real Everything)

The sandbox is a full Linux container. The agent can:
- Install packages (`pip install`, `npm install`, `apt-get`)
- Run servers (`python -m http.server`, `npm run dev`)
- Use git (clone, commit, push)
- Run tests (pytest, jest, cargo test)
- Build projects (make, cmake, cargo build)
- Use Jupyter/IPython for data analysis

This is fundamentally different from "simulated" environments. When the agent runs `npm install && npm run build`, it's running real npm in a real Node.js environment.

### No XML Tag Dependency

Actions are native function calls (OpenAI tool format), not XML-wrapped strings. The LLM doesn't need to produce perfect XML -- it just fills in function parameters. This means:
- Fewer parsing failures
- Better compatibility across LLM providers
- Cleaner error handling
- No regex-based action extraction

### Tool Execution Design

Tools are cleanly separated:
- **Tool definition** (schema): `openhands/agenthub/codeact_agent/tools/*.py`
- **Action class** (data model): `openhands/events/action/*.py`
- **Execution handler** (runtime): `openhands/runtime/action_execution_server.py`
- **Result class** (observation): `openhands/events/observation/*.py`

This separation means you can add new tools without touching the agent loop.

### Security Analysis

Actions are tagged with risk levels before execution. The controller can pause and ask for user confirmation on risky operations. This is opt-in but well-designed.

### Delegation Pattern

The `AgentController` supports spawning child agent controllers (delegates). Parent and delegate share the same event stream, metrics, iteration count, and budget -- maintaining accountability across agent hierarchies.

---

## 6. What's Broken

### Slow (Many LLM Calls Per Task)

Every action requires a full LLM roundtrip. A simple "create a React app" task might take:
1. LLM call: decide to run `npx create-react-app`
2. LLM call: read the output, decide to `cd` into the directory
3. LLM call: decide to look at the files
4. LLM call: decide to edit `App.js`
5. LLM call: decide to run `npm start`
6. LLM call: check if it works
7. LLM call: decide to finish

That's 7+ LLM calls for a trivial task. Each call has latency (1-10s for cloud APIs). Total: 30-60 seconds for something a human does in 5 seconds.

### "Unknown Event" UI Display

When the frontend receives an event type it doesn't have a renderer for, it shows "Unknown event" with raw data. This happens with:
- `CondensationAction` events
- `TaskTrackingAction` events
- Custom MCP events
- Internal state events the user shouldn't see

The event handling only processes the MOST RECENT event (`events[events.length - 1]`), which means rapid-fire events can be missed or displayed incorrectly.

### Preview Panel Doesn't Auto-Show Apps

The `served-host` / browser preview panel has major UX issues:
- No auto-detection of when an app starts serving on a port
- User must manually discover the forwarded port and enter the URL
- Port mapping through Docker adds indirection and latency
- No hot-reload or live-refresh integration
- The BrowserGym accessibility tree is lossy -- you can't debug visual issues from it

### Context Overflow Loses Everything

When the context window fills up:
- The condenser fires and summarizes/truncates history
- But the summary is lossy -- file contents, exact error messages, and intermediate state are lost
- If the agent was in the middle of a multi-step fix, it may lose track of what it was doing
- The `ContextWindowExceededError` path tries condensation, but if condensation fails, it just errors out
- No incremental checkpointing of progress

### No Incremental Research Saving

When the agent researches a codebase (reading files, understanding architecture), all that knowledge exists only in the context window. If context overflows:
- All file contents are gone
- All understanding is gone
- The agent starts over from scratch
- No persistent scratchpad or knowledge base

### Stuck Loop Detection Is Reactive

The stuck detection in `_is_stuck()` only fires AFTER the agent has been looping. The recovery options (truncate history, restart with last message, stop) are all destructive. There's no proactive loop prevention.

### Heavy Dependencies

The full Docker image is large. BrowserGym adds Chromium. Jupyter adds kernel management. The action execution server is a full FastAPI app. Starting a sandbox takes noticeable time (seconds to tens of seconds depending on image pulls).

---

## 7. Skill System

### Overview

Skills (called "microagents" in V0) are markdown files that provide specialized knowledge and instructions to the agent. They're injected into the system prompt based on context.

**Two sources:**
1. **Public skills**: `OpenHands/skills/` -- 27 files, shared across all users
2. **Repository-specific skills**: `.openhands/skills/` (V1) or `.openhands/microagents/` (V0) -- per-project instructions

### Available Public Skills (27)

**Agent Management:**
- `add_agent.md` -- How to add new agents
- `add_repo_inst.md` -- Adding repository instructions
- `agent-builder.md` -- Building custom agents
- `agent_memory.md` -- Memory management

**Version Control & Code Review:**
- `github.md` -- GitHub operations
- `gitlab.md` -- GitLab operations
- `code-review.md` -- Code review practices
- `codereview-roasted.md` -- Aggressive code review style
- `address_pr_comments.md` -- Responding to PR feedback
- `update_pr_description.md` -- PR description formatting

**Infrastructure & DevOps:**
- `docker.md` -- Docker operations
- `kubernetes.md` -- K8s operations
- `azure_devops.md` -- Azure DevOps
- `bitbucket.md` -- Bitbucket cloud
- `bitbucket_data_center.md` -- Bitbucket Data Center
- `ssh.md` -- SSH operations

**Development Tools:**
- `npm.md` -- NPM/Node.js
- `swift-linux.md` -- Swift on Linux
- `pdflatex.md` -- LaTeX PDF generation
- `default-tools.md` -- Default tool descriptions

**Testing & Fixes:**
- `fix_test.md` -- Test debugging
- `fix-py-line-too-long.md` -- Python line length fixes
- `update_test.md` -- Test updates

**Specialized:**
- `security.md` -- Security practices
- `onboarding.md` -- New user setup
- `flarglebargle.md` -- Unknown/test skill

### How Skills Are Loaded

1. When OpenHands starts a session with a repository, it scans `.openhands/skills/` (or `.openhands/microagents/`)
2. Repository-specific skills are always loaded
3. Public skills are "knowledge agents" triggered by conversation keywords
4. Loaded skill content is injected via `microagent_info.j2` template into the system prompt
5. Skills are plain markdown -- no code execution, just instructions

### Skill Types

**Knowledge Agents** (keyword-triggered):
- Activated when specific keywords appear in conversation
- Provide language/framework best practices
- Reusable across projects
- Example: `github.md` activates when conversation mentions GitHub operations

**Repository Agents** (always-on):
- Auto-loaded for their specific repository
- Enforce team conventions
- Project-specific setup, testing, CI workflows

### How to Create New Skills

1. Create a markdown file with instructions
2. For public skills: PR to OpenHands repo, place in `skills/`
3. For repo-specific: place in `.openhands/skills/` (V1) or `.openhands/microagents/` (V0)
4. Skills are pure text -- they augment the system prompt, not the tool set

### Skills Are NOT Executable

Important distinction: skills are **prompt augmentation**, not **tool definitions**. A skill like `github.md` doesn't add a `create_pr()` tool -- it adds instructions to the system prompt telling the agent HOW to use existing tools (bash, file edit) to accomplish GitHub tasks. The agent still does everything through `execute_bash` (running `gh` CLI commands).

---

## 8. Architecture Summary: What to Keep vs Rewrite

### Keep (Core Strengths)

| Component | Why |
|---|---|
| Docker sandbox architecture | Real execution environment is the #1 feature |
| Action/Observation event model | Clean, extensible, well-separated |
| Tool definition format (OpenAI function calling) | Universal, well-supported by all LLMs |
| LiteLLM integration | Multi-provider support without custom code |
| Security risk tagging | Good foundation for user safety |
| Persistent bash session (tmux) | State preservation across commands |
| Skill system (markdown injection) | Simple, effective, extensible |

### Rewrite (Pain Points)

| Component | Problem | BoltHands Fix |
|---|---|---|
| Frontend event display | "Unknown event", missed events | Proper event type registry, render all events |
| Preview panel | No auto-detect, manual port entry | Auto-detect serving ports, iframe with hot-reload |
| Context management | Lossy condensation, no checkpoint | Persistent scratchpad, incremental saves |
| Agent loop efficiency | Too many LLM calls per task | Batch actions, multi-step planning, caching |
| Stuck detection | Reactive only | Proactive loop prevention, action deduplication |
| WebSocket event handling | Only processes latest event | Event queue with guaranteed delivery |
| Container startup time | Slow image pulls, heavy deps | Pre-built slim images, lazy loading |
| Condenser system | Complex pipeline, still loses info | Structured memory with retrieval, not summarization |

### V1 Migration Notes

OpenHands is migrating to V1 with "Software Agent SDK" -- the V0 code analyzed here is scheduled for removal April 1, 2026. V1 uses:
- New application server at `openhands/app_server/`
- Different agent architecture
- Skills instead of microagents terminology

For BoltHands, we should study V0's battle-tested patterns but build on V1's direction where it makes sense. The core sandbox + event model + tool system design is solid regardless of version.
