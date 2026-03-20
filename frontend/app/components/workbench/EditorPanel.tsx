import { useStore } from "@nanostores/react";
import { $activeFile } from "../../stores/files";
import FileTree from "./FileTree";
import CodeEditor from "./CodeEditor";

export default function EditorPanel() {
  const activeFile = useStore($activeFile);

  return (
    <div style={{ display: "flex", height: "100%" }}>
      <div
        style={{
          width: "200px",
          flexShrink: 0,
          background: "var(--bg-secondary)",
          borderRight: "1px solid var(--border)",
          overflow: "auto",
        }}
      >
        <FileTree />
      </div>
      <div style={{ flex: 1, overflow: "hidden" }}>
        {activeFile ? (
          <CodeEditor />
        ) : (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: "var(--text-secondary)",
              fontSize: "14px",
            }}
          >
            Select a file from the tree
          </div>
        )}
      </div>
    </div>
  );
}
