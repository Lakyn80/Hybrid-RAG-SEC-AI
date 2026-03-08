export type PipelineStepId =
  | "prompt"
  | "embedding"
  | "retrieval"
  | "rerank"
  | "context"
  | "llm"
  | "answer";

export type PipelineStepStatus = "idle" | "active" | "completed" | "error";

export type StreamConnectionStatus =
  | "idle"
  | "connecting"
  | "open"
  | "fallback"
  | "closed"
  | "error";

export interface AskRequest {
  query: string;
  company?: string;
  form?: string;
}

export interface AskResponse {
  query: string;
  answer: string;
  mode: string;
  sources: string;
  cache_hit: boolean;
}

export interface ExecutionLogEntry {
  id: string;
  timestamp: string;
  message: string;
  raw: string;
  stepId?: PipelineStepId;
  severity: "info" | "system" | "error";
}

export interface PipelineStepState {
  id: PipelineStepId;
  label: string;
  description: string;
  status: PipelineStepStatus;
}

export interface NormalizedStreamEvent {
  raw: string;
  message: string;
  stepId?: PipelineStepId;
  severity: "info" | "error";
  terminal: boolean;
}

export interface RunState {
  query: string;
  logs: ExecutionLogEntry[];
  steps: PipelineStepState[];
  answer: AskResponse | null;
  error: string | null;
  isLoading: boolean;
  isStreaming: boolean;
  streamStatus: StreamConnectionStatus;
  startedAt: string | null;
  observedStreamEvents: boolean;
}

export interface HistoryEntry {
  id: string;
  query: string;
  createdAt: string;
  answer?: string;
  mode?: string;
  cacheHit?: boolean;
  status: "success" | "error";
  snapshot: RunState;
}
