# BoltHands Context Management — Design Spec

**Date:** 2026-03-20
**Goal:** Prevent context overflow and enable multi-session continuity. The agent saves progress to disk, compacts history when context fills up, and can resume from where it left off.

---

## Overview

Context management solves the #1 problem with autonomous agents: losing everything when the context window fills up. BoltHands uses three strategies:

1. **Proactive file saves** — Agent writes findings to disk immediately, not just to context
2. **Three-tier compaction** — Observation masking → LLM summarization → file offload
3. **Session continuity** — State files enable resume after crash/overflow/restart

## Architecture

Context management is a middleware layer between the agent controller and the LLM client. It intercepts the message history before each LLM call, measures token usage, and applies compaction when thresholds are hit.

```
src/bolthands/
  context/
    __init__.py
    monitor.py         # Token counting + threshold detection
    compactor.py       # Three-tier compaction pipeline
    workspace.py       # File-based workspace memory (/workspace/context/)
    session.py         # Session lifecycle (start/resume/handoff)
```

## Components

### 1. Context Monitor (monitor.py)

Tracks token usage and triggers compaction:

- count_tokens(messages) -> int: Approximate token count (chars/4 heuristic, or tiktoken if available)
- check_budget(messages, max_context) -> CompactionLevel: Returns GREEN/YELLOW/ORANGE/RED based on utilization

Thresholds (percentage of max context window):
- GREEN (< 60%): No action
- YELLOW (60-75%): Mask old observations (Tier 1)
- ORANGE (75-85%): Summarize + mask (Tier 2)
- RED (> 85%): Emergency save + summarize + mask (Tier 3)

### 2. Compactor (compactor.py)

Three-tier compaction pipeline:

**Tier 1 — Observation masking (no LLM call):**
Replace old tool outputs (beyond the last N turns) with a one-line summary:
"[Output masked, was {length} chars] {first_line}..."

**Tier 2 — LLM summarization (uses the agent's own LLM):**
Summarize the oldest conversation chunk into a compact status block:
- What was the original goal
- What has been accomplished
- What files were modified
- What's the current approach
- What needs to happen next

**Tier 3 — File offload (before summarizing):**
Before summarizing, extract valuable info from history and save to workspace files:
- Code snippets to relevant source files
- Decisions to /workspace/context/decisions.md
- Findings to /workspace/context/research.md
Then apply Tier 2 summarization.

### 3. Workspace Memory (workspace.py)

File-based memory inside the Docker container at /workspace/context/:

```
/workspace/context/
  state.json          # Current agent state (step, phase, key vars)
  progress.md         # What's done, what's next
  decisions.md        # Design decisions with rationale
  file-index.md       # Map of what files exist and what they contain
```

Methods:
- save_state(state_dict) — Write state.json
- load_state() -> dict — Read state.json
- append_progress(step, status, details) — Append to progress.md
- save_research(topic, content) — Write to context/{topic}.md
- get_file_index() -> str — Read file-index.md

### 4. Session Manager (session.py)

Handles session lifecycle:

**Start of session:**
1. Check if /workspace/context/state.json exists
2. If yes: resume mode — read state, read progress, inject into system prompt
3. If no: fresh start — create workspace structure

**End of session (triggered by RED threshold or explicit finish):**
1. Write handoff document to /workspace/context/handoff.md
2. Update state.json with current step and status
3. Update progress.md
4. Signal to controller: "session ending, state saved"

**Resume bootstrap:** The system prompt includes:
"You are resuming work. Read /workspace/context/state.json for where you left off.
Read /workspace/context/progress.md for history. Continue from the current step."

## Integration with Agent Controller

The compactor hooks into the controller's main loop:

```python
# In controller.py run() loop, before each LLM call:
level = self.monitor.check_budget(self.history, self.config.max_context)
if level != CompactionLevel.GREEN:
    self.history = await self.compactor.compact(self.history, level)
```

The workspace memory hooks into tool execution — after every file write or significant finding, the agent updates the file index.

## Token Counting

For llama.cpp, approximate with chars/4 (within ~10% for English). If tiktoken is available, use cl100k_base for better accuracy. The monitor accepts a pluggable counter.

## Testing

- test_monitor.py: Token counting, threshold detection at each level
- test_compactor.py: Tier 1 masking (verify old observations replaced), Tier 2 summarization (mock LLM), Tier 3 file offload (mock executor)
- test_session.py: Fresh start vs resume, handoff generation
- test_workspace.py: File read/write operations

## Out of Scope

- Vector search / RAG (future enhancement)
- Multi-agent memory sharing
- Automatic knowledge base updates
