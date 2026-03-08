import {
  NormalizedStreamEvent,
  PipelineStepId,
  PipelineStepState,
} from "@/lib/types";

const PIPELINE_STEP_DEFINITIONS: Array<{
  id: PipelineStepId;
  label: string;
  description: string;
}> = [
  {
    id: "prompt",
    label: "Prompt",
    description: "Incoming user request enters the runtime graph.",
  },
  {
    id: "embedding",
    label: "Embedding",
    description: "Query gets transformed into vector space for retrieval.",
  },
  {
    id: "retrieval",
    label: "Hybrid Retrieval",
    description: "Qdrant and BM25 search run and merge their candidates.",
  },
  {
    id: "rerank",
    label: "Rerank",
    description: "CrossEncoder rescoring refines the highest-value chunks.",
  },
  {
    id: "context",
    label: "Context Build",
    description: "Top grounded excerpts are formatted for answer generation.",
  },
  {
    id: "llm",
    label: "LLM",
    description: "DeepSeek generates the final grounded response.",
  },
  {
    id: "answer",
    label: "Answer",
    description: "Final answer and sources are returned to the interface.",
  },
];

const EVENT_PATTERNS: Array<{
  pattern: RegExp;
  stepId: PipelineStepId;
  terminal?: boolean;
}> = [
  { pattern: /\bquery_received\b|\bquery_started\b|\bquery_submitted\b/i, stepId: "prompt" },
  { pattern: /\bembedding_created\b|\bembedding_started\b|\bembedding_generated\b/i, stepId: "embedding" },
  {
    pattern:
      /\bparallel_retrieval_rows\b|\bretrieved_rows\b|\bhybrid_retrieval\b|\bvector_search\b|\bbm25\b|\bretrieval_started\b/i,
    stepId: "retrieval",
  },
  { pattern: /\breranked_top_k\b|\breranking\b|\brerank_score\b/i, stepId: "rerank" },
  { pattern: /\bcontext_length\b|\bcontext_built\b|\bcontext_build\b/i, stepId: "context" },
  { pattern: /\bcalling_llm\b|\bllm_generation_started\b|\bllm_ms\b|\bllm_generation\b/i, stepId: "llm" },
  { pattern: /\banswer_generated\b|\banswer_ready\b|\bcompleted\b|\bdone\b/i, stepId: "answer", terminal: true },
];

function extractRawMessage(payload: string): string {
  const trimmed = String(payload ?? "").trim();
  if (!trimmed) {
    return "empty_event";
  }

  try {
    const parsed = JSON.parse(trimmed) as Record<string, unknown>;
    const candidate =
      parsed.message ??
      parsed.event ??
      parsed.status ??
      parsed.log ??
      parsed.data;

    if (typeof candidate === "string" && candidate.trim()) {
      return candidate.trim();
    }
  } catch {
    // Keep raw payload if it is not JSON.
  }

  return trimmed;
}

function humanizeMessage(message: string): string {
  return message
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .replace(/\b([a-z])/g, (match) => match.toUpperCase());
}

export function createInitialSteps(): PipelineStepState[] {
  return PIPELINE_STEP_DEFINITIONS.map((step) => ({
    ...step,
    status: "idle",
  }));
}

export function mapBackendEvent(payload: string): NormalizedStreamEvent {
  const raw = extractRawMessage(payload);
  const severity = /\berror\b|\bfailed\b|\bexception\b/i.test(raw) ? "error" : "info";
  const rule = EVENT_PATTERNS.find((entry) => entry.pattern.test(raw));

  return {
    raw,
    message: humanizeMessage(raw),
    stepId: rule?.stepId,
    severity,
    terminal: rule?.terminal ?? false,
  };
}
