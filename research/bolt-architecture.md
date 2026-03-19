# Bolt.diy Architecture Deep Dive

**Source**: https://github.com/stackblitz-labs/bolt.diy (cloned 2026-03-18)
**Purpose**: Reference for BoltHands fork — what to keep, rewrite, or throw away.

---

## 1. UI Architecture

### Framework Stack

Bolt.diy is a **Remix** (v2.15) app running on **Vite**, deployable to Cloudflare Pages or as an **Electron** desktop app. The frontend is React 18 with:

- **Nanostores** (`nanostores` + `@nanostores/react`) for global state — NOT Redux/Zustand for the core stores
- **Framer Motion** for animations (workbench open/close, view transitions)
- **UnoCSS** for utility CSS (not Tailwind directly, but UnoCSS with Tailwind-compatible classes)
- **CodeMirror 6** for the code editor (`@codemirror/*` packages)
- **xterm.js** for the terminal (`@xterm/xterm`)
- **react-resizable-panels** for the split-pane layout
- **Radix UI** primitives for dropdowns, dialogs, tabs, tooltips, etc.
- **Headless UI** (`@headlessui/react`) for some popovers

### Entry Point & Routing

```
app/routes/_index.tsx          → Landing page, renders Header + Chat (client-only)
app/routes/chat.$id.tsx        → Chat page (just re-exports _index with an id param)
app/routes/api.chat.ts         → The LLM streaming endpoint (POST)
app/routes/api.models.ts       → Model list endpoint
app/routes/api.enhancer.ts     → Prompt enhancement endpoint
app/routes/webcontainer.preview.$id.tsx → Preview iframe proxy
```

**File**: `app/routes/_index.tsx` (lines 20-28)
The index route renders `<Header />` + `<Chat />` wrapped in `<ClientOnly>`. The `Chat` component is the main orchestrator.

### The Split-Pane Layout

The layout is **Chat (left) + Workbench (right)**, NOT a traditional three-panel layout. The structure:

```
BaseChat (app/components/chat/BaseChat.tsx)
├── Menu (sidebar, client-only)
├── Chat panel (left)
│   ├── Messages list (scrollable)
│   ├── Alert bars (action/deploy/supabase/llm errors)
│   ├── ChatBox (input area with model selector)
│   └── StarterTemplates + ExamplePrompts (pre-chat only)
└── Workbench (right, client-only)
    ├── Toolbar (Code/Diff/Preview slider, sync/terminal buttons)
    └── Three animated views (only one visible):
        ├── EditorPanel (file tree + code editor + terminal)
        ├── DiffView (file change viewer)
        └── Preview (iframe with dev server)
```

**File**: `app/components/workbench/Workbench.client.tsx` (lines 283-515)
The Workbench uses `motion.div` with `variants` for open/close animation. Width is controlled by CSS variable `--workbench-width`. The three views (code/diff/preview) are positioned absolutely and animated with `motion.div` x-transforms.

**File**: `app/components/workbench/EditorPanel.tsx` (lines 47-100)
The EditorPanel uses `react-resizable-panels` (`PanelGroup` + `Panel`) for:
- **Left panel** (20% default, collapsible): File tree with tabs for Files/Search/Lock
- **Right panel**: CodeMirror editor with breadcrumb
- **Bottom panel** (togglable): Terminal tabs

### File Tree

**File**: `app/components/workbench/FileTree.tsx` (not read in full, but referenced)
The file tree reads from `workbenchStore.files` (a nanostores `MapStore<FileMap>`). It displays the WebContainer's filesystem, with file/folder CRUD operations and lock indicators.

### Preview iframe

**File**: `app/components/workbench/Preview.tsx` (lines 55-1049)
The preview renders an `<iframe>` pointing at the WebContainer's dev server URL. Key details:

- URL format: `https://{previewId}.local-credentialless.webcontainer-api.io`
- Sandbox: `allow-scripts allow-forms allow-popups allow-modals allow-storage-access-by-user-activation allow-same-origin`
- Has device mode (iPhone/iPad/laptop frames), responsive resize handles, inspector mode
- Inspector mode uses `postMessage` to communicate with an injected inspector script
- Port dropdown allows switching between multiple running servers
- Device frames are rendered as CSS-styled containers around the iframe

