import {
  NormalizedStreamEvent,
  PipelineStepId,
  PipelineStepState,
} from "@/lib/types";
import { getRuntimeCopy, translateBackendEvent } from "@/lib/i18n";

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
  const translated = translateBackendEvent(message);
  if (translated) {
    return translated;
  }

  return message
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .replace(/\b([a-z])/g, (match) => match.toUpperCase());
}

export function createInitialSteps(): PipelineStepState[] {
  const activeCopy = getRuntimeCopy();

  const stepDefinitions: Array<{
    id: PipelineStepId;
    label: string;
    description: string;
  }> = [
    {
      id: "prompt",
      label: activeCopy.pipeline.steps.prompt.label,
      description: activeCopy.pipeline.steps.prompt.description,
    },
    {
      id: "embedding",
      label: activeCopy.pipeline.steps.embedding.label,
      description: activeCopy.pipeline.steps.embedding.description,
    },
    {
      id: "retrieval",
      label: activeCopy.pipeline.steps.retrieval.label,
      description: activeCopy.pipeline.steps.retrieval.description,
    },
    {
      id: "rerank",
      label: activeCopy.pipeline.steps.rerank.label,
      description: activeCopy.pipeline.steps.rerank.description,
    },
    {
      id: "context",
      label: activeCopy.pipeline.steps.context.label,
      description: activeCopy.pipeline.steps.context.description,
    },
    {
      id: "llm",
      label: activeCopy.pipeline.steps.llm.label,
      description: activeCopy.pipeline.steps.llm.description,
    },
    {
      id: "answer",
      label: activeCopy.pipeline.steps.answer.label,
      description: activeCopy.pipeline.steps.answer.description,
    },
  ];

  return stepDefinitions.map((step) => ({
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
