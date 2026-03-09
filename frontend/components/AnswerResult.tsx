"use client";

import { StatusPill } from "@/components/StatusPill";
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
    .filter((line) => line && line !== "Sources:");
}

function renderAnswerBlocks(answerText: string) {
  const lines = answerText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  const bulletLines = lines.filter((line) => line.startsWith("*") || line.startsWith("-"));

  if (bulletLines.length > 0) {
    return (
      <ul className="space-y-3 text-sm leading-7 text-slate-700">
        {bulletLines.map((line, index) => (
          <li key={`${line}-${index}`} className="flex gap-3">
            <span className="mt-[10px] h-2 w-2 shrink-0 rounded-full bg-brand" />
            <span>{line.replace(/^[-*]\s*/, "")}</span>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <div className="space-y-3 text-sm leading-7 text-slate-700">
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
  const sources = answer ? parseSourceLines(answer.sources) : [];

  return (
    <section className="panel rounded-[32px] p-5 sm:p-6">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500">Final answer</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">Grounded response</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          {answer?.mode ? <StatusPill label={answer.mode} variant="info" /> : null}
          {typeof answer?.cache_hit === "boolean" ? (
            <StatusPill label={answer.cache_hit ? "cache hit" : "cache miss"} variant={answer.cache_hit ? "success" : "warning"} />
          ) : null}
          <StatusPill label={`stream ${streamStatus}`} variant={streamStatus === "fallback" ? "warning" : "neutral"} />
        </div>
      </div>

      {error ? (
        <div className="rounded-[24px] border border-red-200 bg-red-50 px-5 py-4 text-sm leading-7 text-red-700">
          {error}
        </div>
      ) : null}

      {!error && !answer && !isLoading ? (
        <div className="rounded-[24px] border border-dashed border-slate-200 bg-slate-50 px-5 py-10 text-sm leading-7 text-slate-500">
          The final answer will appear here once the backend completes the run.
        </div>
      ) : null}

      {!error && !answer && isLoading ? (
        <div className="rounded-[24px] border border-slate-200 bg-slate-50 px-5 py-10">
          <div className="space-y-4">
            <div className="h-4 w-2/5 animate-pulse rounded-full bg-slate-200" />
            <div className="h-4 w-full animate-pulse rounded-full bg-slate-200" />
            <div className="h-4 w-[88%] animate-pulse rounded-full bg-slate-200" />
            <div className="h-4 w-[72%] animate-pulse rounded-full bg-slate-200" />
          </div>
        </div>
      ) : null}

      {answer ? (
        <div className="space-y-5">
          <div className="rounded-[26px] border border-slate-200 bg-white px-5 py-5">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-slate-500">Query</p>
            <p className="mt-2 text-sm leading-7 text-slate-700">{answer.query}</p>
          </div>

          <div className="rounded-[26px] border border-slate-200 bg-white px-5 py-5">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-slate-500">Answer</p>
            <div className="mt-3">{renderAnswerBlocks(answer.answer)}</div>
            <div className="mt-4 rounded-[20px] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">
              <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-slate-500">LLM Run Info</p>
              <p className="mt-2 break-all">
                <span className="font-medium text-slate-700">run_id:</span>{" "}
                {answer.run_id ?? "n/a"}
              </p>
              <p className="mt-1">
                <span className="font-medium text-slate-700">source:</span>{" "}
                {answer.cache_hit ? "cache" : "pipeline"}
              </p>
            </div>
          </div>

          <div className="rounded-[26px] border border-slate-200 bg-white px-5 py-5">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-slate-500">Sources</p>
            {sources.length === 0 ? (
              <p className="mt-3 text-sm leading-7 text-slate-500">No sources returned.</p>
            ) : (
              <ul className="mt-3 space-y-3">
                {sources.map((sourceLine, index) => (
                  <li key={`${sourceLine}-${index}`} className="rounded-[20px] border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-700">
                    {sourceLine}
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
