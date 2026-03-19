# OpenHands Original Plan (recovered from agent context)

> This was created by OpenHands' Qwen3-Coder agent before it lost context.
> Kept for reference but superseded by our deeper research.

## Key Takeaway from OpenHands' Analysis

**"Add agent backend to Bolt.diy" rather than adding UI to OpenHands**

Reasoning: Bolt.diy is primarily a frontend with a simple backend, while OpenHands
is agent-centric. It's easier to replace Bolt.diy's one-shot backend with OpenHands'
autonomous agent loop than to rebuild OpenHands' UI from scratch.

## Their Estimated Timeline
- UI Integration: 2-3 weeks
- Backend Integration: 3-4 weeks
- Preview Sync: 1-2 weeks
- Error Handling: 1 week
- Testing: 1-2 weeks
- **Total: 8-12 weeks**

## Our Additional Requirements (not in their plan)
- Built-in code RAG with web search (SearXNG integration)
- Error-driven learning (log errors → search → store solutions → never repeat)
- Incremental file-based memory (agent saves research as it goes, never relies on context alone)
- Context compaction (summarize old messages, keep working state)
- Model cascading (9B for orchestration, 30B for heavy coding)
- Auto-updating knowledge base (watch framework releases, re-index docs)
- Self-improving system (learns from every session)
