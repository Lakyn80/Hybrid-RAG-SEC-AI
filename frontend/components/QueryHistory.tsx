"use client";

import { useUiLocale } from "@/components/UiLocaleProvider";
import { translateAnswerMode, translateHistoryStatus } from "@/lib/i18n";
import { getStoredPresetAnswerByQuery } from "@/lib/presetAnswerBank";
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
  const savedReports = history.filter((entry) => entry.status === "success").slice(0, 4);
  const analysisHistoryLabel =
    locale === "ru" ? "История анализа" : locale === "en" ? "Analysis history" : "Historie analýz";
  const savedReportsLabel =
    locale === "ru" ? "Сохраненные отчеты" : locale === "en" ? "Saved reports" : "Uložené reporty";
  const savedReportsEmpty =
    locale === "ru"
      ? "После успешного аудита здесь появятся последние проверенные отчеты."
      : locale === "en"
        ? "The latest verified reports will appear here after a successful audit."
        : "Po úspěšném auditu se zde zobrazí poslední ověřené reporty.";
  const openReportLabel =
    locale === "ru" ? "Открыть отчет" : locale === "en" ? "Open report" : "Otevřít report";

  return (
    <section className="panel p-5 sm:p-6">
      <div className="mb-5 flex items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500">
            {copy.queryHistory.eyebrow}
          </p>
          <h2 className="text-metallic-gold mt-2 text-xl font-semibold tracking-tight">
            {copy.queryHistory.title}
          </h2>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="rounded-[2px] border border-line bg-white/5 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-slate-400">
            {copy.queryHistory.stored(history.length)}
          </div>
          <button
            type="button"
            onClick={onDeleteCache}
            disabled={isDeletingCache}
            className="rounded-[2px] border border-amber-500/40 bg-amber-500/10 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-amber-200 transition hover:bg-amber-500/15 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isDeletingCache ? copy.queryHistory.deletingCache : copy.queryHistory.deleteCache}
          </button>
          {history.length > 0 ? (
            <button
              type="button"
              onClick={onClearAll}
              className="rounded-[2px] border border-red-500/40 bg-red-500/10 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-red-200 transition hover:bg-red-500/15"
            >
              {copy.queryHistory.clearAll}
            </button>
          ) : null}
        </div>
      </div>

      {cacheMessage ? (
        <div className="mb-4 rounded-[2px] border border-line bg-[#0d0d0d] px-4 py-3 text-sm leading-6 text-slate-300">
          {cacheMessage}
        </div>
      ) : null}

      {history.length === 0 ? (
        <div className="rounded-[2px] border border-dashed border-line bg-[#0d0d0d] px-4 py-8 text-sm leading-6 text-slate-400">
          {copy.queryHistory.empty}
        </div>
      ) : (
        <div className="space-y-5">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-slate-500">
              {analysisHistoryLabel}
            </p>
            <div className="mt-3 max-h-[280px] space-y-3 overflow-auto pr-1">
              {history.map((entry) => {
                const isActive = entry.id === activeHistoryId;
                const localizedPreset = getStoredPresetAnswerByQuery(entry.query, locale);
                const displayedQuery = localizedPreset?.query ?? entry.query;

                return (
                  <div
                    key={entry.id}
                    className={`border px-4 py-4 transition ${
                      isActive
                        ? "border-[#f5d15a]/60 bg-[linear-gradient(180deg,rgba(250,220,120,0.12),rgba(18,18,18,0.98))] shadow-focus"
                        : "border-line bg-[#0d0d0d] hover:bg-white/5"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => onRestore(entry.id)}
                      className="w-full text-left"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-sm font-medium leading-6 text-slate-100">
                          {displayedQuery}
                        </p>
                        <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-slate-500">
                          {formatTime(entry.createdAt, locale)}
                        </span>
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2">
                        <span className="rounded-[2px] border border-line bg-white/5 px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-slate-400">
                          {translateHistoryStatus(entry.status, locale)}
                        </span>
                        {entry.mode ? (
                          <span className="rounded-[2px] border border-[#f5d15a]/40 bg-[#f5d15a]/10 px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-[#f6db7d]">
                            {translateAnswerMode(entry.mode, locale)}
                          </span>
                        ) : null}
                        {typeof entry.cacheHit === "boolean" ? (
                          <span className="rounded-[2px] border border-line bg-white/5 px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-slate-400">
                            {copy.queryHistory.cacheLabel(entry.cacheHit)}
                          </span>
                        ) : null}
                      </div>
                    </button>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => onRestore(entry.id)}
                        className="rounded-[2px] border border-line bg-white/5 px-3 py-2 font-mono text-[11px] uppercase tracking-[0.16em] text-slate-200 transition hover:bg-white/10"
                      >
                        {copy.queryHistory.open}
                      </button>
                      <button
                        type="button"
                        onClick={() => onRunAgain(entry.id)}
                        className="rounded-[2px] border border-[#f5d15a]/40 bg-[#f5d15a]/10 px-3 py-2 font-mono text-[11px] uppercase tracking-[0.16em] text-[#f6db7d] transition hover:bg-[#f5d15a]/15"
                      >
                        {copy.queryHistory.runAgain}
                      </button>
                      <button
                        type="button"
                        onClick={() => onDelete(entry.id)}
                        className="rounded-[2px] border border-red-500/40 bg-red-500/10 px-3 py-2 font-mono text-[11px] uppercase tracking-[0.16em] text-red-200 transition hover:bg-red-500/15"
                      >
                        {copy.queryHistory.delete}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-slate-500">
              {savedReportsLabel}
            </p>
            {savedReports.length === 0 ? (
              <div className="mt-3 border border-dashed border-line bg-[#0d0d0d] px-4 py-5 text-sm leading-6 text-slate-400">
                {savedReportsEmpty}
              </div>
            ) : (
              <div className="mt-3 grid gap-px border border-line bg-line">
                {savedReports.map((entry) => {
                  const localizedPreset = getStoredPresetAnswerByQuery(entry.query, locale);
                  const displayedQuery = localizedPreset?.query ?? entry.query;

                  return (
                    <button
                      key={`report-${entry.id}`}
                      type="button"
                      onClick={() => onRestore(entry.id)}
                      className="bg-paper px-4 py-4 text-left transition hover:bg-white/5"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-sm font-medium leading-6 text-slate-100">
                          {displayedQuery}
                        </p>
                        <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-slate-500">
                          {formatTime(entry.createdAt, locale)}
                        </span>
                      </div>
                      <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.18em] text-[#f6db7d]">
                        {openReportLabel}
                      </p>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
