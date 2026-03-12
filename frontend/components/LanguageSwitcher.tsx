"use client";

import { useUiLocale } from "@/components/UiLocaleProvider";
import { type UiLocale } from "@/lib/i18n";

const OPTIONS: Array<{ locale: UiLocale; label: string }> = [
  { locale: "en", label: "EN" },
  { locale: "cs", label: "CS" },
  { locale: "ru", label: "RU" },
];

export function LanguageSwitcher() {
  const { locale, setLocale } = useUiLocale();

  return (
    <div className="inline-flex rounded-full border border-slate-200 bg-white/90 p-1 shadow-sm">
      {OPTIONS.map((option) => {
        const isActive = option.locale === locale;

        return (
          <button
            key={option.locale}
            type="button"
            onClick={() => setLocale(option.locale)}
            className={`rounded-full px-3 py-2 font-mono text-[11px] uppercase tracking-[0.22em] transition ${
              isActive
                ? "bg-slate-950 text-white"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