**File**: `app/lib/stores/previews.ts` (lines 20-313)
The `PreviewsStore` listens for WebContainer `server-ready` and `port` events. Uses `BroadcastChannel` for cross-tab preview sync and localStorage synchronization.

---

## 2. Prompt System

### System Prompt

**File**: `app/lib/common/prompts/prompts.ts` (lines 6-715)
The `getSystemPrompt()` function returns a massive string (~700 lines) containing:

1. **System constraints** — Tells the LLM it's in WebContainer (no native binaries, no pip, no g++, no git, limited Python stdlib). Lists available shell commands.
2. **Database instructions** — Supabase-first, with RLS requirements, migration file format, dual action pattern (migration file + query execution).
3. **Artifact instructions** — The critical `<boltArtifact>` and `<boltAction>` XML tag format:
   - `<boltArtifact id="..." title="..." type="...">` wraps a set of actions
   - `<boltAction type="file" filePath="...">` — writes a file
   - `<boltAction type="shell">` — runs a shell command
   - `<boltAction type="start">` — starts the dev server
   - `<boltAction type="supabase" operation="migration|query">` — database ops
4. **Design instructions** — Color system, typography, spacing, responsive design guidelines, user-provided design scheme injection.
5. **Mobile app instructions** — Expo/React Native specific guidance.
6. **Examples** — Three example interactions showing proper artifact format.

Key constants from `app/utils/constants.ts`:
- `WORK_DIR = "/home/project"` — the working directory in WebContainer
- `DEFAULT_MODEL = "claude-3-5-sonnet-latest"`

### PromptLibrary

**File**: `app/lib/common/prompt-library.ts` (lines 21-65)
Three prompt variants:

| ID | Label | Source |
|---|---|---|
| `default` | "Default Prompt" | `getFineTunedPrompt()` from `prompts/new-prompt.ts` |
| `original` | "Old Default Prompt" | `getSystemPrompt()` from `prompts/prompts.ts` |
| `optimized` | "Optimized Prompt (experimental)" | `optimized()` from `prompts/optimized.ts` |

Selection is via `promptId` parameter passed from the client. The `getPropmtFromLibrary` method (note: typo in source) picks the prompt.

### CONTINUE_PROMPT

**File**: `app/lib/common/prompts/prompts.ts` (lines 711-714)
When the model hits the token limit and `finishReason === 'length'`, the system injects:
```
Continue your prior response. IMPORTANT: Immediately begin from where you left off without any interruptions.
Do not repeat any content, including artifact and action tags.
```

This is handled in `app/routes/api.chat.ts` (line 252-283) with a `SwitchableStream` that allows up to `MAX_RESPONSE_SEGMENTS` continuations.

---

## 3. Message Parsing — XML Tags to Actions

This is the core magic of Bolt. The LLM outputs free-form markdown mixed with XML tags, and the parser turns them into file writes and shell commands.

### StreamingMessageParser

**File**: `app/lib/runtime/message-parser.ts` (lines 76-416)

The parser is a **character-by-character streaming state machine**. Key state:

```typescript
interface MessageState {
  position: number;       // cursor position in the input
  insideArtifact: boolean;
  insideAction: boolean;
  currentArtifact?: BoltArtifactData;
  currentAction: BoltActionData;
  actionId: number;
}
```

**Tag constants** (lines 6-9):
```
ARTIFACT_TAG_OPEN = '<boltArtifact'
ARTIFACT_TAG_CLOSE = '</boltArtifact>'
ARTIFACT_ACTION_TAG_OPEN = '<boltAction'
ARTIFACT_ACTION_TAG_CLOSE = '</boltAction>'
```

