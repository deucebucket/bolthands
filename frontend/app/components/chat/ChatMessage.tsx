import type { ChatMessage as ChatMessageType } from "../../lib/types";
import ActionStatus from "./ActionStatus";

interface ChatMessageProps {
  message: ChatMessageType;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      style={{
        padding: "12px 16px",
        background: isUser ? "var(--bg-tertiary)" : "transparent",
        borderRadius: isUser ? 8 : 0,
        marginBottom: 8,
      }}
    >
      <div
        style={{
          fontSize: 11,
          color: "var(--text-muted)",
          marginBottom: 4,
          fontWeight: 600,
          textTransform: "uppercase" as const,
          letterSpacing: "0.05em",
        }}
      >
        {isUser ? "You" : "Assistant"}
      </div>

      {message.content && (
        <div
          style={{
            fontSize: 14,
            lineHeight: 1.6,
            color: "var(--text-primary)",
            whiteSpace: "pre-wrap",
          }}
        >
          {message.content}
        </div>
      )}

      {message.actions && message.actions.length > 0 && (
        <div style={{ marginTop: 8 }}>
          {message.actions.map((action) => (
            <ActionStatus
              key={action.id}
              tool={action.tool}
              args={action.args}
              status={action.status}
              output={action.output}
              error={action.error}
            />
          ))}
        </div>
      )}
    </div>
  );
}
