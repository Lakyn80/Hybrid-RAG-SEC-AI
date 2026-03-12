"use client";

import { StatusPill } from "@/components/StatusPill";
import { useUiLocale } from "@/components/UiLocaleProvider";
import { translateStreamStatus } from "@/lib/i18n";
import { PipelineStepState, StreamConnectionStatus } from "@/lib/types";

interface PipelineVisualizerProps {
  steps: PipelineStepState[];
  status: StreamConnectionStatus;
  isLoading: boolean;
}

function stepTone(status: PipelineStepState["status"]) {
  switch (status) {
    case "active":
      return {
        card: "border-brand/40 bg-brand-soft text-brand animate-pulseGlow",
        dot: "bg-brand",
      };
    case "completed":
      return {
        card: "border-emerald-200 bg-emerald-50 text-emerald-700",
        dot: "bg-emerald-600",
      };
    case "error":
      return {
        card: "border-red-200 bg-red-50 text-red-700",
        dot: "bg-red-600",
      };
    default:
      return {
        card: "border-slate-200 bg-white text-slate-500",
        dot: "bg-slate-300",
      };
  }
}

export function PipelineVisualizer({
  steps,
  status,
  isLoading,
}: PipelineVisualizerProps) {
  const { copy, locale } = useUiLocale();
  return (
    <section className="panel rounded-[32px] p-5 sm:p-6">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500">{copy.pipeline.eyebrow}</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{copy.pipeline.title}</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusPill label={`${copy.common.streamLabel} ${translateStreamStatus(status, locale)}`} variant={status === "open" ? "success" : status === "fallback" ? "warning" : "neutral"} />
          <StatusPill label={isLoading ? copy.common.activeRun : copy.common.ready} variant={isLoading ? "info" : "neutral"} />
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-7">
        {steps.map((step, index) => {
          const tone = stepTone(step.status);
          const connectorActive = index < steps.length - 1 && (step.status === "active" || step.status === "completed");

          return (
            <div key={step.id} className="relative">
              <div className={`relative h-full rounded-[24px] border px-4 py-4 transition ${tone.card}`}>
                <div className="flex items-start justify-between gap-3">
                  <span className={`mt-1 h-3 w-3 rounded-full ${tone.dot}`} />
                  <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-current/70">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                </div>
                <h3 className="mt-5 text-base font-semibold tracking-tight">{step.label}</h3>
                <p className="mt-2 text-sm leading-6 text-current/80">{step.description}</p>
              </div>

              {index < steps.length - 1 ? (
                <div
                  className={`hidden md:block absolute left-[calc(100%-8px)] top-1/2 h-[2px] w-4 -translate-y-1/2 ${
                    connectorActive ? "bg-brand/60" : "bg-slate-200"
                  }`}
                />
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}
