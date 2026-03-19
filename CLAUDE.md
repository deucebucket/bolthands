# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BoltHands is a research and development project to build an autonomous coding agent that combines:
- **Bolt.diy's frontend** (Remix/React web IDE with live preview, code editor, terminal)
- **OpenHands' backend** (Docker sandbox with real shell execution, iterative error loops)
- **Custom context management** (file-based memory, tiered compaction, multi-session continuity)
- **Local LLM inference** via llama.cpp (model cascading between 4B-9B orchestrator and 27B coder)
- **Custom fine-tuned model** (Qwen3.5-9B trained on agentic coding trajectories via Unsloth QLoRA)

The project is currently in the **research/planning phase** — no implementation code exists yet. All content is in `research/`.

## Architecture Vision

The core idea: take Bolt.diy's browser-based IDE UI and replace its one-shot LLM backend with OpenHands-style autonomous agent loops running in Docker containers. Key innovations over both projects:

1. **Incremental file-based memory** — agent writes findings to disk immediately, never relies on context alone
2. **Three-tier context compaction** — observation masking (cheap) → LLM summarization → file offload
3. **Self-aware context management** — agent monitors its own token budget and proactively saves state
4. **Model cascading** — small model for planning/navigation, large model for code generation
5. **Self-improving training loop** — log successful sessions → filter → retrain → deploy if better

## Research Documents

| File | Contents |
|------|----------|
| `research/bolt-architecture.md` | Deep dive into Bolt.diy's codebase — UI, message parser, action runner, WebContainer, LLM providers. Includes what to keep/rewrite/discard. |
| `research/openhands-architecture.md` | Deep dive into OpenHands — agent loop, Docker sandbox, tool system, condensers, skill system, frontend. |
| `research/context-management.md` | Technical design for BoltHands' memory system — file-based memory, compaction pipeline, token budgeting, session continuity, model routing. |
| `research/custom-model-training.md` | QLoRA fine-tuning plan — datasets (OpenHands trajectories, Hermes, xLAM), training config, synthetic data generation, evaluation, GGUF export, self-improvement loop. |
| `research/existing-loras-and-finetunes.md` | Catalog of existing LoRAs/fine-tunes for Qwen 9B variants (57 adapters surveyed). |
| `research/unsloth-cli-training.md` | Unsloth CLI commands and Python API for headless training. |
| `research/custom-9b-all-skills.md` | Plan for an all-skills Qwen3.5-9B fine-tune (OpenClaw agent, Windows mgmt, Plex, *arr stack). |
| `research/openhands-original-plan.md` | Original plan from OpenHands' agent (superseded by deeper research). |

## Code Philosophy

**Modular by default.** Every feature, system, and concern gets its own file — no monoliths. This is a direct lesson from Bolt.diy's 700-line system prompt and OpenHands' fragmented store architecture. Specifically:

- One file per feature/module — split aggressively rather than growing files
- Composable system prompts built from small, purpose-specific fragments (not one mega-prompt)
- Each tool definition, action handler, and condenser in its own file
- Stores/state split by domain (files, previews, editor, terminal — not one god-store)
- Clear separation between tool schema, action data model, execution handler, and result type

When adding new functionality, create a new file. When a file grows beyond a single clear responsibility, split it.

## Key Design Decisions

- **XML action format from Bolt.diy** (`<boltArtifact>`/`<boltAction>` tags) — keep the streaming message parser but consider tool calling as alternative for local models
- **Docker sandbox from OpenHands** — real shell execution, not WebContainer's limited sandbox
- **OpenAI function calling format** for tool definitions (universal, well-supported)
- **Qwen3.5 ChatML format** with `<tool_call>`/`<tool_response>` XML tags for the fine-tuned model
- **File-first memory**: workspace structure at `/workspace/{research,plans,progress,context}/`
- **Single RTX 3090** — run one model at a time, use simpler prompts for orchestration tasks rather than model swapping

## Target Stack

- **Frontend**: Remix + React 18 + Nanostores + CodeMirror 6 + xterm.js (from Bolt.diy)
- **Backend**: Python (FastAPI) + Docker runtime (from OpenHands)
- **LLM**: llama.cpp server, local inference, Qwen3.5 models
- **Training**: Unsloth QLoRA in distrobox "ai" (CUDA 12.6)

## Directories

- `research/` — completed research documents
- `docs/` — (empty, for future documentation)
- `specs/` — (empty, for future specifications)