**Parse flow**:
1. Scan for `<boltArtifact` — extract `title`, `type`, generate `artifactId`, fire `onArtifactOpen` callback
2. Inside artifact, scan for `<boltAction` — extract `type`, `filePath`, fire `onActionOpen`
3. Inside action, accumulate content until `</boltAction>` — fire `onActionStream` for file actions (live preview), then `onActionClose`
4. After `</boltArtifact>` — fire `onArtifactClose`
5. Non-artifact text passes through as markdown output

**Important**: File content is cleaned of markdown code block syntax (`cleanoutMarkdownSyntax`, line 60) and escaped HTML tags (`cleanEscapedTags`, line 73). This handles models that wrap file content in ``` blocks.

Also handles `<bolt-quick-actions>` blocks (lines 103-131) for suggested follow-up actions.

### EnhancedStreamingMessageParser

**File**: `app/lib/runtime/enhanced-message-parser.ts` (lines 11-80+)

Extends `StreamingMessageParser` to handle models that DON'T output proper `<boltArtifact>` tags. It:

1. Runs the normal parse first
2. If NO artifacts detected, scans for code blocks with file path patterns
3. Detects shell commands via a pattern map (npm, git, docker, etc.)
4. Wraps detected code blocks in synthetic `<boltArtifact>` + `<boltAction>` tags
5. Re-parses the enhanced input

This is the fix for issue #1797 where local models output code to chat instead of files.

### useMessageParser Hook

**File**: `app/lib/hooks/useMessageParser.ts` (lines 1-80)

Creates a singleton `EnhancedStreamingMessageParser` and wires the callbacks to `workbenchStore`:

- `onArtifactOpen` → `workbenchStore.showWorkbench.set(true)` + `addArtifact()`
- `onActionOpen` → `addAction()` for file actions only (streamed)
- `onActionClose` → `addAction()` for non-file actions + `runAction()` for all
- `onActionStream` → `runAction(data, true)` (streaming mode)

---

## 4. Action Execution Pipeline

### WorkbenchStore

**File**: `app/lib/stores/workbench.ts` (lines 38-944)

The central orchestrator. Key flow:

1. `addArtifact()` — creates an `ArtifactState` with a new `ActionRunner` instance
2. `addAction()` / `runAction()` — queued via `#globalExecutionQueue` (sequential Promise chain)
3. `_runAction()` — for file actions: updates editor, saves to WebContainer. For shell/start actions: delegates to `ActionRunner`.

**File**: `app/lib/runtime/action-runner.ts` (lines 66-760)

The `ActionRunner` handles execution:

- **File actions** (`#runFileAction`): Creates directories (`mkdir -p`) then writes file via `webcontainer.fs.writeFile()`
- **Shell actions** (`#runShellAction`): Executes via `BoltShell.executeCommand()`. Pre-validates commands (fixes `rm` without `-f`, creates missing `cd` targets, etc.)
- **Start actions** (`#runStartAction`): Same as shell but non-blocking (2s delay between starts)
- **Build actions** (`#runBuildAction`): Runs `npm run build`, scans for output directory
- **Supabase actions**: Shows alerts, creates migration files

Error handling: `ActionCommandError` with enhanced error messages for common failures (file not found, permission denied, command not found, etc.). Errors trigger `onAlert` callbacks that show the `ChatAlert` component.

### Execution Queue

The `#globalExecutionQueue` in `WorkbenchStore` ensures actions execute **sequentially** — critical because file writes must complete before shell commands that reference them. The `actionStreamSampler` (line 603) throttles streaming file updates to 100ms intervals.

---

## 5. WebContainer

### Boot & Setup

**File**: `app/lib/webcontainer/index.ts` (lines 1-65)

```typescript
WebContainer.boot({
  coep: 'credentialless',
  workdirName: WORK_DIR_NAME,  // 'project'
  forwardPreviewErrors: true,
});
```

After boot:
1. Loads and sets an inspector script (`/inspector-script.js`) via `setPreviewScript()`
2. Listens for `preview-message` events (uncaught exceptions, unhandled rejections)
3. Stores instance as a module-level `Promise<WebContainer>`

