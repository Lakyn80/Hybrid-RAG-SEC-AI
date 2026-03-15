"use client";

import { StatusPill } from "@/components/StatusPill";
import { useUiLocale } from "@/components/UiLocaleProvider";
import { translateAnswerMode, translateCacheState, translateStreamStatus } from "@/lib/i18n";
import { getStoredPresetAnswerByQuery } from "@/lib/presetAnswerBank";
import { AskResponse, StreamConnectionStatus } from "@/lib/types";

interface AnswerResultProps {
  answer: AskResponse | null;
  isLoading: boolean;
  error: string | null;
  streamStatus: StreamConnectionStatus;
}

function parseSourceLines(sources: string) {
  return sources
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !/^(Sources|Zdroje|Источники):$/i.test(line));
}

function createSourceBadge(sourceLine: string, locale: "en" | "cs" | "ru") {
  if (/preset|lokalni scenar|llm/i.test(sourceLine)) {
    return "[Preset]";
  }

  const formMatch = sourceLine.match(/\b(10-K|10-Q|8-K|DEF\s*14A|DEFA14A|SC\s*13G(?:\/A)?|SC\s*13G\/A)\b/i);
  const pageMatch = sourceLine.match(/\b(?:page|p\.|str\.?)\s*(\d+)\b/i);
  const form = formMatch ? formMatch[1].replace(/\s+/g, " ").toUpperCase() : locale === "ru" ? "Документ" : locale === "cs" ? "Filing" : "Filing";
  const pagePrefix = locale === "ru" ? "стр." : locale === "en" ? "p." : "str.";
  const page = pageMatch ? `, ${pagePrefix} ${pageMatch[1]}` : "";

  return `[SEC ${form}${page}]`;
}

function renderAnswerBlocks(answerText: string) {
  const lines = answerText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  const bulletLines = lines.filter((line) => line.startsWith("*") || line.startsWith("-"));

  if (bulletLines.length > 0) {
    return (
      <ul className="space-y-3 text-sm leading-7 text-slate-200">
        {bulletLines.map((line, index) => (
          <li key={`${line}-${index}`} className="flex gap-3">
            <span className="mt-[10px] h-2 w-2 shrink-0 rounded-full bg-[#f5d15a]" />
            <span>{line.replace(/^[-*]\s*/, "")}</span>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div className="space-y-3 text-sm leading-7 text-slate-200">
      {lines.map((line, index) => (
        <p key={`${line}-${index}`}>{line}</p>
      ))}
    </div>
  );
}

export function AnswerResult({
  answer,
  isLoading,
  error,
  streamStatus,
}: AnswerResultProps) {
  const { copy, locale } = useUiLocale();
  const localizedPresetAnswer =
    answer && answer.mode === "preset"
      ? getStoredPresetAnswerByQuery(answer.query, locale)
      : null;
  const displayedAnswer = localizedPresetAnswer
    ? { ...answer, ...localizedPresetAnswer }
    : answer;
  const sources = displayedAnswer ? parseSourceLines(displayedAnswer.sources) : [];

  return (
    <section className="panel p-5 sm:p-6">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500">{copy.answerResult.eyebrow}</p>
          <h2 className="text-metallic-gold mt-2 text-2xl font-semibold tracking-tight">{copy.answerResult.title}</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          {displayedAnswer?.mode ? <StatusPill label={translateAnswerMode(displayedAnswer.mode, locale)} variant="info" /> : null}
          {displayedAnswer?.mode !== "preset" && typeof displayedAnswer?.cache_hit === "boolean" ? (
            <StatusPill label={translateCacheState(displayedAnswer.cache_hit, locale)} variant={displayedAnswer.cache_hit ? "success" : "warning"} />
          ) : null}
          <StatusPill label={`${copy.common.streamLabel} ${translateStreamStatus(streamStatus, locale)}`} variant={streamStatus === "fallback" ? "warning" : "neutral"} />
        </div>
      </div>

      {error ? (
        <div className="border border-red-500/40 bg-red-500/10 px-5 py-4 text-sm leading-7 text-red-100">
          {error}
        </div>
      ) : null}

      {!error && !answer && !isLoading ? (
        <div className="border border-dashed border-line bg-[#0d0d0d] px-5 py-10 text-sm leading-7 text-slate-400">
          {copy.answerResult.waiting}
        </div>
      ) : null}

      {!error && !answer && isLoading ? (
        <div className="border border-line bg-[#0d0d0d] px-5 py-10">
          <div className="space-y-4">
            <div className="h-4 w-2/5 animate-pulse rounded-[2px] bg-slate-700" />
            <div className="h-4 w-full animate-pulse rounded-[2px] bg-slate-700" />
            <div className="h-4 w-[88%] animate-pulse rounded-[2px] bg-slate-700" />
            <div className="h-4 w-[72%] animate-pulse rounded-[2px] bg-slate-700" />
          </div>
        </div>
      ) : null}

      {displayedAnswer ? (
        <div className="space-y-5">
          <div className="border border-line bg-[#0d0d0d] px-5 py-5">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-slate-500">{copy.answerResult.query}</p>
            <p className="mt-2 text-sm leading-7 text-slate-200">{displayedAnswer.query}</p>
          </div>

          <div className="border border-line bg-[#0d0d0d] px-5 py-5">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-slate-500">{copy.answerResult.answer}</p>
            <div className="mt-3">{renderAnswerBlocks(displayedAnswer.answer)}</div>
            <div className="mt-4 border border-line bg-black/30 px-4 py-3 text-sm text-slate-400">
              <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-slate-500">{copy.answerResult.llmRunInfo}</p>
              <p className="mt-2 break-all">
                <span className="font-medium text-slate-200">{copy.answerResult.runId}:</span>{" "}
                {displayedAnswer.run_id ?? copy.common.notAvailable}
              </p>
              <p className="mt-1">
                <span className="font-medium text-slate-200">{copy.answerResult.source}:</span>{" "}
                {displayedAnswer.cache_hit ? copy.answerResult.cache : copy.answerResult.pipeline}
              </p>
            </div>
          </div>

          <div className="border border-line bg-[#0d0d0d] px-5 py-5">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-slate-500">{copy.answerResult.sources}</p>
            {sources.length === 0 ? (
              <p className="mt-3 text-sm leading-7 text-slate-400">{copy.answerResult.noSources}</p>
            ) : (
              <ul className="mt-3 space-y-3">
                {sources.map((sourceLine, index) => (
                  <li key={`${sourceLine}-${index}`} className="border border-line bg-black/30 px-4 py-3 text-sm leading-6 text-slate-200">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <span className="inline-flex w-fit rounded-[2px] border border-slate-300/30 bg-[linear-gradient(90deg,rgba(255,248,204,0.2),rgba(214,158,36,0.16))] px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-[#f7e3a0]">
                        {createSourceBadge(sourceLine, locale)}
                      </span>
                      <span className="text-sm leading-6 text-slate-300">{sourceLine}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : null}
    </section>
  );
}
