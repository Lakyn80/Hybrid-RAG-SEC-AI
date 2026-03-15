"use client";

import { useUiLocale } from "@/components/UiLocaleProvider";
import { getQuickAuditPresets } from "@/lib/presetCatalog";
import { getPromptGuardState } from "@/lib/promptGuard";

interface PromptPanelProps {
  query: string;
  isLoading: boolean;
  onQueryChange: (query: string) => void;
  onQuickSelect: (query: string) => void;
  onSubmit: () => void;
}

export function PromptPanel({
  query,
  isLoading,
  onQueryChange,
  onQuickSelect,
  onSubmit,
}: PromptPanelProps) {
  const { copy, locale } = useUiLocale();
  const promptGuard = getPromptGuardState(query);
  const quickAuditPresets = getQuickAuditPresets(locale);
  const auditLabel = locale === "ru" ? "Аудит" : "Audit";
  const presetHint =
    locale === "ru"
      ? "Эти 4 карточки используют локальные preset-ответы. Backend и LLM не вызываются."
      : locale === "en"
        ? "These 4 cards use local preset answers. The backend and LLM stay disabled."
        : "Tyto 4 karty pouzivaji lokalni preset odpovedi. Backend a LLM se nespousti.";

  return (
    <section className="panel panel-accent p-5 sm:p-6">
      <div className="mb-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500">{copy.promptPanel.eyebrow}</p>
        <h2 className="text-metallic-gold mt-2 text-2xl font-semibold tracking-tight">{copy.promptPanel.title}</h2>
        <p className="mt-2 text-sm leading-7 text-slate-400">
          {copy.promptPanel.description}
        </p>
      </div>

      <div className="mb-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-slate-500">
          {copy.promptPanel.helperTitle}
        </p>
        <div className="mt-3 grid gap-px border border-line bg-line sm:grid-cols-2">
          {quickAuditPresets.map((card) => {
            const isActive = query.trim() === card.query;

            return (
              <button
                key={card.title}
                type="button"
                onClick={() => onQuickSelect(card.query)}
                className={`bg-paper px-4 py-4 text-left transition ${
                  isActive
                    ? "bg-[linear-gradient(180deg,rgba(250,220,120,0.14),rgba(18,18,18,0.96))]"
                    : "hover:bg-white/5"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="text-lg">{card.icon}</span>
                  <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-500">
                    {auditLabel}
                  </span>
                </div>
                <p className="text-metallic-gold mt-6 text-base font-semibold">{card.title}</p>
                <p className="mt-2 text-sm leading-6 text-slate-400">{card.description}</p>
              </button>
            );
          })}
        </div>
        <p className="mt-3 text-xs leading-6 text-slate-500">
          {presetHint}
        </p>
      </div>

      <label className="mb-3 block font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500" htmlFor="query">
        {copy.promptPanel.queryLabel}
      </label>

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
        className="h-44 w-full resize-none rounded-[2px] border border-line bg-[#0f0f0f] px-4 py-4 text-[15px] leading-7 text-slate-100 outline-none transition focus:border-brand focus:shadow-focus"
      />

      {promptGuard.showWarning ? (
        <div className="mt-4 rounded-[2px] border border-amber-500/40 bg-amber-500/10 px-4 py-4 text-sm leading-6 text-amber-100">
          <p className="font-medium text-amber-200">
            {copy.promptPanel.warningTitle}
          </p>
          <p className="mt-1">
            {copy.promptPanel.warningText}
          </p>
        </div>
      ) : null}

      <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
        <div className="rounded-[2px] border border-line bg-[#0d0d0d] px-4 py-3">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-slate-500">{copy.promptPanel.transportLabel}</p>
          <p className="mt-1 text-sm text-slate-300">
            {copy.promptPanel.transportText}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="inline-flex min-w-[128px] items-center justify-center rounded-[2px] border border-line bg-[#0d0d0d] px-5 py-3 text-sm font-medium text-slate-200 transition hover:bg-white/5"
          >
            {copy.promptPanel.refresh}
          </button>

          <button
            type="button"
            onClick={onSubmit}
            disabled={isLoading || !query.trim()}
            className="inline-flex min-w-[168px] items-center justify-center rounded-[2px] bg-[linear-gradient(90deg,#fff8cc_0%,#f5d15a_28%,#c9971d_56%,#fff2a0_100%)] px-6 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? copy.promptPanel.running : copy.promptPanel.askPipeline}
          </button>
        </div>
      </div>
    </section>
  );
}
