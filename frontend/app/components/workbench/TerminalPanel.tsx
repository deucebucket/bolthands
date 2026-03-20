import { useStore } from "@nanostores/react";
import { useRef, useEffect, useCallback } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";
import { $terminalLines } from "../../stores/terminal";
import type { TerminalLine } from "../../lib/types";

function formatLine(line: TerminalLine): string {
  switch (line.type) {
    case "command":
      return `\x1b[32m$ ${line.content}\x1b[0m`;
    case "stderr":
      return `\x1b[31m${line.content}\x1b[0m`;
    case "stdout":
    default:
      return line.content;
  }
}

export default function TerminalPanel() {
  const lines = useStore($terminalLines);
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const writtenCountRef = useRef(0);

  // Create terminal instance
  useEffect(() => {
    if (!containerRef.current) return;

    const term = new Terminal({
      cursorBlink: false,
      disableStdin: true,
      convertEol: true,
      fontSize: 13,
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
      theme: {
        background: "#1a1b26",
        foreground: "#c0caf5",
        cursor: "#c0caf5",
        black: "#15161e",
        red: "#f7768e",
        green: "#9ece6a",
        yellow: "#e0af68",
        blue: "#7aa2f7",
        magenta: "#bb9af7",
        cyan: "#7dcfff",
        white: "#a9b1d6",
      },
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(containerRef.current);
    fitAddon.fit();

    termRef.current = term;
    fitAddonRef.current = fitAddon;
    writtenCountRef.current = 0;

    const handleResize = () => fitAddon.fit();
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      term.dispose();
      termRef.current = null;
      fitAddonRef.current = null;
    };
  }, []);

  // Write new lines as they arrive
  useEffect(() => {
    const term = termRef.current;
    if (!term) return;

    const newLines = lines.slice(writtenCountRef.current);
    for (const line of newLines) {
      term.writeln(formatLine(line));
    }
    writtenCountRef.current = lines.length;
  }, [lines]);

  return (
    <div
      ref={containerRef}
      style={{
        height: "100%",
        width: "100%",
        padding: "4px",
        background: "#1a1b26",
        boxSizing: "border-box",
      }}
    />
  );
}
