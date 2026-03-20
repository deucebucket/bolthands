import { useRef, useEffect } from "react";
import { useStore } from "@nanostores/react";
import { $messages } from "../../stores/chat";
import { $agentState } from "../../stores/agent";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";

export default function Chat() {
  const messages = useStore($messages);
  const agentState = useStore($agentState);
  const scrollRef = useRef<HTMLDivElement>(null);

  const isEmpty = messages.length === 0 && agentState === "idle";

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: "var(--bg-primary)",
      }}
    >
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px 12px",
        }}
      >
        {isEmpty ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: "var(--text-muted)",
              fontSize: 18,
              fontWeight: 500,
            }}
          >
            What would you like to build?
          </div>
        ) : (
          messages.map((msg) => <ChatMessage key={msg.id} message={msg} />)
        )}
      </div>

      <ChatInput />
    </div>
  );
}
