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

  useEffect(() => {
    let isMounted = true;

    const loadQuestions = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await getQuestionBank();
        if (!isMounted) {
          return;
        }

        setQuestions(response.questions.slice(0, 20));
      } catch (loadError) {
        if (!isMounted) {
          return;
        }

        setError(
          loadError instanceof Error
            ? loadError.message
            : copy.suggestedQuestions.loadError,
        );
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void loadQuestions();

    return () => {
      isMounted = false;
    };
  }, [copy.suggestedQuestions.loadError]);

  return (
    <section className="panel p-5 sm:p-6">
      <div className="mb-5 flex items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-slate-500">
            {copy.suggestedQuestions.eyebrow}
          </p>
          <h2 className="text-metallic-gold mt-2 text-xl font-semibold tracking-tight">
            {copy.suggestedQuestions.title}
          </h2>
        </div>

        <div className="rounded-[2px] border border-line bg-white/5 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-slate-300">
          {isLoading ? copy.suggestedQuestions.loading : questions.length}
        </div>
      </div>

      {error ? (
        <div className="border border-red-500/30 bg-red-500/10 px-4 py-4 text-sm leading-6 text-red-100">
          {error}
        </div>
      ) : null}

      {!error && questions.length === 0 && !isLoading ? (
        <div className="border border-dashed border-line bg-[#0d0d0d] px-4 py-6 text-sm leading-6 text-slate-400">
          {copy.suggestedQuestions.empty}
        </div>
      ) : null}

      {!error && questions.length > 0 ? (
        <div className="max-h-[320px] space-y-3 overflow-auto pr-1">
          {questions.map((question) => (
            <button
              key={question}
              type="button"
              onClick={() => onSelect(question)}
              className="w-full border border-line bg-[#0d0d0d] px-4 py-3 text-left text-sm leading-6 text-slate-200 transition hover:border-[#f5d15a]/35 hover:bg-[#f5d15a]/10"
            >
              {question}
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}
