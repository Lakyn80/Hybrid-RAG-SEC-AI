"use client";

import { useUiLocale } from "@/components/UiLocaleProvider";
import { translateAnswerMode, translateHistoryStatus } from "@/lib/i18n";
import { HistoryEntry } from "@/lib/types";

interface QueryHistoryProps {
  activeHistoryId: string | null;
  cacheMessage: string | null;
  history: HistoryEntry[];
  isDeletingCache: boolean;
  onClearAll: () => void;
  onDeleteCache: () => void;
  onDelete: (entryId: string) => void;
  onRestore: (entryId: string) => void;
  onRunAgain: (entryId: string) => void;
}

function formatTime(timestamp: string, locale: string) {
  return new Date(timestamp).toLocaleTimeString(locale, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function QueryHistory({
  activeHistoryId,
  cacheMessage,
  history,
  isDeletingCache,
  onClearAll,
  onDeleteCache,
  onDelete,
  onRestore,
  onRunAgain,
}: QueryHistoryProps) {
  const { copy, locale } = useUiLocale();
  return (
    <section className="panel rounded-[32px] p-5 sm:p-6">
      <div className="mb-5 flex items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500">
            {copy.queryHistory.eyebrow}
          </p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight text-slate-950">
            {copy.queryHistory.title}
          </h2>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="rounded-full border border-slate-200 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-slate-500">
            {copy.queryHistory.stored(history.length)}
          </div>
          <button
            type="button"
            onClick={onDeleteCache}
            disabled={isDeletingCache}
            className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-amber-700 transition hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isDeletingCache ? copy.queryHistory.deletingCache : copy.queryHistory.deleteCache}
          </button>
          {history.length > 0 ? (
            <button
              type="button"
              onClick={onClearAll}
              className="rounded-full border border-red-200 bg-red-50 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-red-700 transition hover:bg-red-100"
            >
              {copy.queryHistory.clearAll}
            </button>
          ) : null}
        </div>
      </div>

      {cacheMessage ? (
        <div className="mb-4 rounded-[20px] border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-600">
          {cacheMessage}
        </div>
      ) : null}

      {history.length === 0 ? (
        <div className="rounded-[24px] border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-sm leading-6 text-slate-500">
          {copy.queryHistory.empty}
        </div>
      ) : (
        <div className="max-h-[440px] space-y-3 overflow-auto pr-1">
          {history.map((entry) => {
            const isActive = entry.id === activeHistoryId;

            return (
              <div
                key={entry.id}
                className={`rounded-[24px] border px-4 py-4 transition ${
                  isActive
                    ? "border-brand/40 bg-brand-soft/70 shadow-focus"
                    : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                <button
                  type="button"
                  onClick={() => onRestore(entry.id)}
                  className="w-full text-left"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-medium leading-6 text-slate-900">
                      {entry.query}
                    </p>
                    <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-slate-500">
                      {formatTime(entry.createdAt, locale)}
                    </span>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-slate-600">
                      {translateHistoryStatus(entry.status, locale)}
                    </span>
                    {entry.mode ? (
                      <span className="rounded-full bg-brand-soft px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-brand">
                        {translateAnswerMode(entry.mode, locale)}
                      </span>
                    ) : null}
                    {typeof entry.cacheHit === "boolean" ? (
                      <span className="rounded-full bg-amber-50 px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-amber-700">
                        {copy.queryHistory.cacheLabel(entry.cacheHit)}
                      </span>
                    ) : null}
                  </div>
                </button>

                <div className="mt-4 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => onRestore(entry.id)}
                    className="rounded-full border border-slate-200 bg-white px-3 py-2 font-mono text-[11px] uppercase tracking-[0.16em] text-slate-700 transition hover:bg-slate-100"
                  >
                    {copy.queryHistory.open}
                  </button>
                  <button
                    type="button"
                    onClick={() => onRunAgain(entry.id)}
                    className="rounded-full border border-brand/20 bg-brand-soft px-3 py-2 font-mono text-[11px] uppercase tracking-[0.16em] text-brand transition hover:bg-brand-soft/80"
                  >
                    {copy.queryHistory.runAgain}
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(entry.id)}
                    className="rounded-full border border-red-200 bg-red-50 px-3 py-2 font-mono text-[11px] uppercase tracking-[0.16em] text-red-700 transition hover:bg-red-100"
                  >
                    {copy.queryHistory.delete}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
