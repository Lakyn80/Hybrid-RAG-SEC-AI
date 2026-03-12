"use client";

import { getPromptGuardState } from "@/lib/promptGuard";
import { copy } from "@/lib/i18n";

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
        <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500">{copy.promptPanel.eyebrow}</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{copy.promptPanel.title}</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          {copy.promptPanel.description}
        </p>
      </div>

      <label className="mb-3 block font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500" htmlFor="query">
        {copy.promptPanel.queryLabel}
      </label>

      <div className="mb-4 rounded-[24px] border border-slate-200 bg-slate-50 px-4 py-4">
        <p className="text-sm font-medium text-slate-900">
          {copy.promptPanel.helperTitle}
        </p>
        <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
          {copy.promptPanel.helperExamples.map((example) => (
            <li key={example}>{example}</li>
          ))}
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
        placeholder={copy.promptPanel.placeholder}
        className="h-44 w-full resize-none rounded-[26px] border border-slate-200 bg-white px-4 py-4 text-[15px] leading-7 text-slate-900 outline-none transition focus:border-brand focus:shadow-focus"
      />

      {promptGuard.showWarning ? (
        <div className="mt-4 rounded-[22px] border border-amber-200 bg-amber-50 px-4 py-4 text-sm leading-6 text-amber-800">
          <p className="font-medium text-amber-900">
            {copy.promptPanel.warningTitle}
          </p>
          <p className="mt-1">
            {copy.promptPanel.warningText}
          </p>
        </div>
      ) : null}

      <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-slate-500">{copy.promptPanel.transportLabel}</p>
          <p className="mt-1 text-sm text-slate-700">
            {copy.promptPanel.transportText}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="inline-flex min-w-[120px] items-center justify-center rounded-full border border-slate-300 bg-white px-5 py-3 text-sm font-medium text-slate-800 transition hover:border-slate-400 hover:bg-slate-50"
          >
            {copy.promptPanel.refresh}
          </button>

          <button
            type="button"
            onClick={onSubmit}
            disabled={isLoading || !query.trim()}
            className="inline-flex min-w-[156px] items-center justify-center rounded-full bg-slate-950 px-6 py-3 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {isLoading ? copy.promptPanel.running : copy.promptPanel.askPipeline}
          </button>
        </div>
      </div>
    </section>
  );
}
