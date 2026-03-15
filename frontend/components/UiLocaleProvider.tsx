"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  LOCALE_STORAGE_KEY,
  type UiLocale,
  getCopyForLocale,
  getRuntimeLocale,
  setRuntimeLocale,
  uiLocale as defaultLocale,
} from "@/lib/i18n";

type UiLocaleContextValue = {
  locale: UiLocale;
  copy: ReturnType<typeof getCopyForLocale>;
  setLocale: (locale: UiLocale) => void;
};

const UiLocaleContext = createContext<UiLocaleContextValue | null>(null);

export function UiLocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<UiLocale>(defaultLocale);

  useEffect(() => {
    setLocale(getRuntimeLocale());
  }, []);

  useEffect(() => {
    setRuntimeLocale(locale);
    window.localStorage.setItem(LOCALE_STORAGE_KEY, locale);
    document.documentElement.lang = getCopyForLocale(locale).metadata.lang;
    document.title = getCopyForLocale(locale).metadata.title;
  }, [locale]);

  const value = useMemo(
    () => ({
      locale,
      copy: getCopyForLocale(locale),
      setLocale,
    }),
    [locale],
  );

  return (
    <UiLocaleContext.Provider value={value}>
      {children}
    </UiLocaleContext.Provider>
  );
}

export function useUiLocale() {
  const context = useContext(UiLocaleContext);

  if (!context) {
    throw new Error("useUiLocale must be used within UiLocaleProvider.");
  }

  return context;
}
