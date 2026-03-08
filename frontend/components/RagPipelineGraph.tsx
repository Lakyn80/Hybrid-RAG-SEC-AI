"use client";

import { GraphEdge } from "@/components/GraphEdge";
import { GraphNode } from "@/components/GraphNode";
import { StatusPill } from "@/components/StatusPill";
import { mapStepsToGraphNodes } from "@/lib/graphMap";
import {
  ExecutionLogEntry,
  PipelineStepState,
  StreamConnectionStatus,
} from "@/lib/types";

interface RagPipelineGraphProps {
  observedStreamEvents: boolean;
  steps: PipelineStepState[];
  status: StreamConnectionStatus;
  logs: ExecutionLogEntry[];
  isLoading: boolean;
}

function formatTimestamp(timestamp: string | undefined) {
  if (!timestamp) {
    return "No events yet";
  }

  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function getCurrentStageLabel(steps: PipelineStepState[], isLoading: boolean) {
  const activeStep = steps.find((step) => step.status === "active");
  if (activeStep) {
    return activeStep.label;
  }

  const lastCompletedStep = [...steps]
    .reverse()
    .find((step) => step.status === "completed");

  if (lastCompletedStep && !isLoading) {
    return `${lastCompletedStep.label} complete`;
  }

  if (isLoading) {
    return "Preparing pipeline";
  }

  return "Waiting for query";
}

function getProgressPercent(steps: PipelineStepState[]) {
  const total = steps.length || 1;
  const completed = steps.filter((step) => step.status === "completed").length;
  const active = steps.some((step) => step.status === "active") ? 0.5 : 0;
  return Math.round(((completed + active) / total) * 100);
}

export function RagPipelineGraph({
  observedStreamEvents,
  steps,
  status,
  logs,
  isLoading,
}: RagPipelineGraphProps) {
  const nodes = mapStepsToGraphNodes(steps, {
    observedStreamEvents,
    streamStatus: status,
  });
  const latestLog = logs[logs.length - 1];
  const currentStageLabel = getCurrentStageLabel(steps, isLoading);
  const progressPercent = getProgressPercent(steps);
  const completedCount = steps.filter((step) => step.status === "completed").length;

  const mobileNodes = nodes;
  const tabletFirstRow = nodes.slice(0, 4);
  const tabletSecondRow = nodes.slice(4);

  return (
    <section className="w-full max-w-full overflow-hidden rounded-[32px] border border-slate-800 bg-slate-950 text-slate-100 shadow-panel">
      <div className="border-b border-slate-800 bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.14),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(16,185,129,0.12),_transparent_24%),linear-gradient(180deg,_rgba(2,6,23,0.96),_rgba(15,23,42,0.98))] px-5 py-5 sm:px-6">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-3xl">
            <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-cyan-300">
              Live orchestration
            </p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white">
              RAG pipeline graph
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              Live view of the current query as it moves through retrieval, reranking, context
              assembly, and answer generation.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <StatusPill
              label={observedStreamEvents ? "live events" : isLoading ? "awaiting events" : "idle graph"}
              variant={observedStreamEvents ? "success" : isLoading ? "info" : "neutral"}
            />
            <StatusPill
              label={`stream ${status}`}
              variant={
                status === "open"
                  ? "success"
                  : status === "error"
                    ? "danger"
                    : status === "fallback"
                      ? "warning"
                      : "neutral"
              }
            />
          </div>
        </div>

        <div className="mt-5 grid gap-3 lg:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.9fr)]">
          <div className="rounded-[24px] border border-slate-800 bg-slate-950/60 px-4 py-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-slate-500">
                  Current stage
                </p>
                <p className="mt-1 text-lg font-semibold text-white">{currentStageLabel}</p>
              </div>
              <div className="rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-slate-300">
                {progressPercent}% complete
              </div>
            </div>

            <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-slate-900">
              <div
                className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-sky-300 to-emerald-300 transition-all duration-500"
                style={{ width: `${progressPercent}%` }}
              />
            </div>

            <div className="mt-4 flex flex-wrap gap-4 text-sm text-slate-400">
              <span>Completed steps: <span className="font-semibold text-slate-200">{completedCount}/{steps.length}</span></span>
              <span>Latest update: <span className="font-semibold text-slate-200">{formatTimestamp(latestLog?.timestamp)}</span></span>
            </div>
          </div>

          <div className="rounded-[24px] border border-slate-800 bg-slate-950/60 px-4 py-4">
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-slate-500">
              Latest event
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-200">
              {latestLog?.message || "Submit a query to start the live trace."}
            </p>
          </div>
        </div>
      </div>

      <div className="px-5 py-5 sm:px-6 sm:py-6">
        <div className="rounded-[28px] border border-slate-800 bg-[radial-gradient(circle_at_center,_rgba(8,145,178,0.08),_transparent_28%),linear-gradient(180deg,_rgba(2,6,23,0.84),_rgba(15,23,42,0.96))] p-4 sm:p-5">
          <div className="flex w-full flex-col gap-3 md:hidden">
            {mobileNodes.map((node, index) => {
              const connectorActive =
                index < mobileNodes.length - 1 &&
                (node.state === "active" || node.state === "completed");

              return (
                <div key={node.id} className="flex min-w-0 flex-col">
                  <GraphNode node={node} />
                  {index < mobileNodes.length - 1 ? (
                    <GraphEdge active={connectorActive} direction="vertical" className="my-1" />
                  ) : null}
                </div>
              );
            })}
          </div>

          <div className="hidden w-full flex-col gap-4 md:flex xl:hidden">
            <div className="flex min-w-0 items-stretch gap-3">
              {tabletFirstRow.map((node, index) => {
                const connectorActive =
                  index < tabletFirstRow.length - 1 &&
                  (node.state === "active" || node.state === "completed");

                return (
                  <div key={node.id} className="flex min-w-0 flex-1 items-center gap-3">
                    <GraphNode node={node} className="flex-1" />
                    {index < tabletFirstRow.length - 1 ? (
                      <GraphEdge active={connectorActive} direction="horizontal" />
                    ) : null}
                  </div>
                );
              })}
            </div>

            <div className="flex min-w-0 items-stretch gap-3">
              {tabletSecondRow.map((node, index) => {
                const connectorActive =
                  index < tabletSecondRow.length - 1 &&
                  (node.state === "active" || node.state === "completed");

                return (
                  <div key={node.id} className="flex min-w-0 flex-1 items-center gap-3">
                    <GraphNode node={node} className="flex-1" />
                    {index < tabletSecondRow.length - 1 ? (
                      <GraphEdge active={connectorActive} direction="horizontal" />
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="hidden w-full min-w-0 items-center gap-3 xl:flex">
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
      </div>
    </section>
  );
}