### What WebContainer Can Do
- Run Node.js, npm, Python (stdlib only)
- File system operations (read/write/mkdir/rm)
- Run web servers (Vite, serve, etc.)
- Serve content through iframe via `*.local-credentialless.webcontainer-api.io` URLs
- zsh-like shell (limited command set listed in the system prompt)
- Watch file changes via `watchPaths()`

### What WebContainer CANNOT Do
- Run native binaries (no C/C++ compilation, no pip packages)
- Git operations
- Full Linux (no systemd, no full POSIX)
- Diff/patch editing (always full file rewrites)
- Run Docker
- Access the real filesystem

### FilesStore

**File**: `app/lib/stores/files.ts` (lines 47-952)

The `FilesStore` wraps the WebContainer filesystem with:
- A nanostores `MapStore<FileMap>` mirroring the WC filesystem
- File watching via `webcontainer.internal.watchPaths()` with 100ms buffering
- Binary file detection (using `istextorbinary`)
- File modification tracking (for sending diffs to the LLM)
- File/folder locking system (persisted to localStorage, per-chat)
- Deleted paths tracking (persisted to localStorage)

### Preview Rendering

The dev server runs inside WebContainer. When it starts listening on a port, WebContainer fires a `server-ready` event. The `PreviewsStore` captures this and provides the URL to the `Preview` component, which renders it in an iframe. The iframe gets a special `*.webcontainer-api.io` URL that the WebContainer runtime proxies.

**The preview "just works" because**: the dev server (Vite, etc.) runs in the browser's WebContainer, outputs to a virtual port, and WebContainer maps that port to a real URL that the iframe can load.

---

## 6. LLM Integration

### Provider Abstraction

**File**: `app/lib/modules/llm/base-provider.ts` (lines 10-183)
**File**: `app/lib/modules/llm/manager.ts` (lines 8-212)
**Providers**: `app/lib/modules/llm/providers/` — 22 provider files

The `BaseProvider` abstract class defines:
- `name`, `staticModels[]`, `config` (baseUrlKey, apiTokenKey, baseUrl)
- `getModelInstance()` — returns a Vercel AI SDK `LanguageModelV1`
- `getProviderBaseUrlAndKey()` — resolves API key from cookies → env → process.env
- Optional `getDynamicModels()` — fetches model lists from API
- Docker URL rewriting (`localhost` → `host.docker.internal`)
- Model caching

The `LLMManager` is a singleton that registers all providers from `app/lib/modules/llm/providers/registry.ts`. Providers include: OpenAI, Anthropic, Google, Groq, Ollama, LM Studio, OpenRouter, HuggingFace, Deepseek, Together, Mistral, Cohere, Amazon Bedrock, xAI, Fireworks, Hyperbolic, Cerebras, Moonshot, Perplexity, GitHub, and more.

**Key pattern**: All providers use `getOpenAILikeModel()` from `base-provider.ts` for OpenAI-compatible APIs, or their respective `@ai-sdk/*` packages.

### Streaming Pipeline

**File**: `app/routes/api.chat.ts` (lines 42-463)

The chat endpoint:

1. Extracts `messages`, `files`, `promptId`, `contextOptimization`, `chatMode`, `designScheme`, `maxLLMSteps` from request body
2. Reads API keys and provider settings from cookies
3. If `contextOptimization` is on:
   - Creates a summary of the conversation (`createSummary()`)
   - Selects relevant context files (`selectContext()`)
   - Slices old messages, keeping only recent ones + summary
4. Calls `streamText()` with the Vercel AI SDK
5. Wraps `<think>` blocks from reasoning models in `__boltThought__` divs (lines 391-412)
6. Handles `finishReason === 'length'` by appending a `CONTINUE_PROMPT` and re-streaming (up to `MAX_RESPONSE_SEGMENTS` times)
7. Returns a streaming `Response` with `text/event-stream`

**File**: `app/lib/.server/llm/stream-text.ts` (lines 54-311)

