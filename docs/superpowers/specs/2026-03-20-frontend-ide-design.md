# BoltHands Frontend IDE — Design Spec

**Date:** 2026-03-20
**Goal:** Remix/React web IDE that connects to the BoltHands agent backend via WebSocket, providing chat, code editor, terminal, and live preview in a sleek split-pane layout.

---

## Overview

The frontend is a browser-based IDE inspired by Bolt.diy's layout but rebranded and streamlined for BoltHands. It connects to the FastAPI agent backend via WebSocket for real-time event streaming. No WebContainer — all execution happens in Docker via the backend.

## What We Keep from Bolt.diy

- Split-pane layout: chat (left) + workbench (right)
- CodeMirror 6 code editor with syntax highlighting
- File tree with expand/collapse
- xterm.js terminal showing command output
- Live iframe preview with port auto-detection
- Action status indicators in chat (pending/running/complete/failed)
- Workbench auto-opens when first file action arrives
- Sequential action rendering (files appear as they stream)
- File locking (prevent agent from overwriting user edits)

## What We Change

- WebContainer replaced by Docker sandbox (via backend WebSocket)
- One-shot LLM replaced by iterative agent loop (auto error recovery)
- Vercel AI SDK replaced by direct WebSocket to our FastAPI /ws endpoint
- No 22 LLM providers — single llama.cpp backend
- No Supabase, no mobile app instructions, no device frames, no Electron
- Rebranded: BoltHands identity, sleeker dark theme

## Tech Stack

- Remix v2 + React 18 + TypeScript
- Nanostores for state management (same as Bolt.diy — lightweight, works with React)
- CodeMirror 6 for code editor
- xterm.js for terminal
- react-resizable-panels for split panes
- UnoCSS for utility styling
- Native WebSocket (no socket.io needed)

## Module Structure

```
app/
  routes/
    _index.tsx                 # Landing / main page
    api.health.ts              # Health check endpoint
  components/
    chat/
      Chat.tsx                 # Chat panel — message list + input
      ChatMessage.tsx          # Single message (user or assistant)
      ChatInput.tsx            # Text input + submit button
      ActionStatus.tsx         # Tool call status indicator (pending/running/done/error)
    workbench/
      Workbench.tsx            # Right panel container — tabs for code/terminal/preview
      EditorPanel.tsx          # File tree + CodeMirror editor
      FileTree.tsx             # Collapsible file/folder tree
      CodeEditor.tsx           # CodeMirror 6 wrapper
      TerminalPanel.tsx        # xterm.js terminal showing agent commands
      PreviewPanel.tsx         # Live iframe preview with port detection
    layout/
      Header.tsx               # Top bar — logo, task status, settings
      SplitLayout.tsx          # Left (chat) + right (workbench) resizable
  stores/
    agent.ts                   # Agent state: task_id, status, events
    files.ts                   # File map from agent actions
    terminal.ts                # Terminal output lines
    editor.ts                  # Active file, cursor position
    preview.ts                 # Preview URL, detected ports
    chat.ts                    # Messages list, input state
  lib/
    websocket.ts               # WebSocket client for /ws/{task_id}
    event-handler.ts           # Route WebSocket events to stores
    types.ts                   # Shared TypeScript types
  styles/
    global.css                 # Global styles, dark theme, BoltHands branding
```

## Components

### 1. SplitLayout

Two resizable panels using react-resizable-panels:
- Left panel (35% default): Chat
- Right panel (65% default): Workbench (hidden until first file action)

Workbench slides open with CSS transition when first file write or command execution arrives.

### 2. Chat Panel

Message list showing the conversation:
- User messages: styled as sent messages (right-aligned or distinct bg)
- Assistant text: markdown-rendered responses
- Tool calls: compact action cards showing:
  - Tool icon + name (bash, read_file, write_file, etc.)
  - Status badge: pending (gray), running (blue pulse), done (green check), error (red x)
  - Expandable: click to see arguments and output
  - Auto-scroll to bottom on new messages

Input area: text input + submit button. On submit, POST /task to backend, get task_id, connect WebSocket.

### 3. Workbench (tabbed)

Three tabs: Code | Terminal | Preview

**Code tab:**
- Left: FileTree — built from file write/edit events. Shows files the agent has created or modified.
- Right: CodeEditor — CodeMirror 6 with the selected file's content. Read-only by default (agent is writing), but user can toggle to edit mode (file locking).
- Files update live as agent writes them.

**Terminal tab:**
- xterm.js showing all bash commands the agent runs and their output.
- Each command shown as: `$ command\noutput\n` with color coding (green prompt, white output, red errors).

