import { useStore } from "@nanostores/react";
import { $agentState, $iteration, $maxIterations } from "../../stores/agent";

const statusConfig: Record<string, { label: string; color: string; pulse?: boolean }> = {
  idle: { label: "Idle", color: "var(--text-muted)" },
  running: { label: "Running...", color: "var(--accent)", pulse: true },
  paused: { label: "Paused", color: "var(--warning)" },
  finished: { label: "Finished", color: "var(--success)" },
  error: { label: "Error", color: "var(--error)" },
};

export default function Header() {
  const agentState = useStore($agentState);
  const iteration = useStore($iteration);
  const maxIterations = useStore($maxIterations);

  const status = statusConfig[agentState] ?? statusConfig.idle;

  return (
    <header
      style={{
        width: "100%",
        height: 48,
        backgroundColor: "var(--bg-secondary)",
        borderBottom: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 16px",
        flexShrink: 0,
      }}
    >
      {/* Left: branding */}
      <span style={{ fontWeight: 700, fontSize: 16, color: "var(--accent)" }}>
        BoltHands
      </span>

      {/* Center: status indicator */}
      <span
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontSize: 13,
          color: status.color,
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            backgroundColor: status.color,
            display: "inline-block",
            animation: status.pulse ? "pulse 1.5s ease-in-out infinite" : undefined,
          }}
        />
        {status.label}
      </span>

      {/* Right: iteration counter */}
      <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
        Step {iteration}/{maxIterations}
      </span>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </header>
  );
}
