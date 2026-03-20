import { useStore } from "@nanostores/react";
import Header from "../components/layout/Header";
import SplitLayout from "../components/layout/SplitLayout";
import Chat from "../components/chat/Chat";
import Workbench from "../components/workbench/Workbench";
import { $fileMap } from "../stores/files";
import { $agentState } from "../stores/agent";
import { $terminalLines } from "../stores/terminal";

export default function Index() {
  const fileMap = useStore($fileMap);
  const agentState = useStore($agentState);
  const terminalLines = useStore($terminalLines);
  const showWorkbench =
    Object.keys(fileMap).length > 0 ||
    terminalLines.length > 0 ||
    agentState === "running";

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <Header />
      <SplitLayout
        left={<Chat />}
        right={<Workbench />}
        showWorkbench={showWorkbench}
      />
    </div>
  );
}
