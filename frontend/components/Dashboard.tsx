"use client";

import { useState } from "react";

import { AnswerResult } from "@/components/AnswerResult";
import { ExecutionLog } from "@/components/ExecutionLog";
import { PipelineVisualizer } from "@/components/PipelineVisualizer";
import { PromptPanel } from "@/components/PromptPanel";
import { QueryHistory } from "@/components/QueryHistory";
import { SuggestedQuestions } from "@/components/SuggestedQuestions";
import { useAskPipeline } from "@/hooks/useAskPipeline";
import { clearSystemCache } from "@/lib/api";
import { copy } from "@/lib/i18n";

const DEFAULT_QUERY = copy.dashboard.defaultQuery;

export function Dashboard() {
  const [query, setQuery] = useState(DEFAULT_QUERY);
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
    <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-[1680px] flex-col px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
      <header className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-4xl">
          <p className="mb-2 inline-flex rounded-full border border-brand/20 bg-brand-soft px-3 py-1 font-mono text-[11px] uppercase tracking-[0.26em] text-brand">
            Hybrid RAG SEC AI
          </p>
          <h1 className="text-balance text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            {copy.dashboard.heroTitle}
          </h1>
        </div>
        <div className="max-w-xl rounded-3xl border border-slate-200/80 bg-white/85 px-5 py-4 shadow-panel">
          <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500">
            {copy.dashboard.runtimeProfileLabel}
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {copy.dashboard.runtimeProfileText}
          </p>
        </div>
      </header>

      <section className="grid flex-1 gap-6 xl:grid-cols-[390px_minmax(0,1fr)]">
        <div className="flex min-h-[720px] flex-col gap-6">
          <PromptPanel
            query={query}
            isLoading={run.isLoading}
            onQueryChange={setQuery}
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

        <div className="grid min-h-[720px] gap-6 lg:grid-rows-[auto_minmax(0,1fr)_auto]">
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
