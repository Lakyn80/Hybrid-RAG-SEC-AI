"use client";

import { useState } from "react";

import { AnswerResult } from "@/components/AnswerResult";
import { ExecutionLog } from "@/components/ExecutionLog";
import { PipelineVisualizer } from "@/components/PipelineVisualizer";
import { PromptPanel } from "@/components/PromptPanel";
import { QueryHistory } from "@/components/QueryHistory";
import { RagPipelineGraph } from "@/components/RagPipelineGraph";
import { useAskPipeline } from "@/hooks/useAskPipeline";

const DEFAULT_QUERY = "What legal risks did Apple mention in its 10-K filings?";

export function Dashboard() {
  const [query, setQuery] = useState(DEFAULT_QUERY);
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

  return (
    <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-[1680px] flex-col px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
      <header className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-4xl">
          <p className="mb-2 inline-flex rounded-full border border-brand/20 bg-brand-soft px-3 py-1 font-mono text-[11px] uppercase tracking-[0.26em] text-brand">
            Hybrid RAG SEC AI
          </p>
          <h1 className="text-balance text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            Live pipeline control room for AI-powered SEC filing retrieval and answer generation.
          </h1>
        </div>
        <div className="max-w-xl rounded-3xl border border-slate-200/80 bg-white/85 px-5 py-4 shadow-panel">
          <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500">
            Runtime profile
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Two-panel dashboard for demos, debugging, and technical presentations. The UI listens to live
            pipeline events and renders the final grounded answer from the production backend.
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
          <QueryHistory
            activeHistoryId={activeHistoryId}
            history={history}
            onClearAll={() => {
              clearHistory();
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
          <RagPipelineGraph
            isLoading={run.isLoading}
            logs={run.logs}
            observedStreamEvents={run.observedStreamEvents}
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