The `streamText()` function:
1. Extracts model/provider from the last user message (embedded as `[Model: ...]` `[Provider: ...]` tags)
2. Sanitizes messages (strips `__boltThought__`, `<think>` tags, `package-lock.json` content)
3. Selects the prompt from `PromptLibrary`
4. Appends context files and chat summary to the system prompt
5. Appends locked file paths to the system prompt (telling the LLM not to modify them)
6. Detects reasoning models (o1, GPT-5) and adjusts parameters (uses `maxCompletionTokens` instead of `maxTokens`, forces `temperature: 1`)
7. Calls Vercel AI SDK's `_streamText()` with the configured model

### MCP (Model Context Protocol) Integration

**File**: `app/lib/services/mcpService.ts` (not read in full, but referenced)
The chat endpoint integrates MCP tool calls:
- `mcpService.processToolInvocations(messages, dataStream)` — processes any pending tool invocations
- `toolChoice: 'auto'` + `tools: mcpService.toolsWithoutExecute` — passes MCP tools to the LLM
- `onStepFinish` callback processes tool call results

### Client-Side Chat

**File**: `app/components/chat/Chat.client.tsx` (lines 34-100)
Uses `useChat()` from `@ai-sdk/react` to manage the chat state. The `processSampledMessages` sampler (50ms) calls `parseMessages()` to feed streaming LLM output through the message parser, which triggers workbench actions.

---

## 7. What Makes It Good

### Live Preview
The WebContainer + iframe preview is genuinely impressive. You type a prompt, the LLM streams code, files get written to the virtual filesystem, the dev server hot-reloads, and you see the result live in the iframe. The feedback loop is nearly instant.

### Visual Feedback
- Actions show status (pending/running/complete/failed) in the chat
- File writes stream live in the editor (via `onActionStream`)
- The workbench auto-opens when artifacts are detected
- Progress annotations show "Analysing Request" → "Code Files Selected" → "Generating Response"
- Error alerts with "Fix" buttons that send error context back to the LLM

### One-Shot Generation Flow
The `<boltArtifact>` format is well-designed: a single LLM response can create `package.json`, install deps, write multiple files, and start the dev server — all in order. The sequential execution queue ensures correctness.

### Provider Flexibility
22 LLM providers out of the box. The `BaseProvider` abstraction is clean enough that adding a new OpenAI-compatible provider is ~50 lines.

### Context Optimization
The `contextOptimization` pipeline (summarize → select relevant files → slim messages) is a practical solution to context window limits. It runs 2 extra LLM calls but keeps the main generation focused.

### File Locking
The per-chat, per-file/folder locking system prevents the LLM from overwriting files the user has manually edited. Practical UX touch.

---

## 8. What's Broken

### One-Shot Generation (No Error Loop)
**The biggest problem.** When a shell command fails (npm install error, build error, runtime error), Bolt shows an alert with a "Fix" button. But there's NO automatic retry loop. The user has to click "Fix", which sends the error back to the LLM as a new message. This means:
- Build failures require manual intervention
- The LLM often doesn't get enough context about what went wrong
- Complex projects that need iterative fixes (install → fix → install → fix) are painful

**Where to look**: `app/lib/runtime/action-runner.ts` lines 226-247 (error handling), `app/components/chat/ChatAlert.tsx` (the "Fix" button).

### WebContainer Limitations
- No native binaries = no Python packages, no Rust, no C++, no Docker
- No git = can't clone repos inside the container (only import via UI)
- Full file rewrites only (no diffs/patches) = massive token waste
- Limited shell = many common commands missing or behaving differently
- File system is ephemeral = everything lost on page refresh (mitigated by chat history replay)

### Local Model Compatibility
The `<boltArtifact>` XML tag format is the Achilles heel for local models:
- Small models often fail to produce well-formed XML tags
- Models may escape `<` and `>` as `&lt;` and `&gt;` (handled by `cleanEscapedTags()`)
- Models may wrap file content in markdown code blocks (handled by `cleanoutMarkdownSyntax()`)
- The `EnhancedStreamingMessageParser` tries to compensate by detecting code blocks without tags, but it's pattern-matching heuristics — unreliable
- **No structured output / tool calling mode** — everything relies on free-form XML in the text stream

