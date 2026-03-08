"use client";

import { getPromptGuardState } from "@/lib/promptGuard";

interface PromptPanelProps {
  query: string;
  isLoading: boolean;
  onQueryChange: (query: string) => void;
  onSubmit: () => void;
}

export function PromptPanel({
  query,
  isLoading,
  onQueryChange,
  onSubmit,
}: PromptPanelProps) {
  const promptGuard = getPromptGuardState(query);

  return (
    <section className="panel panel-accent rounded-[32px] p-5 sm:p-6">
      <div className="mb-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500">Prompt panel</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">Run a live filing query</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Send a prompt to the production RAG backend and watch each pipeline stage update in real time.
        </p>
      </div>

      <label className="mb-3 block font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500" htmlFor="query">
        Query
      </label>

      <div className="mb-4 rounded-[24px] border border-slate-200 bg-slate-50 px-4 py-4">
        <p className="text-sm font-medium text-slate-900">
          Ask questions about SEC filings and financial reports.
        </p>
        <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
          <li>What legal risks did Apple mention in its 10-K filings?</li>
          <li>Summarize risk factors in Tesla&apos;s annual report.</li>
          <li>What litigation risks appear in the filings?</li>
        </ul>
      </div>

      <textarea
        id="query"
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
        onKeyDown={(event) => {
          if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
            event.preventDefault();
            onSubmit();
          }
        }}
        placeholder="What legal risks did Apple mention in its 10-K filings?"
        className="h-44 w-full resize-none rounded-[26px] border border-slate-200 bg-white px-4 py-4 text-[15px] leading-7 text-slate-900 outline-none transition focus:border-brand focus:shadow-focus"
      />

      {promptGuard.showWarning ? (
        <div className="mt-4 rounded-[22px] border border-amber-200 bg-amber-50 px-4 py-4 text-sm leading-6 text-amber-800">
          <p className="font-medium text-amber-900">
            This system is designed to analyze SEC filings and financial documents.
          </p>
          <p className="mt-1">
            Please ask questions related to company filings or financial reports.
          </p>
        </div>
      ) : null}

      <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-slate-500">Transport</p>
          <p className="mt-1 text-sm text-slate-700">
            <span className="font-medium text-slate-950">SSE</span> for live execution + <span className="font-medium text-slate-950">POST</span> for the final answer.
          </p>
        </div>

        <button
          type="button"
          onClick={onSubmit}
          disabled={isLoading || !query.trim()}
          className="inline-flex min-w-[156px] items-center justify-center rounded-full bg-slate-950 px-6 py-3 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {isLoading ? "Running..." : "Ask pipeline"}
        </button>
      </div>
    </section>
  );
}
