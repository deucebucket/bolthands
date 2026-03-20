from enum import Enum


class CompactionLevel(Enum):
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"


class ContextMonitor:
    """Tracks token usage and triggers compaction at threshold levels."""

    def __init__(self, max_context: int = 131072):
        self.max_context = max_context

    def count_tokens(self, messages: list[dict]) -> int:
        """Approximate token count: len(content)/4 + 10 overhead per message."""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if content is None:
                content = ""
            total += len(content) // 4 + 10
        return total

    def check_budget(self, messages: list[dict]) -> CompactionLevel:
        """Return compaction level based on token utilization percentage."""
        tokens = self.count_tokens(messages)
        utilization = tokens / self.max_context

        if utilization >= 0.85:
            return CompactionLevel.RED
        elif utilization >= 0.75:
            return CompactionLevel.ORANGE
        elif utilization >= 0.60:
            return CompactionLevel.YELLOW
        else:
            return CompactionLevel.GREEN
