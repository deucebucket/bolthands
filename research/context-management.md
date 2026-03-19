# BoltHands: Context Management for Autonomous Coding Agents

## Technical Design Document

**Date:** 2026-03-18
**Target Runtime:** llama.cpp (local, no cloud APIs)
**Models:** 4B/9B for orchestration, 27B-32B for heavy coding
**Context Window:** 131,072 tokens (typical for Qwen3.5-27B and similar)

---

## Table of Contents

1. [Incremental File-Based Memory](#1-incremental-file-based-memory)
2. [Context Compaction](#2-context-compaction)
3. [Multi-Session Continuity](#3-multi-session-continuity)
4. [Model Cascading](#4-model-cascading)
5. [Working Memory vs Long-Term Memory](#5-working-memory-vs-long-term-memory)
6. [Token Budgeting](#6-token-budgeting)
7. [Self-Aware Context Management](#7-self-aware-context-management)
8. [Implementation Roadmap](#8-implementation-roadmap)

---

## 1. Incremental File-Based Memory

### The Problem

An agent that keeps research only in conversation context will lose everything when the context overflows. The solution is to treat files as the primary memory store and conversation as a temporary workspace.

### Core Principle

**Never hold knowledge only in conversation.** Every finding, decision, or plan must be written to disk within the same turn it was discovered. The conversation is ephemeral; files are permanent.

### Workspace Directory Structure

```
/workspace/
  research/           # Raw findings, organized by topic
    topic-{name}.md   # One file per research topic
    sources.md        # URLs, references, citations
  plans/              # Actionable plans
    PLAN.md           # Master plan with numbered steps
    architecture.md   # System design decisions
    api-design.md     # API/interface specifications
  progress/           # Execution tracking
    PROGRESS.md       # Current step, status, blockers
    changelog.md      # What was done and when
    decisions.md      # Design decisions with rationale
  context/            # Agent working memory (machine-readable)
    state.json        # Current agent state (step, phase, key variables)
    scratchpad.md     # In-progress thinking (triaged at session end)
    file-index.md     # Map of what's in each workspace file
```

### File Writing Rules

1. **Write-on-discover:** When the agent finds something important, it appends to the relevant research file immediately, before continuing its chain of thought.

2. **Structured format:** Every research file uses a consistent template:
   ```markdown
   # Topic: {name}
   ## Last Updated: {timestamp}

   ## Key Findings
   - Finding 1
   - Finding 2

   ## Details
   {detailed notes}

   ## Open Questions
   - Question 1
   ```

3. **Append-only during a session:** Files are appended to, never overwritten, during a single session. Consolidation happens at session boundaries.

4. **File index maintenance:** After writing to any file, the agent updates `context/file-index.md` with a one-line summary of what that file contains. This is the agent's "table of contents" for its own memory.

### Implementation for llama.cpp

The agent framework wraps file operations as tool calls:

```python
def save_research(topic: str, content: str) -> str:
    """Append research findings to a topic file."""
    path = f"/workspace/research/{slugify(topic)}.md"
    timestamp = datetime.now().isoformat()
    with open(path, "a") as f:
        f.write(f"\n## Entry [{timestamp}]\n{content}\n")
    update_file_index(path, topic)
    return f"Saved to {path}"

def save_progress(step: int, status: str, details: str) -> str:
    """Update progress tracking."""
    state = load_state()
    state["current_step"] = step
    state["status"] = status
    state["last_update"] = datetime.now().isoformat()
    save_state(state)
    with open("/workspace/progress/PROGRESS.md", "a") as f:
        f.write(f"\n### Step {step}: {status}\n{details}\n")
    return f"Progress updated: step {step} = {status}"
```

### Reference Pattern

When the agent needs old research, it reads the file rather than relying on conversation history:

```
System: You have research files in /workspace/research/. Before starting work,
read the file-index.md to see what's available. Reference files instead of
relying on memory.
```

---

## 2. Context Compaction

### How OpenHands Does It

OpenHands implements a `LLMSummarizingCondenser` with these mechanics:

- **Trigger:** Fires when event history exceeds `max_size` (configurable, e.g., 10 events)
- **Preservation:** Always keeps the first `keep_first` events (system prompt, initial user message)
- **Summarization:** An LLM generates a summary of the dropped events, focusing on:
  - The user's original goals
  - Progress made so far
  - What still needs to be done
  - Critical technical details (file paths, failing tests, key code)
- **Replacement:** Old events are replaced with a single `CondensationEvent` containing the summary
- **Result:** Linear cost scaling instead of quadratic; up to 2x reduction in per-turn API costs

### How MemGPT/Letta Does It

MemGPT uses a virtual memory paging system inspired by OS memory management:

- **Main context** (like RAM): System prompt + working context + FIFO message queue
- **External storage** (like disk): Archival memory (vector DB) + recall memory (full history)
- **Eviction:** When main context fills up, oldest messages are evicted (LRU-style) to external storage
- **Retrieval:** The agent has explicit tools to search and retrieve from external storage
- **Self-editing:** The agent can modify its own working context -- consolidating, updating, or reprioritizing information
- **Key insight:** The agent actively manages its own memory rather than relying on automatic systems

### JetBrains Research Findings

JetBrains tested two strategies on coding agents and found:

1. **Observation masking** (replacing old tool outputs with placeholders): Best overall -- 2.6% higher solve rate while being 52% cheaper than baseline
2. **LLM summarization** (condensing conversation history): Works but has overhead -- summary generation consumed 7% of costs, and agents ran 15% longer due to "trajectory elongation"
3. **Recommendation:** Use observation masking as the first line of defense, with targeted summarization for specific bottlenecks

### Recommended Implementation for BoltHands

A three-tier compaction strategy:

#### Tier 1: Observation Masking (Cheap, No LLM Call)
Replace old tool outputs with compact summaries. Keep the action (what was done) but replace the full output with a one-line result.

```python
def mask_old_observations(messages, keep_recent=10):
    """Replace old tool outputs with placeholders."""
    for i, msg in enumerate(messages[:-keep_recent]):
        if msg["role"] == "tool":
            original_len = len(msg["content"])
            # Keep first line + token count as placeholder
            first_line = msg["content"].split("\n")[0][:100]
            msg["content"] = f"[Output masked, was {original_len} chars] {first_line}..."
    return messages
```

#### Tier 2: Rolling Summary (Uses Small Model)
When history exceeds a threshold, use the orchestrator model (9B) to summarize older conversation into a condensed block.

```python
SUMMARIZE_PROMPT = """Summarize this conversation history into a compact status update.
Preserve:
- The user's original goal
- All file paths mentioned
- Key decisions made and their rationale
- Current progress (what's done, what's next)
- Any errors or blockers encountered
- Code patterns or APIs that were established

Drop:
- Verbose tool outputs (file contents, search results)
- Exploratory dead ends that didn't lead anywhere
- Redundant exchanges

Format as a structured summary under 500 tokens."""
```

#### Tier 3: File Offload (Before Compaction)
Before summarizing, save any valuable information from the conversation to workspace files. This ensures nothing important is lost even if the summary misses something.

```python
def pre_compaction_save(messages_to_compact):
    """Extract and save valuable info before compaction."""
    # Extract code snippets to relevant files
    # Extract decisions to decisions.md
    # Extract findings to research files
    # Then compact the conversation
```

### Compaction Pipeline

```
Messages arrive
    |
    v
[Token counter] -- "How full is the context?"
    |
    |-- <60% full: Do nothing
    |-- 60-80% full: Tier 1 (mask old observations)
    |-- 80-90% full: Tier 2 (summarize + mask)
    |-- >90% full: Tier 3 (file offload + summarize + mask)
    |
    v
Compacted message history
```

---

## 3. Multi-Session Continuity

### The Problem

When the agent's session ends (context overflow, crash, user closes it), all progress is lost unless explicitly persisted. The next session starts from scratch.

### Session Lifecycle

```
Session Start (SOD - Start of Day)
    |
    v
[Read state.json] -- "Am I resuming or starting fresh?"
    |
    |-- Fresh: Read PLAN.md, start from step 1
    |-- Resuming: Read PROGRESS.md, continue from last step
    |
    v
[Active Work] -- Save progress incrementally
    |
    v
Session End (EOD - End of Day)
    |
    v
[Write handoff] -- PROGRESS.md + state.json + scratchpad triage
```

### State File (state.json)

```json
{
  "session_id": "sess_20260318_001",
  "project": "bolthands",
  "phase": "implementation",
  "current_step": 4,
  "current_task": "Implement token counter module",
  "status": "in_progress",
  "started_at": "2026-03-18T10:00:00",
  "last_update": "2026-03-18T14:30:00",
  "key_files": [
    "src/context/counter.py",
    "src/context/compactor.py"
  ],
  "blockers": [],
  "context_tokens_used": 45000,
  "compaction_count": 2
}
```

### PROGRESS.md Format

```markdown
# Progress Log

## Current Status
- Phase: Implementation
- Step: 4 of 12
- Task: Implement token counter module
- Status: In Progress

## Completed Steps
### Step 1: Project Setup (2026-03-18)
- Created directory structure
- Initialized Python project with pyproject.toml
- Result: /workspace/src/ created

### Step 2: Core Architecture (2026-03-18)
- Designed message pipeline
- Defined interfaces for Compactor, Router, MemoryStore
- Result: See /workspace/plans/architecture.md

### Step 3: Token Counter Prototype (2026-03-18)
- Implemented tiktoken-based counter
- Tested against llama.cpp tokenizer
- Result: src/context/counter.py (working, needs optimization)

## Next Steps
- Step 4: Implement compaction pipeline
- Step 5: Implement model router
- Step 6: Integration tests
```

### Resume Bootstrap Prompt

When a new session starts, the system prompt includes:

```
You are resuming work on the BoltHands project.

1. Read /workspace/context/state.json to see where you left off
2. Read /workspace/progress/PROGRESS.md for detailed history
3. Read /workspace/plans/PLAN.md if you need the full plan
4. Read /workspace/context/file-index.md to see what files exist
5. Continue from the current step

Do NOT re-research topics that already have files in /workspace/research/.
Do NOT re-plan steps that are already in PLAN.md.
Start working from where you left off.
```

### Handoff Document (End of Session)

Before a session ends (ideally triggered by the self-aware context monitor), the agent writes a handoff:

```markdown
# Session Handoff: sess_20260318_001

## Accomplished
- Completed steps 1-3 of the plan
- Token counter module working (src/context/counter.py)
- Architecture design finalized

## In Progress
- Step 4: Compaction pipeline -- started, 60% done
- File: src/context/compactor.py (has Tier 1, needs Tier 2/3)

## Blocked
- None

## Next Session Should
1. Finish compactor.py (add Tier 2 and Tier 3)
2. Write tests for compaction pipeline
3. Start on model router (Step 5)

## Key Context
- Using tiktoken cl100k_base for approximate token counts
- Compaction thresholds: 60/80/90 percent
- Small model for summarization: Qwen3.5-9B
```

---

## 4. Model Cascading

### Architecture

Two models running on llama.cpp, potentially on different ports or swapped via the model swap script:

| Role | Model | Size | Speed | Context |
|------|-------|------|-------|---------|
| Orchestrator | Qwen3.5-9B or Qwen3.5-4B | 7GB / 3GB | 60-100 t/s | 32K |
| Coder | Qwen3.5-27B or GLM-4.7 | 20GB / 17GB | 15-40 t/s | 131K |

### Routing Strategy

The orchestrator handles:
- **Planning:** Breaking tasks into steps, deciding what to do next
- **File navigation:** Deciding which files to read, search queries to run
- **Progress tracking:** Updating state files, writing summaries
- **Context compaction:** Generating conversation summaries (Tier 2)
- **Decision routing:** Determining if a task needs the big model
- **Tool orchestration:** Deciding tool call sequences

The coder handles:
- **Code generation:** Writing new functions, classes, modules
- **Code modification:** Complex refactors, bug fixes
- **Code review:** Analyzing code for issues
- **Architecture decisions:** Evaluating technical trade-offs
- **Complex reasoning:** Anything requiring deep understanding of code semantics

### Router Implementation

```python
class ModelRouter:
    ORCHESTRATOR_URL = "http://localhost:8080"  # 9B model
    CODER_URL = "http://localhost:8081"         # 27B model

    # Tasks that always go to the big model
    CODER_TASKS = {
        "write_code", "modify_code", "review_code",
        "debug", "refactor", "architect"
    }

    # Tasks that the small model handles
    ORCHESTRATOR_TASKS = {
        "plan", "navigate", "summarize", "track_progress",
        "decide_next_step", "search_files", "read_file"
    }

    def route(self, task_type: str, complexity: str = "normal") -> str:
        """Return the appropriate model endpoint."""
        if task_type in self.CODER_TASKS:
            return self.CODER_URL
        if task_type in self.ORCHESTRATOR_TASKS:
            return self.ORCHESTRATOR_URL
        # Unknown task: use coder if complex, orchestrator otherwise
        if complexity == "high":
            return self.CODER_URL
        return self.ORCHESTRATOR_URL
```

### Single-GPU Strategy

With a single RTX 3090 (24GB), you cannot run both models simultaneously at full size. Options:

1. **Hot-swap:** Load the orchestrator (3-7GB VRAM) by default. When coding is needed, unload it and load the coder (17-20GB). Use the existing `swap-model.sh` script.
   - Latency: 5-15 seconds per swap (model load time)
   - Best for: Long coding tasks where swaps are infrequent

2. **Shared context server:** Run the coder model but use a shorter context/simpler prompt for orchestration tasks. Send the full context only for coding tasks.
   - Latency: No swap overhead
   - Trade-off: Using an expensive model for simple tasks

3. **Quantization split:** Run a heavily quantized version of the big model (Q2_K, ~10GB) alongside the small model (Q4_K_M, ~3GB) using split layers.
   - Feasible but quality degrades significantly at Q2

**Recommended approach for single GPU:** Option 2 (single coder model, simpler prompts for orchestration). The 27B model is fast enough for planning tasks, and swap overhead adds up. Reserve model swapping for when you want the 4B model's speed for rapid-fire orchestration phases.

### Dual-Model Workflow

When both models are available (or using a single model with role-based prompting):

```
User Request
    |
    v
[Orchestrator] -- "Break this into steps"
    |
    v
Step 1: Read relevant files (orchestrator handles)
Step 2: Plan code changes (orchestrator handles)
Step 3: Write the code (ROUTE TO CODER)
Step 4: Verify the code (orchestrator runs tests)
Step 5: Update progress (orchestrator handles)
```

---

## 5. Working Memory vs Long-Term Memory

### Memory Architecture

```
+--------------------------------------------------+
|              CONTEXT WINDOW (Working Memory)       |
|                                                    |
|  System Prompt          [fixed, ~2K tokens]        |
|  Working Context Block  [agent-editable, ~2K]      |
|  Recent Messages        [FIFO, ~90K tokens]        |
|  Current Task           [variable, ~20K tokens]    |
|  Reserved for Response  [~16K tokens]              |
|                                                    |
+--------------------------------------------------+
         ^                    |
         |   retrieve         |   save/evict
         |                    v
+--------------------------------------------------+
|           LONG-TERM MEMORY (Files + DB)            |
|                                                    |
|  Workspace Files     /workspace/**/*.md            |
|  Code Files          /workspace/src/**             |
|  State Files         /workspace/context/           |
|  Vector Store        (optional, for large projects)|
|                                                    |
+--------------------------------------------------+
```

### Working Context Block

Inspired by MemGPT's core memory, the agent maintains a structured block at the top of every conversation that it can edit itself:

```markdown
## Working Context (agent-editable)
- Project: BoltHands context management system
- Phase: Implementation (step 4 of 12)
- Current task: Building compaction pipeline
- Key files: src/context/compactor.py, src/context/counter.py
- Recent decision: Using observation masking as Tier 1
- Blocker: None
- Token budget remaining: ~85K tokens
```

This block is always in context (pinned) and the agent updates it via a tool call. It acts as a "scratchpad" that survives compaction because it is part of the system prompt region, not the message history.

### Information Flow Between Tiers

```
Discovery in conversation
    |
    v
[Is this worth keeping?]
    |
    |-- Yes, critical: Write to workspace file + update working context
    |-- Yes, reference: Write to workspace file only
    |-- No: Leave in conversation (will be compacted away)
    |
When retrieving:
    |
    v
[Do I need this information?]
    |
    |-- In working context: Already available (0 cost)
    |-- In workspace file: Read file (tool call, moderate cost)
    |-- In vector store: Semantic search (tool call, higher cost)
    |-- In compacted history: Re-read summary or search files
```

### Vector Store (Optional, For Large Projects)

For projects with many research files, a simple vector store enables semantic search:

```python
# Using sentence-transformers + FAISS (runs on CPU, no VRAM needed)
from sentence_transformers import SentenceTransformer
import faiss

class SimpleVectorStore:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.index = faiss.IndexFlatIP(384)
        self.documents = []

    def add(self, text: str, metadata: dict):
        embedding = self.model.encode([text])
        self.index.add(embedding)
        self.documents.append({"text": text, "metadata": metadata})

    def search(self, query: str, k: int = 5) -> list:
        embedding = self.model.encode([query])
        scores, indices = self.index.search(embedding, k)
        return [self.documents[i] for i in indices[0] if i < len(self.documents)]
```

For most coding agent tasks, file-based memory (grep/read) is sufficient. Vector stores add value when the workspace grows beyond ~50 files or when the agent needs to find conceptually related information across many documents.

---

## 6. Token Budgeting

### Budget Allocation for 131K Context

| Component | Tokens | % | Notes |
|-----------|--------|---|-------|
| System prompt | 3,000 | 2.3% | Instructions, persona, tool descriptions |
| Working context block | 2,000 | 1.5% | Agent-editable state summary |
| Retrieved context (RAG/files) | 20,000 | 15.3% | File contents pulled in for current task |
| Compacted history summary | 5,000 | 3.8% | Summary of older conversation |
| Recent conversation | 80,000 | 61.1% | Last N turns, verbatim |
| Current task output | 5,000 | 3.8% | Space for current tool output |
| Response generation | 16,000 | 12.2% | Model's output buffer |
| **Total** | **131,000** | **100%** | |

### Dynamic Budget Adjustment

The budget is not static. As the conversation grows, allocations shift:

```python
class TokenBudget:
    def __init__(self, total_ctx=131072):
        self.total = total_ctx
        self.fixed = {
            "system_prompt": 3000,
            "working_context": 2000,
            "response_reserve": 16000,
        }
        self.fixed_total = sum(self.fixed.values())  # 21,000
        self.available = self.total - self.fixed_total  # 110,000

    def allocate(self, n_history_tokens: int, n_rag_tokens: int) -> dict:
        """Dynamically allocate remaining budget."""
        used = n_history_tokens + n_rag_tokens
        remaining = self.available - used

        if remaining > 30000:
            # Plenty of room, no action needed
            return {"status": "ok", "remaining": remaining}
        elif remaining > 10000:
            # Getting tight, start masking old observations
            return {"status": "compact_tier1", "remaining": remaining}
        elif remaining > 0:
            # Critical, summarize history
            return {"status": "compact_tier2", "remaining": remaining}
        else:
            # Over budget, emergency compaction
            return {"status": "compact_tier3", "over_by": abs(remaining)}
```

### Token Counting with llama.cpp

llama.cpp server provides token counting via the `/v1/messages/count_tokens` endpoint. For pre-flight estimation without a server call, use a local tokenizer:

```python
# Option 1: Use llama.cpp's tokenize endpoint
import requests

def count_tokens_server(text: str, server_url: str = "http://localhost:8080") -> int:
    """Count tokens using the running llama.cpp server."""
    response = requests.post(
        f"{server_url}/tokenize",
        json={"content": text}
    )
    return len(response.json()["tokens"])

# Option 2: Use tiktoken as a fast approximation (no server needed)
import tiktoken

def count_tokens_approx(text: str) -> int:
    """Approximate token count using tiktoken cl100k_base.
    Within ~10% of most model tokenizers for English text."""
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

# Option 3: Use the model's own tokenizer via llama-cpp-python
from llama_cpp import Llama

def count_tokens_exact(text: str, model_path: str) -> int:
    """Exact count using the model's tokenizer (expensive to init)."""
    llm = Llama(model_path=model_path, n_ctx=0, n_gpu_layers=0)
    return len(llm.tokenize(text.encode()))
```

### Budget Monitoring Response Fields

llama.cpp's completion response includes:

- `tokens_evaluated`: Total prompt tokens processed
- `tokens_cached`: Tokens reused from KV cache
- `truncated`: Boolean, true if context was exceeded

Use `tokens_evaluated` from each response to track cumulative context usage.

---

## 7. Self-Aware Context Management

### The Concept

The agent monitors its own context consumption and proactively takes action before overflow. This is the key innovation that prevents catastrophic context loss.

### Implementation: Context Monitor

```python
class ContextMonitor:
    """Injected into every agent turn. Tracks and manages context budget."""

    def __init__(self, total_ctx: int = 131072, thresholds: dict = None):
        self.total_ctx = total_ctx
        self.thresholds = thresholds or {
            "green": 0.60,   # < 60% -- no action
            "yellow": 0.75,  # 75% -- start masking
            "orange": 0.85,  # 85% -- summarize
            "red": 0.92,     # 92% -- emergency save + compact
        }
        self.tokens_used = 0
        self.compaction_count = 0

    def update(self, tokens_evaluated: int):
        """Called after every LLM response with usage data."""
        self.tokens_used = tokens_evaluated

    @property
    def utilization(self) -> float:
        return self.tokens_used / self.total_ctx

    @property
    def status(self) -> str:
        u = self.utilization
        if u < self.thresholds["green"]:
            return "green"
        elif u < self.thresholds["yellow"]:
            return "yellow"
        elif u < self.thresholds["orange"]:
            return "orange"
        else:
            return "red"

    def get_action(self) -> dict:
        """Determine what action to take based on context pressure."""
        status = self.status
        if status == "green":
            return {"action": "none"}
        elif status == "yellow":
            return {
                "action": "mask_observations",
                "keep_recent": 10,
                "message": "Context at 75%. Masking old tool outputs."
            }
        elif status == "orange":
            return {
                "action": "summarize_and_mask",
                "keep_recent": 5,
                "summarize_oldest": 20,
                "message": "Context at 85%. Summarizing old history."
            }
        else:  # red
            return {
                "action": "emergency_save",
                "message": "Context at 92%. Saving all state to files and preparing handoff."
            }
```

### Injecting Awareness into the System Prompt

The agent is told about its own context status in every turn:

```
[CONTEXT STATUS: {status} | {utilization:.0%} used | {tokens_remaining} tokens remaining]

When context reaches YELLOW: Stop exploring new topics. Focus on completing current task.
When context reaches ORANGE: Save all unsaved findings to workspace files immediately.
When context reaches RED: Write session handoff, save state.json, and signal session end.
```

### Proactive Save Triggers

The agent doesn't wait for overflow. At key moments it saves proactively:

1. **After every research finding:** Append to research file
2. **After every code generation:** The code is already in files (the tool wrote it)
3. **After every decision:** Append to decisions.md
4. **At YELLOW threshold:** Save scratchpad to file, update working context
5. **At ORANGE threshold:** Full state save, write partial handoff
6. **At RED threshold:** Complete handoff, signal session end

### Emergency Protocol

If context hits RED (92%+), the agent executes an emergency sequence:

```
1. STOP current task
2. Write handoff document to /workspace/progress/HANDOFF.md
3. Update state.json with current step and status
4. Update PROGRESS.md with what was accomplished
5. Triage scratchpad (promote important items to research files)
6. Signal to the framework: "Session ending, restart needed"
```

The framework then:
1. Kills the current session
2. Starts a new session with the resume bootstrap prompt
3. The new session reads state.json and continues

### Detecting Context Pressure Without Server Metrics

If the llama.cpp server doesn't report `tokens_evaluated`, the agent can estimate:

```python
def estimate_context_usage(messages: list) -> int:
    """Estimate total tokens in message history."""
    total = 0
    for msg in messages:
        # Rough estimate: 1 token per 4 characters for English
        total += len(msg.get("content", "")) // 4
        # Add overhead for role markers, formatting
        total += 10
    return total
```

A more accurate approach: count tokens for each message as it enters the history, maintaining a running total.

---

## 8. Implementation Roadmap

### Phase 1: Foundation (File Memory + Token Counting)

Build the workspace structure and file I/O tools first. This is the foundation everything else depends on.

**Components:**
- Workspace directory initializer
- File read/write/append tools with index maintenance
- Token counter (tiktoken approximation + llama.cpp exact)
- State file (state.json) manager
- Progress tracker (PROGRESS.md writer)

**Deliverable:** An agent that saves everything to files as it works.

### Phase 2: Context Compaction

Implement the three-tier compaction pipeline.

**Components:**
- Observation masker (Tier 1 -- no LLM needed)
- History summarizer (Tier 2 -- uses orchestrator model)
- Pre-compaction file saver (Tier 3 -- saves before compacting)
- Token budget manager
- Context monitor with threshold alerts

**Deliverable:** An agent that can work indefinitely without context overflow.

### Phase 3: Multi-Session Continuity

Implement session lifecycle management.

**Components:**
- Session start (SOD) bootstrap from state files
- Session end (EOD) handoff writer
- Resume logic (read state, skip completed steps)
- Scratchpad triage (promote/discard at session boundaries)

**Deliverable:** An agent that can be stopped and resumed without losing progress.

### Phase 4: Model Cascading

Implement the router for multi-model workflows.

**Components:**
- Model router (task classification)
- Prompt templates per role (orchestrator vs coder)
- Model swap integration (with existing swap-model.sh)
- Response aggregation (combining orchestrator decisions with coder output)

**Deliverable:** An agent that uses small models for planning and big models for coding.

### Phase 5: Advanced Memory (Optional)

Add vector search and sophisticated memory management.

**Components:**
- Vector store (FAISS + sentence-transformers)
- Automatic memory indexing on file save
- Semantic search tool for the agent
- Memory consolidation (merge related research files)

**Deliverable:** An agent with efficient retrieval across large workspaces.

---

## Appendix A: Key Research Sources

- [OpenHands Context Condenser](https://docs.openhands.dev/sdk/guides/context-condenser) -- LLM-based summarization, observation masking
- [OpenHands Blog: Context Condensation](https://openhands.dev/blog/openhands-context-condensensation-for-more-efficient-ai-agents) -- Performance data: 2x cost reduction, linear scaling
- [MemGPT Paper (arXiv:2310.08560)](https://arxiv.org/abs/2310.08560) -- Virtual memory paging for LLMs, self-editing memory
- [JetBrains Research: Efficient Context Management](https://blog.jetbrains.com/research/2025/12/efficient-context-management/) -- Observation masking > LLM summarization for coding agents
- [Factory.ai: Context Window Problem](https://factory.ai/news/context-window-problem) -- Hierarchical memory, repository overviews, enterprise context
- [Context Window Management in Agentic Systems](https://blog.jroddev.com/context-window-management-in-agentic-systems/) -- Practical implementation patterns, budget allocation, anti-patterns
- [Letta/MemGPT Architecture](https://docs.letta.com/concepts/memgpt/) -- Core memory + archival memory + recall memory tiers
- [llama.cpp Server API](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) -- Token counting endpoints, context tracking response fields
- [LLM Routing and Cascading (arXiv:2410.10347)](https://arxiv.org/html/2410.10347v1) -- Unified framework for routing between models of different capability
- [Interpretable Context Methodology: Folder Structure as Agent Architecture](https://arxiv.org/html/2603.16021) -- Using directory structure as the agent's cognitive architecture

## Appendix B: Anti-Patterns to Avoid

1. **Keeping research only in conversation.** If it is not in a file, it does not exist.
2. **Naive middle truncation.** LLMs have primacy/recency bias -- cutting the middle loses the most-attended information.
3. **Summarizing too eagerly.** Summaries lose detail. Mask observations first (cheap), summarize only when necessary.
4. **Over-reliance on vector search.** For coding agents, grep and file reads are faster and more precise than semantic search for most tasks.
5. **Static token budgets.** The budget must shift dynamically as conversation grows.
6. **Ignoring tool output size.** A single `cat` of a large file can consume 50K tokens. Cap tool output length.
7. **No handoff protocol.** Sessions will end. Plan for it from the start.
8. **Using the big model for everything.** Planning and navigation don't need 27B. Save VRAM and speed for code generation.
