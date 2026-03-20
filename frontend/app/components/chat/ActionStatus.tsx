import { useState } from "react";
import type { ChatAction } from "../../lib/types";

type ActionStatusProps = Pick<ChatAction, "tool" | "args" | "status" | "output" | "error">;

const statusIcons: Record<ChatAction["status"], string> = {
  pending: "\u25CB",
  running: "\u25CF",
  done: "\u2713",
  error: "\u2717",
};

const statusColors: Record<ChatAction["status"], string> = {
  pending: "var(--text-muted)",
  running: "var(--accent)",
  done: "var(--success)",
  error: "var(--error)",
};

export default function ActionStatus({ tool, args, status, output, error }: ActionStatusProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: 6,
        marginTop: 6,
        fontSize: 13,
      }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          width: "100%",
          padding: "6px 10px",
          background: "none",
          border: "none",
          color: "var(--text-primary)",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <span
          style={{
            color: statusColors[status],
            fontSize: 14,
            lineHeight: 1,
            animation: status === "running" ? "pulse 1.5s ease-in-out infinite" : undefined,
          }}
        >
          {statusIcons[status]}
        </span>
        <code
          style={{
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
            fontSize: 12,
            color: "var(--text-secondary)",
          }}
        >
          {tool}
        </code>
        <span
          style={{
            marginLeft: "auto",
            color: "var(--text-muted)",
            fontSize: 11,
          }}
        >
          {expanded ? "\u25B2" : "\u25BC"}
        </span>
      </button>

      {expanded && (
        <div
          style={{
            padding: "8px 10px",
            borderTop: "1px solid var(--border)",
            background: "var(--bg-secondary)",
          }}
        >
          <div style={{ marginBottom: 6 }}>
            <span style={{ color: "var(--text-muted)", fontSize: 11 }}>Args</span>
            <pre
              style={{
                fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
                fontSize: 11,
                color: "var(--text-secondary)",
                whiteSpace: "pre-wrap",
                wordBreak: "break-all",
                marginTop: 2,
              }}
            >
              {JSON.stringify(args, null, 2)}
            </pre>
          </div>

          {output && (
            <div style={{ marginBottom: 6 }}>
              <span style={{ color: "var(--text-muted)", fontSize: 11 }}>Output</span>
              <pre
                style={{
                  fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
                  fontSize: 11,
                  color: "var(--text-secondary)",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-all",
                  marginTop: 2,
                  maxHeight: 200,
                  overflowY: "auto",
                }}
              >
                {output}
              </pre>
            </div>
          )}

          {error && (
            <div>
              <span style={{ color: "var(--error)", fontSize: 11 }}>Error</span>
              <pre
                style={{
                  fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
                  fontSize: 11,
                  color: "var(--error)",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-all",
                  marginTop: 2,
                }}
              >
                {error}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