### npm Prompt Interruptions
WebContainer's npm sometimes prompts for user input (e.g., "Need to install the following packages: ... Ok to proceed? (y)"). This blocks the shell and causes timeouts. The system prompt says "use `--yes` flag" but models don't always comply.

### Token Waste
Because the prompt demands FULL file content (no diffs), every edit rewrites the entire file. A one-line CSS change means the LLM outputs the entire CSS file. The `contextOptimization` pipeline helps with input tokens but not output tokens.

### Race Conditions
- The `#globalExecutionQueue` is a Promise chain, but `actionStreamSampler` introduces 100ms sampling that can cause ordering issues
- `start` actions have a hardcoded 2s delay to "avoid race conditions" (action-runner.ts line 217) — a code smell
- Preview refresh has a 300ms debounce that can miss rapid updates

### State Management Complexity
The store architecture is fragmented:
- `workbenchStore` (nanostores) — files, artifacts, editor state
- `chatStore` (nanostores) — chat visibility
- `useChatHistory` (custom hook with IDB) — persistence
- `supabaseConnection` (nanostores) — Supabase state
- Various `useState` in components — local state

No single source of truth for "what has the LLM done so far."

### Prompt Bloat
The system prompt is ~700 lines for the "original" version. It includes detailed Supabase instructions, mobile app instructions, design instructions, and multiple examples. Most of this is irrelevant for a given task. The `optimized` prompt variant exists but is marked "experimental."

---

## 9. Key File Reference

### Core Pipeline
| File | Purpose |
|---|---|
| `app/routes/api.chat.ts` | LLM streaming endpoint, context optimization, continuation logic |
| `app/lib/.server/llm/stream-text.ts` | Model selection, prompt assembly, Vercel AI SDK call |
| `app/lib/common/prompts/prompts.ts` | Main system prompt (~700 lines) |
| `app/lib/common/prompt-library.ts` | Prompt variant selector |
| `app/lib/runtime/message-parser.ts` | Streaming XML tag parser (core state machine) |
| `app/lib/runtime/enhanced-message-parser.ts` | Fallback parser for models without proper XML output |
| `app/lib/runtime/action-runner.ts` | File/shell/start action execution |
| `app/lib/hooks/useMessageParser.ts` | Wires parser callbacks to workbench store |

### Stores
| File | Purpose |
|---|---|
| `app/lib/stores/workbench.ts` | Main orchestrator: artifacts, files, editor, previews, terminal |
| `app/lib/stores/files.ts` | WebContainer filesystem mirror, locking, modifications |
| `app/lib/stores/previews.ts` | Dev server port/URL tracking, cross-tab sync |
| `app/lib/stores/editor.ts` | Editor document state |
| `app/lib/stores/terminal.ts` | Terminal instance management |

### UI Components
| File | Purpose |
|---|---|
| `app/routes/_index.tsx` | Entry point |
| `app/components/chat/Chat.client.tsx` | Chat state management, useChat() hook |
| `app/components/chat/BaseChat.tsx` | Layout: chat + workbench side-by-side |
| `app/components/workbench/Workbench.client.tsx` | Code/Diff/Preview tabbed view |
| `app/components/workbench/EditorPanel.tsx` | File tree + editor + terminal panels |
| `app/components/workbench/Preview.tsx` | iframe preview with device mode |

### LLM Providers
| File | Purpose |
|---|---|
| `app/lib/modules/llm/base-provider.ts` | Abstract provider base class |
| `app/lib/modules/llm/manager.ts` | Provider registry singleton |
| `app/lib/modules/llm/providers/*.ts` | 22 provider implementations |

### WebContainer
| File | Purpose |
|---|---|
| `app/lib/webcontainer/index.ts` | Boot, inspector script, error forwarding |
| `app/utils/shell.ts` | BoltShell wrapper for command execution |

---

## 10. Architecture Diagram

