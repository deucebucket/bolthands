import { useState } from "react";
import { useStore } from "@nanostores/react";
import { $fileTree, $activeFile } from "../../stores/files";
import type { TreeNode } from "../../lib/types";

function TreeItem({ node, depth }: { node: TreeNode; depth: number }) {
  const activeFile = useStore($activeFile);
  const [expanded, setExpanded] = useState(true);
  const isActive = node.type === "file" && node.path === activeFile;

  const handleClick = () => {
    if (node.type === "directory") {
      setExpanded(!expanded);
    } else {
      $activeFile.set(node.path);
    }
  };

  return (
    <div>
      <div
        onClick={handleClick}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "4px",
          padding: "3px 8px",
          paddingLeft: `${8 + depth * 16}px`,
          cursor: "pointer",
          fontSize: "13px",
          color: "var(--text-primary)",
          background: isActive ? "rgba(var(--accent-rgb, 99, 102, 241), 0.15)" : "transparent",
          userSelect: "none",
        }}
        onMouseEnter={(e) => {
          if (!isActive) e.currentTarget.style.background = "rgba(255,255,255,0.05)";
        }}
        onMouseLeave={(e) => {
          if (!isActive) e.currentTarget.style.background = "transparent";
        }}
      >
        <span style={{ fontSize: "14px", width: "18px", textAlign: "center" }}>
          {node.type === "directory" ? (expanded ? "\u{1F4C2}" : "\u{1F4C1}") : "\u{1F4C4}"}
        </span>
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{node.name}</span>
      </div>
      {node.type === "directory" && expanded && node.children && (
        <div>
          {node.children.map((child) => (
            <TreeItem key={child.path} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function FileTree() {
  const tree = useStore($fileTree);

  if (tree.length === 0) {
    return (
      <div style={{ padding: "16px", color: "var(--text-secondary)", fontSize: "13px" }}>
        No files yet
      </div>
    );
  }

  return (
    <div style={{ paddingTop: "4px", overflow: "auto", height: "100%" }}>
      {tree.map((node) => (
        <TreeItem key={node.path} node={node} depth={0} />
      ))}
    </div>
  );
}
