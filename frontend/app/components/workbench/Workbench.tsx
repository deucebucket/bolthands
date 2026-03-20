import { useState } from "react";
import EditorPanel from "./EditorPanel";
import TerminalPanel from "./TerminalPanel";
import PreviewPanel from "./PreviewPanel";

type Tab = "code" | "terminal" | "preview";

const TABS: { id: Tab; label: string }[] = [
  { id: "code", label: "Code" },
  { id: "terminal", label: "Terminal" },
  { id: "preview", label: "Preview" },
];

export default function Workbench() {
  const [activeTab, setActiveTab] = useState<Tab>("code");

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "var(--bg-primary)" }}>
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid var(--border)",
          background: "var(--bg-secondary)",
          flexShrink: 0,
        }}
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: "8px 16px",
              background: "transparent",
              border: "none",
              borderBottom: activeTab === tab.id ? "2px solid var(--accent)" : "2px solid transparent",
              color: activeTab === tab.id ? "var(--text-primary)" : "var(--text-secondary)",
              cursor: "pointer",
              fontSize: "13px",
              fontWeight: activeTab === tab.id ? 600 : 400,
              fontFamily: "inherit",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div style={{ flex: 1, overflow: "hidden" }}>
        {activeTab === "code" && <EditorPanel />}
        {activeTab === "terminal" && <TerminalPanel />}
        {activeTab === "preview" && <PreviewPanel />}
      </div>
    </div>
  );
}