```
User Input
    │
    ▼
Chat.client.tsx (useChat from @ai-sdk/react)
    │
    ▼ POST /api/chat
api.chat.ts
    │
    ├─► createSummary() ─► selectContext()  (if contextOptimization)
    │
    ▼
stream-text.ts
    │
    ├─► PromptLibrary.getPropmtFromLibrary()  → system prompt
    ├─► provider.getModelInstance()             → Vercel AI SDK model
    │
    ▼
Vercel AI SDK streamText()
    │
    ▼ SSE stream
Chat.client.tsx (onStream)
    │
    ▼
useMessageParser → EnhancedStreamingMessageParser
    │
    ├─► parse() → detects <boltArtifact> / <boltAction> tags
    │
    ▼ callbacks
WorkbenchStore
    │
    ├─► addArtifact() → creates ActionRunner
    ├─► addAction() → queues action
    ├─► runAction() → sequential execution
    │
    ▼
ActionRunner
    │
    ├─► file:  WebContainer.fs.writeFile()
    ├─► shell: BoltShell.executeCommand()
    ├─► start: BoltShell.executeCommand() (non-blocking)
    │
    ▼
WebContainer
    │
    ├─► filesystem changes → FilesStore watcher → Editor updates
    ├─► server-ready event → PreviewsStore → Preview iframe
    └─► preview-message → error alerts
```

---

## 11. Recommendations for BoltHands

### Keep
- **Message parser state machine** (`message-parser.ts`) — well-tested, handles streaming correctly
- **Provider abstraction** (`base-provider.ts` + `manager.ts`) — clean, extensible
- **WorkbenchStore orchestration pattern** — sequential queue is the right approach
- **Preview infrastructure** — WebContainer iframe rendering is solid
- **File locking system** — practical UX feature

### Rewrite
- **Error handling** — Add automatic retry loops. When a shell command fails, the system should automatically send the error back to the LLM and retry (with a max retry count).
- **System prompt** — Modularize it. Break the monolithic 700-line prompt into composable sections that activate based on the task (don't send Supabase instructions for a static site).
- **Context management** — The summary+select pipeline is good but should be the default, not opt-in. Also needs a proper sliding window instead of hardcoded `messageSliceId`.
- **EnhancedStreamingMessageParser** — Consider using tool calling / structured output instead of hoping models produce correct XML. For local models, a two-pass approach (generate then extract) might be more reliable.

### Throw Away
- **Supabase integration** — Unless BoltHands needs it. It's deeply embedded in the prompt, the action types, the alert system. Adds significant complexity for a niche feature.
- **Mobile app (Expo) instructions** — 150+ lines of prompt for a narrow use case.
- **GitHub/GitLab push from workbench** (`workbenchStore.pushToRepository`) — 200+ lines of Octokit code. Use a simpler approach or separate service.
- **Device frame rendering in Preview** — 500+ lines of inline CSS/HTML for phone bezels. Nice but not core.
- **Cloudflare Workers deployment target** — If running locally, the wrangler/CF machinery is dead weight.
- **Electron packaging** — Unless you need a desktop app.

---

## 12. Dependencies Worth Noting

| Package | Version | Purpose | Keep? |
|---|---|---|---|
| `@webcontainer/api` | 1.6.1-internal.1 | Browser Node.js sandbox | Core |
| `ai` (Vercel AI SDK) | 4.3.16 | LLM streaming, tool calling | Core |
| `@ai-sdk/react` | ^1.2.12 | React hooks for chat | Core |
| `nanostores` | ^0.10.3 | Global state management | Core |
| `@remix-run/*` | ^2.15.2 | Framework | Could swap |
| `@codemirror/*` | various | Code editor | Core |
| `@xterm/xterm` | ^5.5.0 | Terminal | Core |
| `react-resizable-panels` | ^2.1.7 | Split pane layout | Core |
| `isomorphic-git` | ^1.27.2 | Git operations (for import) | Optional |
| `jszip` | ^3.10.1 | Project export as zip | Optional |
| `@octokit/rest` | ^21.0.2 | GitHub API (push to repo) | Remove |
| `framer-motion` | ^11.12.0 | Animations | Could simplify |
| `shiki` | ^1.24.0 | Syntax highlighting in chat | Nice to have |
| `chart.js` | ^4.4.7 | Charts (settings?) | Remove |
