import { useCallback, useRef, type KeyboardEvent, type ChangeEvent } from "react";
import { useStore } from "@nanostores/react";
import { $inputValue, $isSubmitting, addUserMessage } from "../../stores/chat";
import { $taskId, $agentState, setAgentState } from "../../stores/agent";
import { AgentWebSocket } from "../../lib/websocket";
import { handleAgentEvent } from "../../lib/event-handler";

const MAX_ROWS = 6;
const LINE_HEIGHT = 20;

export default function ChatInput() {
  const inputValue = useStore($inputValue);
  const isSubmitting = useStore($isSubmitting);
  const agentState = useStore($agentState);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const disabled = isSubmitting || agentState === "running";

  const autoResize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const maxHeight = LINE_HEIGHT * MAX_ROWS;
    el.style.height = `${Math.min(el.scrollHeight, maxHeight)}px`;
  }, []);

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLTextAreaElement>) => {
      $inputValue.set(e.target.value);
      autoResize();
    },
    [autoResize],
  );

  const handleSubmit = useCallback(async () => {
    const value = inputValue.trim();
    if (!value || disabled) return;

    $isSubmitting.set(true);
    addUserMessage(value);
    $inputValue.set("");

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    try {
      const res = await fetch("http://localhost:8000/task", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: value }),
      });
      const data = await res.json();
      const taskId = data.task_id as string;
      $taskId.set(taskId);
      setAgentState("running");

      const ws = new AgentWebSocket(taskId);
      ws.onEvent = handleAgentEvent;
      ws.onClose = () => {
        $isSubmitting.set(false);
      };
      ws.connect();
    } catch (err) {
      console.error("Failed to submit task:", err);
      setAgentState("error", "Failed to submit task");
      $isSubmitting.set(false);
    }
  }, [inputValue, disabled]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  return (
    <div
      style={{
        padding: "12px 16px",
        borderTop: "1px solid var(--border)",
        background: "var(--bg-secondary)",
        display: "flex",
        gap: 8,
        alignItems: "flex-end",
      }}
    >
      <textarea
        ref={textareaRef}
        value={inputValue}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={disabled ? "Agent is working..." : "Describe what you'd like to build..."}
        rows={1}
        style={{
          flex: 1,
          resize: "none",
          background: "var(--bg-tertiary)",
          border: "1px solid var(--border)",
          borderRadius: 6,
          padding: "10px 12px",
          color: "var(--text-primary)",
          fontSize: 14,
          lineHeight: `${LINE_HEIGHT}px`,
          fontFamily: "inherit",
          outline: "none",
          opacity: disabled ? 0.5 : 1,
        }}
      />
      <button
        onClick={handleSubmit}
        disabled={disabled || !inputValue.trim()}
        style={{
          background: disabled || !inputValue.trim() ? "var(--text-muted)" : "var(--accent)",
          color: "#fff",
          border: "none",
          borderRadius: 6,
          padding: "10px 16px",
          fontSize: 13,
          fontWeight: 600,
          cursor: disabled || !inputValue.trim() ? "not-allowed" : "pointer",
          whiteSpace: "nowrap",
          opacity: disabled || !inputValue.trim() ? 0.6 : 1,
        }}
      >
        Run Task
      </button>
    </div>
  );
}
