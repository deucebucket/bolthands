# Frontend IDE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the BoltHands web IDE — a Remix/React app with chat, code editor, terminal, and live preview, connected to the agent backend via WebSocket.

**Architecture:** Remix app with nanostores for state, WebSocket for real-time events, CodeMirror for editing, xterm.js for terminal, iframe for preview. All execution happens on the backend — frontend is pure presentation + event routing.

**Tech Stack:** Remix v2, React 18, TypeScript, Nanostores, CodeMirror 6, xterm.js, react-resizable-panels, UnoCSS, Vitest

**Spec:** `docs/superpowers/specs/2026-03-20-frontend-ide-design.md`

---

## File Map

```
frontend/
  package.json
  tsconfig.json
  vite.config.ts
  uno.config.ts
  app/
    root.tsx
    entry.client.tsx
    entry.server.tsx
    routes/
      _index.tsx
    components/
      layout/
        Header.tsx
        SplitLayout.tsx
      chat/
        Chat.tsx
        ChatMessage.tsx
        ChatInput.tsx
        ActionStatus.tsx
      workbench/
        Workbench.tsx
        EditorPanel.tsx
        FileTree.tsx
        CodeEditor.tsx
        TerminalPanel.tsx
        PreviewPanel.tsx
    stores/
      agent.ts
      files.ts
      terminal.ts
      chat.ts
      preview.ts
    lib/
      websocket.ts
      event-handler.ts
      types.ts
    styles/
      global.css
```

Build order: project scaffold → types + stores → WebSocket + event handler → layout → chat components → workbench components → wiring + integration

---

