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
  const lastIdx = messages.length - 1;
  if (lastIdx < 0) return;
  const lastMsg = { ...messages[lastIdx] };
  if (lastMsg.actions?.length) {
    lastMsg.actions = [...lastMsg.actions];
    const actionIdx = lastMsg.actions.length - 1;
    lastMsg.actions[actionIdx] = {
      ...lastMsg.actions[actionIdx],
      status,
      ...(output !== undefined && { output }),
      ...(error !== undefined && { error }),
    };
  }
  messages[lastIdx] = lastMsg;
  $messages.set(messages);
}
