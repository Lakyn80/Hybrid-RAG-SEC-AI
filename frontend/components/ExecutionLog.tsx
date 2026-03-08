"use client";

import { useEffect, useRef } from "react";

import { StatusPill } from "@/components/StatusPill";
import { ExecutionLogEntry, StreamConnectionStatus } from "@/lib/types";

interface ExecutionLogProps {
  logs: ExecutionLogEntry[];
  status: StreamConnectionStatus;
  isLoading: boolean;
}

function statusLabel(status: StreamConnectionStatus) {
  switch (status) {
    case "connecting":
      return { label: "Connecting", variant: "info" as const };
    case "open":
      return { label: "Live stream", variant: "success" as const };
    case "fallback":
      return { label: "Answer only", variant: "warning" as const };
    case "error":
      return { label: "Stream error", variant: "danger" as const };
    case "closed":
      return { label: "Closed", variant: "neutral" as const };
    default:
      return { label: "Idle", variant: "neutral" as const };
  }
}

function formatTimestamp(timestamp: string) {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function ExecutionLog({ logs, status, isLoading }: ExecutionLogProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const element = scrollRef.current;
    if (!element) {
      return;
    }

    element.scrollTop = element.scrollHeight;
  }, [logs]);

  const pill = statusLabel(status);

  return (
    <section className="panel rounded-[32px] p-5 sm:p-6">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500">Execution log</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">Live pipeline trace</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusPill label={pill.label} variant={pill.variant} />
          {isLoading ? <StatusPill label="Run active" variant="info" /> : <StatusPill label="Standby" variant="neutral" />}
        </div>
      </div>

      <div
        ref={scrollRef}
        className="max-h-[420px] overflow-auto rounded-[26px] border border-slate-200 bg-slate-950 px-3 py-3 sm:px-4"
      >
        {logs.length === 0 ? (
          <div className="flex min-h-[320px] items-center justify-center rounded-[20px] border border-dashed border-slate-700 bg-slate-900/70 px-6 text-center text-sm leading-7 text-slate-400">
            Start a query to watch backend events arrive here in real time.
          </div>
        ) : (
          <ol className="space-y-2">
            {logs.map((entry, index) => {
              const tone =
                entry.severity === "error"
                  ? "border-red-500/30 bg-red-950/30 text-red-100"
                  : entry.severity === "system"
                    ? "border-cyan-500/20 bg-cyan-950/20 text-cyan-100"
                    : "border-slate-700 bg-slate-900 text-slate-100";

              return (
                <li
                  key={entry.id}
                  className={`animate-slideFade rounded-[20px] border px-3 py-3 ${tone}`}
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-current/20 font-mono text-[11px]">
                      {String(index + 1).padStart(2, "0")}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-slate-400">
                          {formatTimestamp(entry.timestamp)}
                        </p>
                        {entry.stepId ? (
                          <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-slate-400">{entry.stepId}</p>
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
