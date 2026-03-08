import { PipelineStepId, PipelineStepStatus, StreamConnectionStatus } from "@/lib/types";

export type GraphNodeId = PipelineStepId;
export type GraphNodeState = PipelineStepStatus;

export interface GraphNodeDefinition {
  id: GraphNodeId;
  label: string;
  subtitle: string;
  accent: string;
}

export interface GraphNodeViewModel extends GraphNodeDefinition {
  state: GraphNodeState;
  order: number;
}

export interface GraphMappingContext {
  observedStreamEvents: boolean;
  streamStatus: StreamConnectionStatus;
}
