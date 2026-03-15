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
    <div className="inline-flex border border-line bg-[#0d0d0d] p-1">
      {OPTIONS.map((option) => {
        const isActive = option.locale === locale;

        return (
          <button
            key={option.locale}
            type="button"
            onClick={() => setLocale(option.locale)}
            className={`px-3 py-2 font-mono text-[11px] uppercase tracking-[0.22em] transition ${
              isActive
                ? "bg-[linear-gradient(90deg,#fff8cc_0%,#f5d15a_28%,#c9971d_56%,#fff2a0_100%)] text-slate-950"
                : "text-slate-300 hover:bg-white/5 hover:text-white"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
