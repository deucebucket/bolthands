import { atom } from "nanostores";
import type { ChatMessage, ChatAction } from "../lib/types";

let msgCounter = 0;
let actionCounter = 0;

export const $messages = atom<ChatMessage[]>([]);
export const $inputValue = atom("");
export const $isSubmitting = atom(false);

export function addUserMessage(content: string) {
  const messages = [...$messages.get()];
  messages.push({
    id: `msg-${++msgCounter}`,
    role: "user",
    content,
    timestamp: new Date().toISOString(),
  });
  $messages.set(messages);
}

export function addAssistantMessage(content: string) {
  const messages = [...$messages.get()];
  messages.push({
    id: `msg-${++msgCounter}`,
    role: "assistant",
    content,
    timestamp: new Date().toISOString(),
    actions: [],
  });
  $messages.set(messages);
}

export function addAction(tool: string, args: Record<string, unknown>) {
  const messages = [...$messages.get()];
  // Find or create the current assistant message
  let lastMsg = messages[messages.length - 1];
  if (!lastMsg || lastMsg.role !== "assistant") {
    lastMsg = { id: `msg-${++msgCounter}`, role: "assistant", content: "", timestamp: new Date().toISOString(), actions: [] };
    messages.push(lastMsg);
  }
  if (!lastMsg.actions) lastMsg.actions = [];
  lastMsg.actions.push({
    id: `action-${++actionCounter}`,
    tool,
    args,
    status: "running",
  });
  $messages.set(messages);
}

export function updateLastActionStatus(status: "done" | "error", output?: string, error?: string) {
  const messages = [...$messages.get()];
  const lastMsg = messages[messages.length - 1];
  if (lastMsg?.actions?.length) {
    const lastAction = lastMsg.actions[lastMsg.actions.length - 1];
    lastAction.status = status;
    if (output) lastAction.output = output;
    if (error) lastAction.error = error;
  }
  $messages.set(messages);
}
