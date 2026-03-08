import { GraphMappingContext, GraphNodeDefinition, GraphNodeId, GraphNodeViewModel } from "@/lib/graphTypes";
import { PipelineStepState } from "@/lib/types";

export const GRAPH_NODE_DEFINITIONS: GraphNodeDefinition[] = [
  {
    id: "prompt",
    label: "Prompt",
    subtitle: "Request accepted",
    accent: "PROMPT",
  },
  {
    id: "embedding",
    label: "Embedding",
    subtitle: "Query vectorized",
    accent: "VECTOR",
  },
  {
    id: "retrieval",
    label: "Hybrid Retrieval",
    subtitle: "Qdrant + BM25",
    accent: "SEARCH",
  },
  {
    id: "rerank",
    label: "Rerank",
    subtitle: "CrossEncoder score",
    accent: "RERANK",
  },
  {
    id: "context",
    label: "Context Build",
    subtitle: "Grounded excerpts",
    accent: "CONTEXT",
  },
  {
    id: "llm",
    label: "LLM",
    subtitle: "DeepSeek response",
    accent: "LLM",
  },
  {
    id: "answer",
    label: "Answer",
    subtitle: "Final output ready",
    accent: "OUTPUT",
  },
];

const GRAPH_EVENT_PATTERNS: Array<{
  pattern: RegExp;
  nodeId: GraphNodeId;
}> = [
  { pattern: /\bquery_received\b/i, nodeId: "prompt" },
  { pattern: /\bembedding_created\b/i, nodeId: "embedding" },
  {
    pattern: /\bhybrid_retrieval_started\b|\bparallel_retrieval_rows\b|\bretrieved_rows\b/i,
    nodeId: "retrieval",
  },
  { pattern: /\breranking_started\b|\breranked_top_k\b/i, nodeId: "rerank" },
  { pattern: /\bcontext_build_started\b|\bcontext_length\b/i, nodeId: "context" },
  { pattern: /\bllm_generation_started\b|\bcalling_llm\b/i, nodeId: "llm" },
  { pattern: /\banswer_generated\b/i, nodeId: "answer" },
];

export function mapBackendEventToGraphNode(rawEvent: string): GraphNodeId | undefined {
  const normalized = String(rawEvent ?? "").trim();
  return GRAPH_EVENT_PATTERNS.find((entry) => entry.pattern.test(normalized))?.nodeId;
}

export function createInitialGraphNodes(): GraphNodeViewModel[] {
  return GRAPH_NODE_DEFINITIONS.map((definition, index) => ({
    ...definition,
    order: index + 1,
    state: "idle",
  }));
}

export function mapStepsToGraphNodes(
  steps: PipelineStepState[],
  context: GraphMappingContext,
): GraphNodeViewModel[] {
  const byId = new Map(steps.map((step) => [step.id, step]));
  const shouldRenderIdle =
    !context.observedStreamEvents &&
    (context.streamStatus === "idle" || context.streamStatus === "fallback");

  return GRAPH_NODE_DEFINITIONS.map((definition, index) => {
    const matchingStep = byId.get(definition.id);

    return {
      ...definition,
      order: index + 1,
      state: shouldRenderIdle ? "idle" : matchingStep?.status ?? "idle",
    };
  });
}
