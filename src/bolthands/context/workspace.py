import json


class WorkspaceMemory:
    """File-based workspace memory using a SandboxExecutor for file ops."""

    def __init__(self, executor):
        self.executor = executor

    async def init_workspace(self):
        """Create the /workspace/context/ directory."""
        await self.executor.run("mkdir -p /workspace/context")

    async def save_state(self, state: dict):
        """Write JSON state to /workspace/context/state.json."""
        json_str = json.dumps(state, indent=2)
        await self.executor.run(
            f"cat > /workspace/context/state.json << 'STATEEOF'\n{json_str}\nSTATEEOF"
        )

    async def load_state(self) -> dict | None:
        """Read /workspace/context/state.json, return None if not found."""
        result = await self.executor.run("cat /workspace/context/state.json 2>/dev/null")
        if result is None or result.strip() == "":
            return None
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return None

    async def append_progress(self, step: int, status: str, details: str):
        """Append an entry to /workspace/context/progress.md."""
        entry = f"\n## Step {step}: {status}\n{details}\n"
        await self.executor.run(
            f"cat >> /workspace/context/progress.md << 'PROGEOF'\n{entry}\nPROGEOF"
        )

    async def save_research(self, topic: str, content: str):
        """Write research content to /workspace/context/{topic}.md."""
        await self.executor.run(
            f"cat > /workspace/context/{topic}.md << 'RESEOF'\n{content}\nRESEOF"
        )

    async def get_file_index(self) -> str:
        """Read /workspace/context/file-index.md."""
        result = await self.executor.run("cat /workspace/context/file-index.md 2>/dev/null")
        return result or ""
