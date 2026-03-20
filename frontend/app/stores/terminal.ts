import { atom } from "nanostores";
import type { TerminalLine } from "../lib/types";

let lineCounter = 0;

export const $terminalLines = atom<TerminalLine[]>([]);

export function addCommand(command: string) {
  const lines = [...$terminalLines.get()];
  lines.push({ id: `line-${++lineCounter}`, type: "command", content: command, timestamp: new Date().toISOString() });
  $terminalLines.set(lines);
}

export function addOutput(stdout: string, stderr: string, exitCode: number) {
  const lines = [...$terminalLines.get()];
  if (stdout) {
    lines.push({ id: `line-${++lineCounter}`, type: "stdout", content: stdout, timestamp: new Date().toISOString() });
  }
  if (stderr) {
    lines.push({ id: `line-${++lineCounter}`, type: "stderr", content: stderr, exitCode, timestamp: new Date().toISOString() });
  }
  $terminalLines.set(lines);
}

export function clearTerminal() {
  $terminalLines.set([]);
  lineCounter = 0;
}
