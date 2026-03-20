import { useStore } from "@nanostores/react";
import { useState } from "react";
import { $previewUrl, $detectedPorts, $activePort } from "../../stores/preview";

export default function PreviewPanel() {
  const previewUrl = useStore($previewUrl);
  const detectedPorts = useStore($detectedPorts);
  const activePort = useStore($activePort);
  const [refreshKey, setRefreshKey] = useState(0);

  if (!previewUrl) {
    return (
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
        No preview available — the agent hasn't started a server yet
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-end",
          gap: "8px",
          padding: "4px 8px",
          background: "var(--bg-secondary)",
          borderBottom: "1px solid var(--border)",
          flexShrink: 0,
        }}
      >
        {detectedPorts.length > 1 && (
          <select
            value={activePort ?? ""}
            onChange={(e) => $activePort.set(Number(e.target.value))}
            style={{
              background: "var(--bg-primary)",
              color: "var(--text-primary)",
              border: "1px solid var(--border)",
              borderRadius: "4px",
              padding: "2px 6px",
              fontSize: "12px",
            }}
          >
            {detectedPorts.map((port) => (
              <option key={port} value={port}>
                Port {port}
              </option>
            ))}
          </select>
        )}
        <button
          onClick={() => setRefreshKey((k) => k + 1)}
          style={{
            background: "transparent",
            border: "1px solid var(--border)",
            borderRadius: "4px",
            color: "var(--text-primary)",
            cursor: "pointer",
            padding: "2px 8px",
            fontSize: "12px",
            fontFamily: "inherit",
          }}
        >
          Refresh
        </button>
      </div>
      <iframe
        key={refreshKey}
        src={previewUrl}
        title="Preview"
        style={{
          flex: 1,
          border: "none",
          width: "100%",
          background: "#fff",
        }}
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
      />
    </div>
  );
}
