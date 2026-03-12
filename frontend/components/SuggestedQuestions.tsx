"use client";

import { useEffect, useState } from "react";

import { useUiLocale } from "@/components/UiLocaleProvider";
import { getQuestionBank } from "@/lib/api";

interface SuggestedQuestionsProps {
  onSelect: (query: string) => void;
}

export function SuggestedQuestions({ onSelect }: SuggestedQuestionsProps) {
  const { copy } = useUiLocale();
  const [questions, setQuestions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadQuestions = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await getQuestionBank();
      setQuestions(response.questions);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : copy.suggestedQuestions.loadError,
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadQuestions();
  }, []);

  return (
    <section className="panel rounded-[32px] p-5 sm:p-6">
      <div className="mb-5 flex items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500">
            {copy.suggestedQuestions.eyebrow}
          </p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight text-slate-950">
            {copy.suggestedQuestions.title}
          </h2>
        </div>

        <button
          type="button"
          onClick={() => {
            void loadQuestions();
          }}
          disabled={isLoading}
          className="rounded-full border border-slate-200 bg-white px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading ? copy.suggestedQuestions.loading : copy.suggestedQuestions.refresh}
        </button>
      </div>

      {error ? (
        <div className="rounded-[20px] border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-700">
          {error}
        </div>
      ) : null}

      {!error && questions.length === 0 && !isLoading ? (
        <div className="rounded-[20px] border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm leading-6 text-slate-500">
          {copy.suggestedQuestions.empty}
        </div>
      ) : null}

      <div className="max-h-[320px] space-y-3 overflow-auto pr-1">
        {questions.map((question) => (
          <button
            key={question}
            type="button"
            onClick={() => onSelect(question)}
            className="w-full rounded-[22px] border border-slate-200 bg-white px-4 py-3 text-left text-sm leading-6 text-slate-700 transition hover:border-brand/30 hover:bg-brand-soft/40"
          >
            {question}
          </button>
        ))}
      </div>
    </section>
  );
}
