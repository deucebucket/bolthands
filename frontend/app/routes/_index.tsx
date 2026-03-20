import { useStore } from "@nanostores/react";
import Header from "../components/layout/Header";
import SplitLayout from "../components/layout/SplitLayout";
import { $fileMap } from "../stores/files";
import { $agentState } from "../stores/agent";

export default function Index() {
  const fileMap = useStore($fileMap);
  const agentState = useStore($agentState);
  const showWorkbench = Object.keys(fileMap).length > 0 || agentState === "running";

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <Header />
      <SplitLayout
        left={
          <div
            style={{
              height: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--text-secondary)",
            }}
          >
            Chat panel (coming soon)
          </div>
        }
        right={
          <div
            style={{
              height: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--text-secondary)",
            }}
          >
            Workbench panel (coming soon)
          </div>
        }
        showWorkbench={showWorkbench}
      />
    </div>
  );
}
