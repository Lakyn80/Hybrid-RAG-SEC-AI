"use client";

import { HistoryEntry } from "@/lib/types";

interface QueryHistoryProps {
  history: HistoryEntry[];
  activeQuery: string;
  onSelect: (query: string) => void;
}

function formatTime(timestamp: string) {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function QueryHistory({ history, activeQuery, onSelect }: QueryHistoryProps) {
  return (
    <section className="panel rounded-[32px] p-5 sm:p-6">
      <div className="mb-5 flex items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500">Query history</p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight text-slate-950">Previous runs</h2>
        </div>
        <div className="rounded-full border border-slate-200 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-slate-500">
          {history.length} stored
        </div>
      </div>

      {history.length === 0 ? (
        <div className="rounded-[24px] border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-sm leading-6 text-slate-500">
          No queries yet. Submit a prompt to create a replayable session history.
        </div>
      ) : (
        <div className="max-h-[440px] space-y-3 overflow-auto pr-1">
          {history.map((entry) => {
            const isActive = entry.query === activeQuery;

            return (
              <button
                key={entry.id}
                type="button"
                onClick={() => onSelect(entry.query)}
                className={`w-full rounded-[24px] border px-4 py-4 text-left transition ${
                  isActive
                    ? "border-brand/40 bg-brand-soft/70 shadow-focus"
                    : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-medium leading-6 text-slate-900">{entry.query}</p>
                  <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-slate-500">
                    {formatTime(entry.createdAt)}
                  </span>
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-slate-600">
                    {entry.status}
                  </span>
                  {entry.mode ? (
                    <span className="rounded-full bg-brand-soft px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-brand">
                      {entry.mode}
                    </span>
                  ) : null}
                  {typeof entry.cacheHit === "boolean" ? (
                    <span className="rounded-full bg-amber-50 px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-amber-700">
                      cache {entry.cacheHit ? "hit" : "miss"}
                    </span>
                  ) : null}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
