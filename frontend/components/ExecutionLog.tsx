"use client";

import { useEffect, useRef } from "react";

import { StatusPill } from "@/components/StatusPill";
import { useUiLocale } from "@/components/UiLocaleProvider";
import { translatePipelineStep, translateStreamStatus, type UiLocale } from "@/lib/i18n";
import { ExecutionLogEntry, StreamConnectionStatus } from "@/lib/types";

interface ExecutionLogProps {
  logs: ExecutionLogEntry[];
  status: StreamConnectionStatus;
  isLoading: boolean;
}

function statusLabel(status: StreamConnectionStatus, locale: UiLocale) {
  switch (status) {
    case "connecting":
      return { label: translateStreamStatus(status, locale), variant: "info" as const };
    case "open":
      return { label: translateStreamStatus(status, locale), variant: "success" as const };
    case "fallback":
      return { label: translateStreamStatus(status, locale), variant: "warning" as const };
    case "error":
      return { label: translateStreamStatus(status, locale), variant: "danger" as const };
    case "closed":
      return { label: translateStreamStatus(status, locale), variant: "neutral" as const };
    default:
      return { label: translateStreamStatus(status, locale), variant: "neutral" as const };
  }
}

function formatTimestamp(timestamp: string, locale: UiLocale) {
  return new Date(timestamp).toLocaleTimeString(locale, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function ExecutionLog({ logs, status, isLoading }: ExecutionLogProps) {
  const { copy, locale } = useUiLocale();
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const element = scrollRef.current;
    if (!element) {
      return;
    }

    element.scrollTop = element.scrollHeight;
  }, [logs]);

  const pill = statusLabel(status, locale);

  return (
    <section className="panel p-5 sm:p-6">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500">{copy.executionLog.eyebrow}</p>
          <h2 className="text-metallic-gold mt-2 text-2xl font-semibold tracking-tight">{copy.executionLog.title}</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusPill label={pill.label} variant={pill.variant} />
          {isLoading ? <StatusPill label={copy.common.activeRun} variant="info" /> : <StatusPill label={copy.common.standby} variant="neutral" />}
        </div>
      </div>

      <div
        ref={scrollRef}
        className="max-h-[420px] overflow-auto border border-line bg-[#090909] px-3 py-3 sm:px-4"
      >
        {logs.length === 0 ? (
          <div className="flex min-h-[320px] items-center justify-center border border-dashed border-line bg-[#0f0f0f] px-6 text-center text-sm leading-7 text-slate-400">
            {copy.executionLog.empty}
          </div>
        ) : (
          <ol className="space-y-2">
            {logs.map((entry, index) => {
              const tone =
                entry.severity === "error"
                  ? "border-red-500/30 bg-red-950/20 text-red-100"
                  : entry.severity === "system"
                    ? "border-[#f5d15a]/25 bg-[#f5d15a]/10 text-[#f7e3a0]"
                    : "border-line bg-[#111111] text-slate-100";

              return (
                <li
                  key={entry.id}
                  className={`animate-slideFade border px-3 py-3 ${tone}`}
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-[2px] border border-current/20 font-mono text-[11px]">
                      {String(index + 1).padStart(2, "0")}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-slate-400">
                          {formatTimestamp(entry.timestamp, locale)}
                        </p>
                        {entry.stepId ? (
                          <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-slate-400">{translatePipelineStep(entry.stepId, locale)}</p>
                        ) : null}
                      </div>
                      <p className="mt-2 break-words text-sm leading-6 text-current">{entry.message}</p>
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </section>
  );
}
