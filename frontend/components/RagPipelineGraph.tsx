"use client";

import { GraphEdge } from "@/components/GraphEdge";
import { GraphNode } from "@/components/GraphNode";
import { StatusPill } from "@/components/StatusPill";
import { mapStepsToGraphNodes } from "@/lib/graphMap";
import { PipelineStepState, StreamConnectionStatus } from "@/lib/types";

interface RagPipelineGraphProps {
  observedStreamEvents: boolean;
  steps: PipelineStepState[];
  status: StreamConnectionStatus;
}

export function RagPipelineGraph({
  observedStreamEvents,
  steps,
  status,
}: RagPipelineGraphProps) {
  const nodes = mapStepsToGraphNodes(steps, {
    observedStreamEvents,
    streamStatus: status,
  });
  const firstTabletRow = nodes.slice(0, 3);
  const secondTabletRow = nodes.slice(3);

  return (
    <section className="w-full max-w-full overflow-hidden rounded-[32px] border border-slate-800 bg-slate-950 px-5 py-5 text-slate-100 shadow-panel sm:px-6 sm:py-6">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-slate-400">
            Live graph
          </p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white">
            RAG pipeline graph
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
            Live node graph driven by existing stream state. It stays visible even when the stream
            falls back or remains idle.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusPill
            label={observedStreamEvents ? "events observed" : "idle graph"}
            variant={observedStreamEvents ? "success" : "neutral"}
          />
          <StatusPill
            label={`stream ${status}`}
            variant={status === "open" ? "success" : status === "error" ? "danger" : status === "fallback" ? "warning" : "neutral"}
          />
        </div>
      </div>

      <div className="w-full max-w-full overflow-hidden rounded-[28px] border border-slate-800 bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.08),_transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(16,185,129,0.08),_transparent_22%),linear-gradient(180deg,_rgba(2,6,23,0.92),_rgba(15,23,42,0.96))] px-4 py-5 sm:px-5">
        <div className="flex w-full max-w-full flex-col gap-4 sm:hidden">
          {nodes.map((node, index) => {
            const connectorActive =
              index < nodes.length - 1 &&
              (node.state === "active" || node.state === "completed");

            return (
              <div key={node.id} className="flex min-w-0 flex-col">
                <GraphNode node={node} />
                {index < nodes.length - 1 ? (
                  <GraphEdge active={connectorActive} direction="vertical" />
                ) : null}
              </div>
            );
          })}
        </div>

        <div className="hidden w-full max-w-full flex-col gap-5 sm:flex lg:hidden">
          <div className="flex min-w-0 items-stretch gap-3 overflow-hidden">
            {firstTabletRow.map((node, index) => {
              const connectorActive =
                index < firstTabletRow.length - 1 &&
                (node.state === "active" || node.state === "completed");

              return (
                <div key={node.id} className="flex min-w-0 flex-1 items-center gap-3">
                  <GraphNode node={node} className="flex-1" />
                  {index < firstTabletRow.length - 1 ? (
                    <GraphEdge active={connectorActive} direction="horizontal" />
                  ) : null}
                </div>
              );
            })}
          </div>

          <div className="flex min-w-0 items-stretch gap-3 overflow-hidden">
            {secondTabletRow.map((node, index) => {
              const connectorActive =
                index < secondTabletRow.length - 1 &&
                (node.state === "active" || node.state === "completed");

              return (
                <div key={node.id} className="flex min-w-0 flex-1 items-center gap-3">
                  <GraphNode node={node} className="flex-1" />
                  {index < secondTabletRow.length - 1 ? (
                    <GraphEdge active={connectorActive} direction="horizontal" />
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>

        <div className="hidden w-full max-w-full min-w-0 items-center gap-3 overflow-hidden lg:flex">
          {nodes.map((node, index) => {
            const connectorActive =
              index < nodes.length - 1 &&
              (node.state === "active" || node.state === "completed");

            return (
              <div key={node.id} className="flex min-w-0 flex-1 items-center gap-3">
                <GraphNode node={node} className="flex-1" />
                {index < nodes.length - 1 ? (
                  <GraphEdge active={connectorActive} direction="horizontal" />
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
