import { atom } from "nanostores";
import type { AgentEvent, AgentState } from "../lib/types";

export const $taskId = atom<string | null>(null);
export const $agentState = atom<AgentState>("idle");
export const $iteration = atom(0);
export const $maxIterations = atom(25);
export const $events = atom<AgentEvent[]>([]);
export const $errorMessage = atom<string | null>(null);

export function resetAgent() {
  $taskId.set(null);
  $agentState.set("idle");
  $iteration.set(0);
  $events.set([]);
  $errorMessage.set(null);
}

export function addEvent(event: AgentEvent) {
  $events.set([...$events.get(), event]);
  $iteration.set(event.iteration);
}

export function setAgentState(state: AgentState, error?: string) {
  $agentState.set(state);
  if (error) $errorMessage.set(error);
}
