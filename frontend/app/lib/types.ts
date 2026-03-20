// Agent events from WebSocket
export interface AgentEvent {
  type: "action" | "observation" | "state_change" | "error";
  timestamp: string;
  iteration: number;
  data: Record<string, unknown>;
}

// Action types (discriminated by type field)
export type ActionType = "cmd_run" | "file_read" | "file_write" | "file_edit" | "search_files" | "think" | "finish";

export interface ActionData {
  type: ActionType;
  [key: string]: unknown;
}

export interface ObservationData {
  type: string;
  [key: string]: unknown;
}

// Agent status
export type AgentState = "idle" | "running" | "paused" | "finished" | "error";

export interface AgentStatus {
  task_id: string;
  state: AgentState;
  iteration: number;
  max_iterations: number;
  last_action_type: string | null;
  error_message: string | null;
}

// Chat
export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  actions?: ChatAction[];
}

export interface ChatAction {
  id: string;
  tool: string;
  args: Record<string, unknown>;
  status: "pending" | "running" | "done" | "error";
  output?: string;
  error?: string;
}

// Terminal
export interface TerminalLine {
  id: string;
  type: "command" | "stdout" | "stderr";
  content: string;
  exitCode?: number;
  timestamp: string;
}

// Files
export interface FileNode {
  path: string;
  content: string;
  locked: boolean;
  lastModified: string;
}

export interface TreeNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: TreeNode[];
}
