import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";

interface SplitLayoutProps {
  left: React.ReactNode;
  right: React.ReactNode;
  showWorkbench: boolean;
}

export default function SplitLayout({ left, right, showWorkbench }: SplitLayoutProps) {
  return (
    <div style={{ flex: 1, overflow: "hidden" }}>
      <PanelGroup direction="horizontal" style={{ height: "100%" }}>
        <Panel defaultSize={showWorkbench ? 35 : 100} minSize={20}>
          {left}
        </Panel>

        {showWorkbench && (
          <>
            <PanelResizeHandle
              style={{
                width: 4,
                backgroundColor: "var(--border)",
                cursor: "col-resize",
                transition: "background-color 150ms",
              }}
              className="resize-handle"
            />
            <Panel defaultSize={65} minSize={30}>
              {right}
            </Panel>
          </>
        )}
      </PanelGroup>
    </div>
  );
}
