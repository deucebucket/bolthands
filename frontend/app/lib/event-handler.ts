import type { AgentEvent } from "./types";
import { addEvent, setAgentState } from "../stores/agent";
import { setFile, editFile } from "../stores/files";
import { addCommand, addOutput } from "../stores/terminal";
import { addAction, updateLastActionStatus, addAssistantMessage } from "../stores/chat";
import { detectPorts } from "../stores/preview";

export function handleAgentEvent(event: AgentEvent) {
  addEvent(event);

  switch (event.type) {
    case "action":
      handleAction(event.data);
      break;
    case "observation":
      handleObservation(event.data);
      break;
    case "state_change":
      handleStateChange(event.data);
      break;
    case "error":
      setAgentState("error", (event.data as any).message || "Unknown error");
      break;
  }
}

function handleAction(data: Record<string, unknown>) {
  const type = data.type as string;

  // Add to chat as action card
  addAction(type, data);

  switch (type) {
    case "cmd_run":
      addCommand(data.command as string);
      break;
    case "file_write":
      setFile(data.path as string, data.content as string);
      break;
    case "file_edit":
      editFile(data.path as string, data.old_str as string, data.new_str as string);
      break;
    case "think":
      // Think actions just show in chat, no side effects
      break;
    case "finish":
      addAssistantMessage(data.message as string);
      break;
  }
}

function handleObservation(data: Record<string, unknown>) {
  const type = data.type as string;

  switch (type) {
    case "cmd_output": {
      const stdout = (data.stdout as string) || "";
      const stderr = (data.stderr as string) || "";
      const exitCode = (data.exit_code as number) || 0;
      addOutput(stdout, stderr, exitCode);
      updateLastActionStatus(exitCode === 0 ? "done" : "error", stdout, stderr || undefined);
      detectPorts(stdout + stderr);
      break;
    }
    case "file_content":
      setFile(data.path as string, data.content as string);
      updateLastActionStatus("done");
      break;
    case "file_write_result":
    case "file_edit_result":
      updateLastActionStatus((data.success as boolean) ? "done" : "error", undefined, data.error as string);
      break;
    case "search_result":
      updateLastActionStatus("done", (data.matches as string[])?.join("\n"));
      break;
    case "think_result":
      updateLastActionStatus("done");
      break;
    case "error":
      updateLastActionStatus("error", undefined, data.message as string);
      break;
  }
}

function handleStateChange(data: Record<string, unknown>) {
  const state = data.state as string;
  if (state === "finished" || state === "error" || state === "idle" || state === "running" || state === "paused") {
    setAgentState(state as any, data.error_message as string | undefined);
  }
}
