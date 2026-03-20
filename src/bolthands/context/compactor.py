from bolthands.context.monitor import CompactionLevel


class Compactor:
    """Three-tier compaction pipeline for conversation history."""

    def __init__(self, llm_client, max_output_length: int = 10000):
        self.llm_client = llm_client
        self.max_output_length = max_output_length

    async def compact(
        self, messages: list[dict], level: CompactionLevel
    ) -> list[dict]:
        """Apply compaction based on the given level."""
        if level == CompactionLevel.GREEN:
            return messages

        result = list(messages)

        if level == CompactionLevel.RED:
            result = await self.tier3_offload(result)

        if level in (CompactionLevel.YELLOW, CompactionLevel.ORANGE, CompactionLevel.RED):
            result = self.tier1_mask(result)

        if level in (CompactionLevel.ORANGE, CompactionLevel.RED):
            result = await self.tier2_summarize(result)

        return result

    def tier1_mask(
        self, messages: list[dict], keep_recent: int = 10
    ) -> list[dict]:
        """Replace old tool response content with a short summary.

        Only masks messages with role='tool'. System and user messages
        are never masked. The most recent `keep_recent` messages are kept
        intact.
        """
        result = list(messages)
        cutoff = len(result) - keep_recent

        for i in range(cutoff):
            msg = result[i]
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                if content is None:
                    content = ""
                first_line = content.split("\n")[0] if content else ""
                char_count = len(content)
                result[i] = {
                    **msg,
                    "content": f"[Output masked, was {char_count} chars] {first_line}...",
                }

        return result

    async def tier2_summarize(self, messages: list[dict]) -> list[dict]:
        """Summarize oldest messages using the LLM, keeping recent 10 pairs."""
        keep_recent = 20  # 10 message pairs

        if len(messages) <= keep_recent + 1:
            return messages

        # Separate system message and initial user task
        system_msgs = []
        rest = []
        for msg in messages:
            if msg.get("role") == "system" and not rest:
                system_msgs.append(msg)
            else:
                rest.append(msg)

        if len(rest) <= keep_recent:
            return messages

        to_summarize = rest[:-keep_recent]
        to_keep = rest[-keep_recent:]

        # Build the summary prompt
        history_text = "\n".join(
            f"[{m.get('role', 'unknown')}]: {m.get('content', '')[:500]}"
            for m in to_summarize
        )

        prompt = (
            "Summarize this conversation history. Preserve: original goal, "
            "files modified, decisions made, current approach, what needs to "
            "happen next. Be concise (under 300 tokens).\n\n"
            f"{history_text}"
        )

        summary = await self.llm_client.generate(prompt)

        summary_msg = {
            "role": "system",
            "content": f"[Conversation summary]\n{summary}",
        }

        return system_msgs + [summary_msg] + to_keep

    async def tier3_offload(self, messages: list[dict], executor=None) -> list[dict]:
        """Extract key information and save to workspace files before summarizing."""
        # Extract code snippets from messages
        code_snippets = []
        decisions = []

        for msg in messages:
            content = msg.get("content", "") or ""

            # Look for code blocks
            if "```" in content:
                lines = content.split("\n")
                in_block = False
                block = []
                for line in lines:
                    if line.strip().startswith("```"):
                        if in_block:
                            code_snippets.append("\n".join(block))
                            block = []
                        in_block = not in_block
                    elif in_block:
                        block.append(line)

            # Look for decision-like statements
            for line in content.split("\n"):
                lower = line.lower()
                if any(
                    kw in lower
                    for kw in ["decided to", "decision:", "chose ", "going with"]
                ):
                    decisions.append(line.strip())

        if executor is not None:
            if code_snippets:
                code_content = "\n\n---\n\n".join(code_snippets)
                await executor.run(
                    f"cat > /workspace/context/extracted_code.md << 'CODEEOF'\n"
                    f"{code_content}\nCODEEOF"
                )

            if decisions:
                decisions_content = "\n".join(f"- {d}" for d in decisions)
                await executor.run(
                    f"cat >> /workspace/context/decisions.md << 'DECEOF'\n"
                    f"{decisions_content}\nDECEOF"
                )

        return messages