### Task 1: Scaffold Remix project with dependencies

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/uno.config.ts`
- Create: `frontend/app/root.tsx`
- Create: `frontend/app/entry.client.tsx`
- Create: `frontend/app/entry.server.tsx`
- Create: `frontend/app/styles/global.css`

- [ ] **Step 1: Create package.json with all dependencies**

Dependencies: @remix-run/node, @remix-run/react, @remix-run/serve, react, react-dom, nanostores, @nanostores/react, @codemirror/state, @codemirror/view, @codemirror/lang-javascript, @codemirror/lang-python, @codemirror/theme-one-dark, @xterm/xterm, @xterm/addon-fit, react-resizable-panels, @unocss/remix

DevDependencies: @remix-run/dev, vite, typescript, unocss, vitest, @testing-library/react, @types/react, @types/react-dom

- [ ] **Step 2: Create tsconfig.json, vite.config.ts, uno.config.ts**

Standard Remix + Vite + UnoCSS config. UnoCSS with dark theme defaults.

- [ ] **Step 3: Create root.tsx with dark theme**

Standard Remix root with Links, Meta, Outlet. Import global.css. Set html class="dark" and bg-neutral-950 text-white.

- [ ] **Step 4: Create global.css with BoltHands dark theme**

CSS variables for colors: --bg-primary: #0a0a0a, --bg-secondary: #141414, --bg-tertiary: #1e1e1e, --border: #2a2a2a, --accent: #3b82f6, --success: #22c55e, --error: #ef4444, --warning: #eab308. Font: JetBrains Mono for code, Inter/system for UI. Scrollbar styling. Base reset.

- [ ] **Step 5: Create entry.client.tsx and entry.server.tsx**

Standard Remix entry files.

- [ ] **Step 6: Install dependencies and verify build**

Run: `cd frontend && npm install && npm run build`

- [ ] **Step 7: Commit**

---

### Task 2: Types, stores, and WebSocket client

**Files:**
- Create: `frontend/app/lib/types.ts`
- Create: `frontend/app/lib/websocket.ts`
- Create: `frontend/app/lib/event-handler.ts`
- Create: `frontend/app/stores/agent.ts`
- Create: `frontend/app/stores/files.ts`
- Create: `frontend/app/stores/terminal.ts`
- Create: `frontend/app/stores/chat.ts`
- Create: `frontend/app/stores/preview.ts`

- [ ] **Step 1: Create types.ts**

TypeScript interfaces: AgentEvent, ActionData (discriminated union by type field), ObservationData, AgentStatus, ChatMessage, TerminalLine, FileNode, TreeNode.

- [ ] **Step 2: Create all 5 stores**

Using nanostores atom/map:
- agent.ts: taskId, status, events array, iteration
- files.ts: fileMap (Record<string, FileNode>), activeFile, methods: setFile, editFile, getTree
- terminal.ts: lines array, methods: addCommand, addOutput
- chat.ts: messages array, inputValue, isSubmitting, methods: addUserMessage, addAction, updateActionStatus
- preview.ts: detectedPorts array, activePort, previewUrl computed

- [ ] **Step 3: Create websocket.ts**

WebSocket client class: connect(taskId), disconnect(), onEvent callback. Auto-reconnect on abnormal close. Parses JSON events.

- [ ] **Step 4: Create event-handler.ts**

Routes AgentEvent to correct store updates. Switch on event.type and data.type. This is the bridge between WebSocket and UI state.

- [ ] **Step 5: Commit**

---

### Task 3: Layout shell (Header + SplitLayout + route)

**Files:**
- Create: `frontend/app/components/layout/Header.tsx`
- Create: `frontend/app/components/layout/SplitLayout.tsx`
- Create: `frontend/app/routes/_index.tsx`

- [ ] **Step 1: Create Header.tsx**

Top bar with: BoltHands logo/text (left), task status indicator (center), iteration counter (right). Uses useStore from nanostores to read agent status.

- [ ] **Step 2: Create SplitLayout.tsx**

Uses react-resizable-panels: PanelGroup with two Panels. Left panel renders children[0] (chat), right panel renders children[1] (workbench). Right panel starts collapsed/hidden and expands when workbench has content (controlled by a store value).

- [ ] **Step 3: Create _index.tsx route**

Renders Header + SplitLayout with Chat (left) and Workbench (right). Client-only rendering for browser APIs (WebSocket, CodeMirror, xterm).

- [ ] **Step 4: Verify it renders**

Run: `npm run dev`, open browser, see the empty shell with header and split panes.

- [ ] **Step 5: Commit**

---

### Task 4: Chat components

**Files:**
- Create: `frontend/app/components/chat/Chat.tsx`
- Create: `frontend/app/components/chat/ChatMessage.tsx`
- Create: `frontend/app/components/chat/ChatInput.tsx`
- Create: `frontend/app/components/chat/ActionStatus.tsx`

- [ ] **Step 1: Create ChatInput.tsx**

Text area + submit button. On submit: calls POST /task to backend, gets task_id, stores in agent store, connects WebSocket. Disabled while agent is running.

- [ ] **Step 2: Create ActionStatus.tsx**

Small component showing tool call status: icon + name + badge. Pending=gray, running=blue pulse, done=green check, error=red x. Expandable on click to show args/output.

- [ ] **Step 3: Create ChatMessage.tsx**

Renders a single message. User messages: right-aligned with blue bg. Assistant text: left-aligned with dark bg, markdown rendered. Tool calls: rendered as ActionStatus cards inline.

- [ ] **Step 4: Create Chat.tsx**

Container: scrollable message list + ChatInput at bottom. Reads from chat store. Auto-scrolls to bottom on new messages.

- [ ] **Step 5: Commit**

---

### Task 5: Workbench — Editor, Terminal, Preview

**Files:**
- Create: `frontend/app/components/workbench/Workbench.tsx`
- Create: `frontend/app/components/workbench/EditorPanel.tsx`
- Create: `frontend/app/components/workbench/FileTree.tsx`
- Create: `frontend/app/components/workbench/CodeEditor.tsx`
- Create: `frontend/app/components/workbench/TerminalPanel.tsx`
- Create: `frontend/app/components/workbench/PreviewPanel.tsx`

- [ ] **Step 1: Create Workbench.tsx**

Tabbed container with 3 tabs: Code, Terminal, Preview. Shows active tab's panel. Tab bar at top with tab buttons.

- [ ] **Step 2: Create FileTree.tsx**

Renders file tree from files store. Collapsible folders, clickable files. Sets activeFile in store on click. Simple recursive component.

- [ ] **Step 3: Create CodeEditor.tsx**

CodeMirror 6 wrapper. Reads content from files store for activeFile. Uses one-dark theme. Language detection by file extension (js/ts/py/json/md/css/html). Read-only while agent is running.

- [ ] **Step 4: Create EditorPanel.tsx**

Split: FileTree (left, narrow) + CodeEditor (right, wide). Uses react-resizable-panels.

- [ ] **Step 5: Create TerminalPanel.tsx**

xterm.js instance. Reads from terminal store. Writes each command as green "$ command" line, output as white, errors as red. Auto-scrolls. Fit addon for responsive sizing.

- [ ] **Step 6: Create PreviewPanel.tsx**

iframe pointing at preview URL from store. Shows "No preview available — the agent hasn't started a server yet" placeholder when no port detected. Refresh button. Port selector dropdown if multiple ports detected.

- [ ] **Step 7: Commit**

---

### Task 6: Full wiring and integration

**Files:**
- Modify: `frontend/app/routes/_index.tsx` — wire everything together
- Modify: stores as needed for final integration

- [ ] **Step 1: Wire _index.tsx**

Import all components. Render: Header, SplitLayout with Chat (left) and Workbench (right). Workbench shows/hides based on agent having file events.

- [ ] **Step 2: Wire ChatInput submit to backend**

On submit: POST to configurable backend URL (default http://localhost:8000/task), get task_id, connect WebSocket, start receiving events.

- [ ] **Step 3: Wire event-handler to all stores**

Ensure events flow from WebSocket -> event-handler -> stores -> components reactively.

- [ ] **Step 4: Test end-to-end manually**

Start backend: `bolthands serve --port 8000`
Start frontend: `cd frontend && npm run dev`
Open browser, type a task, verify: chat shows messages, terminal shows commands, editor shows files, preview detects ports.

- [ ] **Step 5: Commit and push**

---