**Preview tab:**
- iframe pointing at the detected dev server URL.
- Port detection: when agent runs a dev server (npm run dev, python -m http.server, etc.), parse the terminal output for "listening on port XXXX" patterns.
- Since Docker uses host networking, the preview URL is just `http://localhost:{port}`.
- Auto-refresh when files change.
- Show "No preview available" placeholder until a port is detected.

### 4. WebSocket Client

Connects to `ws://localhost:8000/ws/{task_id}` after task creation.

Receives event envelopes:
```typescript
interface AgentEvent {
  type: "action" | "observation" | "state_change" | "error";
  timestamp: string;
  iteration: number;
  data: ActionData | ObservationData | StateData | ErrorData;
}
```

Routes events to stores via event-handler.ts:
- action with type "cmd_run" -> add to terminal store + chat store
- action with type "file_write" -> update files store, show in editor
- action with type "file_edit" -> update files store
- observation with type "cmd_output" -> append output to terminal, update action status
- observation with type "file_content" -> update files store
- state_change -> update agent store (running/finished/error)
- error -> show error in chat

### 5. Stores (Nanostores)

**agent.ts:**
- taskId: string | null
- status: AgentStatus (idle/running/finished/error)
- iteration: number
- events: AgentEvent[]

**files.ts:**
- fileMap: Record<string, {content: string, locked: boolean}>
- fileTree: TreeNode[] (computed from fileMap)
- activeFile: string | null

**terminal.ts:**
- lines: TerminalLine[] ({command, output, exitCode, timestamp})

**chat.ts:**
- messages: ChatMessage[] ({role, content, actions?})
- inputValue: string
- isSubmitting: boolean

**preview.ts:**
- detectedPorts: number[]
- activePort: number | null
- previewUrl: string | null

### 6. Event Handler

Maps WebSocket events to store updates:

```typescript
function handleEvent(event: AgentEvent) {
  agentStore.addEvent(event);

  switch (event.type) {
    case "action":
      handleAction(event.data);
      break;
    case "observation":
      handleObservation(event.data);
      break;
    case "state_change":
      agentStore.setStatus(event.data);
      break;
  }
}

function handleAction(data: ActionData) {
  chatStore.addAction(data);  // show in chat as action card

  if (data.type === "cmd_run") {
    terminalStore.addCommand(data.command);
  } else if (data.type === "file_write") {
    fileStore.setFile(data.path, data.content);
  } else if (data.type === "file_edit") {
    fileStore.editFile(data.path, data.old_str, data.new_str);
  }
}

function handleObservation(data: ObservationData) {
  chatStore.updateLastAction(data);  // update status badge

  if (data.type === "cmd_output") {
    terminalStore.addOutput(data.stdout, data.stderr, data.exit_code);
    previewStore.detectPorts(data.stdout + data.stderr);
  }
}
```

### 7. Branding & Theme

- Dark theme (near-black background, subtle borders)
- BoltHands logo in header
- Accent color: electric blue (#3b82f6) for active states
- Monospace font for code/terminal: JetBrains Mono or Fira Code
- Clean, minimal chrome — let the content breathe
- Status colors: green (success), red (error), blue (running), gray (pending), yellow (warning)

## Data Flow

```
User types task in ChatInput
  |
  v POST /task to backend
Backend returns task_id
  |
  v Connect WebSocket /ws/{task_id}
  |
  v Events stream in:
  |
  +-> action:cmd_run -> terminalStore + chatStore
  +-> observation:cmd_output -> terminalStore + chatStore status
  +-> action:file_write -> fileStore + editorStore
  +-> action:file_edit -> fileStore
  +-> observation:cmd_output with port -> previewStore
  +-> state_change:finished -> agentStore, show summary
  +-> state_change:error -> agentStore, show error
```

## API Integration

The frontend talks to the backend at a configurable URL (default http://localhost:8000):
- POST /task — start a task
- GET /task/{id}/status — poll status (fallback if WS disconnects)
- DELETE /task/{id} — cancel task
- WS /ws/{id} — real-time event stream

No other backend calls needed. All file content comes through WebSocket events.

## Testing

- Component tests with Vitest + React Testing Library
- Store tests: verify event routing updates stores correctly
- WebSocket mock: simulate event streams, verify UI updates
- No E2E tests in v1 (manual testing against running backend)

## Out of Scope

- User authentication (single-user local app)
- Multiple concurrent tasks (one task at a time for v1)
- Project persistence / history (files live only during task)
- Git integration (future)
- Mobile responsive (desktop-first)
