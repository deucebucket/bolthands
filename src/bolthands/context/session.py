from bolthands.context.workspace import WorkspaceMemory


class SessionManager:
    """Handles session lifecycle: start, resume, and handoff."""

    def __init__(self, workspace: WorkspaceMemory):
        self.workspace = workspace

    async def start_session(self) -> dict | None:
        """Start or resume a session.

        Returns the existing state dict if resuming, or None for a fresh start.
        """
        state = await self.workspace.load_state()
        if state is not None:
            return state

        await self.workspace.init_workspace()
        return None

    async def end_session(self, status: str, summary: str):
        """End the session with a handoff document and updated state."""
        handoff = (
            f"# Session Handoff\n\n"
            f"## Status: {status}\n\n"
            f"## Summary\n{summary}\n"
        )
        await self.workspace.executor.run(
            f"cat > /workspace/context/handoff.md << 'HANDOFF'\n{handoff}\nHANDOFF"
        )

        await self.workspace.save_state({
            "status": status,
            "summary": summary,
        })

    def build_resume_prompt(self, state: dict) -> str:
        """Build a prompt for the agent to resume from saved state."""
        return (
            "You are resuming work. Read /workspace/context/state.json for "
            "where you left off. Read /workspace/context/progress.md for "
            "history. Continue from the current step."
        )
