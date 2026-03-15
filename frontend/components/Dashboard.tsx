"use client";

import { useEffect, useState } from "react";

import { AnswerResult } from "@/components/AnswerResult";
import { ExecutionLog } from "@/components/ExecutionLog";
import { PipelineVisualizer } from "@/components/PipelineVisualizer";
import { PromptPanel } from "@/components/PromptPanel";
import { QueryHistory } from "@/components/QueryHistory";
import { SuggestedQuestions } from "@/components/SuggestedQuestions";
import { useUiLocale } from "@/components/UiLocaleProvider";
import { useAskPipeline } from "@/hooks/useAskPipeline";
import { clearSystemCache } from "@/lib/api";

export function Dashboard() {
  const { copy, locale } = useUiLocale();
  const [query, setQuery] = useState(copy.dashboard.defaultQuery);
  const [cacheMessage, setCacheMessage] = useState<string | null>(null);
  const [isDeletingCache, setIsDeletingCache] = useState(false);
  const {
    activeHistoryId,
    clearHistory,
    deleteHistoryEntry,
    history,
    restoreHistoryEntry,
    rerunHistoryEntry,
    run,
    submitQuery,
  } = useAskPipeline();

  useEffect(() => {
    if (!history.length && !run.query) {
      setQuery(copy.dashboard.defaultQuery);
    }
  }, [copy.dashboard.defaultQuery, history.length, run.query, locale]);

  const handleSubmit = async (value?: string) => {
    const nextQuery = (value ?? query).trim();
    if (!nextQuery) {
      return;
    }

    setQuery(nextQuery);
    await submitQuery(nextQuery);
  };

  const handleDeleteCache = async () => {
    setIsDeletingCache(true);
    setCacheMessage(null);

    try {
      const result = await clearSystemCache();
      setCacheMessage(
        copy.dashboard.cacheClearedMessage(
          result.redis_keys_deleted,
          result.answer_cache_cleared,
        ),
      );
    } catch (error) {
      setCacheMessage(
        error instanceof Error ? error.message : copy.dashboard.cacheClearError,
      );
    } finally {
      setIsDeletingCache(false);
    }
  };

  return (
    <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-[1760px] flex-col px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
      <header className="mb-6 grid gap-5 xl:grid-cols-[minmax(0,1.5fr)_420px]">
        <div className="panel panel-accent p-6 sm:p-7">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <p className="inline-flex rounded-[2px] border border-line bg-white/5 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.3em] text-slate-300">
              DocBrain
            </p>
            <p className="inline-flex rounded-[2px] border border-line bg-white/5 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.24em] text-slate-400">
              Obsidian &amp; Chrome
            </p>
          </div>
          <h1 className="text-metallic-gold max-w-4xl text-balance text-3xl font-semibold tracking-tight sm:text-[2.6rem]">
            {copy.dashboard.heroTitle}
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-400">
            Auditní rozhraní pro investory, compliance a právní due diligence. Sledujte celý tok od retrieval až po finální zdrojově podložený závěr.
          </p>
        </div>

        <div className="panel p-6">
          <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-slate-400">
            {copy.dashboard.runtimeProfileLabel}
          </p>
          <p className="mt-3 text-sm leading-7 text-slate-300">
            {copy.dashboard.runtimeProfileText}
          </p>
          <div className="mt-5 grid gap-px border border-line bg-line sm:grid-cols-3">
            <div className="bg-paper px-4 py-3">
              <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-500">Retrieval</p>
              <p className="mt-2 text-sm text-slate-200">Qdrant + BM25</p>
            </div>
            <div className="bg-paper px-4 py-3">
              <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-500">Zdroj</p>
              <p className="mt-2 text-sm text-slate-200">SEC filings</p>
            </div>
            <div className="bg-paper px-4 py-3">
              <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-500">Výstup</p>
              <p className="mt-2 text-sm text-slate-200">Ověřené poznatky</p>
            </div>
          </div>
        </div>
      </header>

      <section className="grid flex-1 gap-5 xl:grid-cols-[420px_minmax(0,1fr)]">
        <div className="flex min-h-[720px] flex-col gap-5">
          <PromptPanel
            query={query}
            isLoading={run.isLoading}
            onQueryChange={setQuery}
            onQuickSelect={(selectedQuery) => {
              setQuery(selectedQuery);
            }}
            onSubmit={() => {
              void handleSubmit();
            }}
          />
          <SuggestedQuestions
            onSelect={(selectedQuery) => {
              setQuery(selectedQuery);
            }}
          />
          <QueryHistory
            activeHistoryId={activeHistoryId}
            cacheMessage={cacheMessage}
            history={history}
            isDeletingCache={isDeletingCache}
            onClearAll={() => {
              clearHistory();
            }}
            onDeleteCache={() => {
              void handleDeleteCache();
            }}
            onDelete={(entryId) => {
              deleteHistoryEntry(entryId);
            }}
            onRestore={(entryId) => {
              const restoredEntry = restoreHistoryEntry(entryId);
              if (restoredEntry) {
                setQuery(restoredEntry.query);
              }
            }}
            onRunAgain={(entryId) => {
              const entry = history.find((item) => item.id === entryId);
              if (entry) {
                setQuery(entry.query);
              }

              void rerunHistoryEntry(entryId);
            }}
          />
        </div>

        <div className="grid min-h-[720px] gap-5 lg:grid-rows-[auto_minmax(0,1fr)_auto]">
          <PipelineVisualizer
            isLoading={run.isLoading}
            status={run.streamStatus}
            steps={run.steps}
          />
          <ExecutionLog
            isLoading={run.isLoading}
            logs={run.logs}
            status={run.streamStatus}
          />
          <AnswerResult
            answer={run.answer}
            error={run.error}
            isLoading={run.isLoading}
            streamStatus={run.streamStatus}
          />
        </div>
      </section>
    </div>
  );
}
