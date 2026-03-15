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
        card: "border-[#f5d15a]/60 bg-[linear-gradient(180deg,rgba(250,220,120,0.12),rgba(18,18,18,0.98))] text-slate-100 animate-pulseGlow",
        dot: "bg-[#f5d15a] shadow-[0_0_18px_rgba(245,209,90,0.75)]",
      };
    case "completed":
      return {
        card: "border-slate-500 bg-[#121212] text-slate-100",
        dot: "bg-slate-200",
      };
    case "error":
      return {
        card: "border-red-500/40 bg-red-500/10 text-red-100",
        dot: "bg-red-600",
      };
    default:
      return {
        card: "border-line bg-[#0d0d0d] text-slate-500",
        dot: "bg-slate-600",
      };
  }
}

export function PipelineVisualizer({
  steps,
  status,
  isLoading,
}: PipelineVisualizerProps) {
  const { copy, locale } = useUiLocale();
  const dataValidationLabel =
    locale === "ru" ? "Проверка данных" : locale === "en" ? "Data validation" : "Datové ověření";
  const checkpointsLabel =
    locale === "ru" ? "Контрольные точки" : locale === "en" ? "Checkpoints" : "Kontrolní body";
  const primarySteps = steps.filter((step) =>
    ["embedding", "retrieval", "rerank", "llm"].includes(step.id),
  );
  const secondarySteps = steps.filter((step) =>
    !["embedding", "retrieval", "rerank", "llm"].includes(step.id),
  );

  return (
    <section className="panel p-5 sm:p-6">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500">{copy.pipeline.eyebrow}</p>
          <h2 className="text-metallic-gold mt-2 text-2xl font-semibold tracking-tight">{copy.pipeline.title}</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusPill label={`${copy.common.streamLabel} ${translateStreamStatus(status, locale)}`} variant={status === "open" ? "success" : status === "fallback" ? "warning" : "neutral"} />
          <StatusPill label={isLoading ? copy.common.activeRun : copy.common.ready} variant={isLoading ? "info" : "neutral"} />
        </div>
      </div>

      <div className="grid gap-px border border-line bg-line md:grid-cols-4">
        {primarySteps.map((step, index) => {
          const tone = stepTone(step.status);
          const connectorActive =
            index < primarySteps.length - 1 &&
            (step.status === "active" || step.status === "completed");
          const localizedStep = copy.pipeline.steps[step.id];

          return (
            <div key={step.id} className="relative bg-paper">
              <div className={`relative h-full min-h-[190px] border px-4 py-5 transition ${tone.card}`}>
                <div className="flex items-start justify-between gap-3">
                  <span className={`mt-1 h-3 w-3 rounded-full ${tone.dot}`} />
                  <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-current/70">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                </div>
                <div className="mt-10">
                  <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-current/55">
                    {dataValidationLabel}
                  </p>
                  <h3 className="text-metallic-gold mt-3 text-base font-semibold tracking-tight">{localizedStep.label}</h3>
                  <p className="mt-3 text-sm leading-6 text-current/80">{localizedStep.description}</p>
                </div>
              </div>

              {index < primarySteps.length - 1 ? (
                <div
                  className={`hidden md:block absolute left-[calc(100%-1px)] top-[29px] h-px w-[calc(100%+2px)] ${
                    connectorActive ? "bg-[#f5d15a]/75" : "bg-slate-700"
                  }`}
                />
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="mt-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-slate-500">
          {checkpointsLabel}
        </p>
        <div className="mt-3 grid gap-px border border-line bg-line sm:grid-cols-3">
          {secondarySteps.map((step) => {
            const tone = stepTone(step.status);
            const localizedStep = copy.pipeline.steps[step.id];

            return (
              <div key={step.id} className={`border px-4 py-3 ${tone.card}`}>
                <div className="flex items-center gap-3">
                  <span className={`h-2.5 w-2.5 rounded-full ${tone.dot}`} />
                  <div>
                    <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-current/60">
                      {localizedStep.label}
                    </p>
                    <p className="mt-1 text-xs leading-5 text-current/80">{localizedStep.description}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
