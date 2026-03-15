import presetLocalizationData from "@/lib/presetLocalization.generated.json";
import type { UiLocale } from "@/lib/i18n";

type LocalizedText = Record<UiLocale, string>;

export interface LocalizedPresetEntry {
  id: string;
  kind: "suggested" | "quick_audit";
  query: LocalizedText;
  title?: LocalizedText | null;
  description?: LocalizedText | null;
  answer?: LocalizedText | null;
  sources?: LocalizedText | null;
}

type PresetLocalizationFile = {
  version: number;
  generated_at: string | null;
  entries: LocalizedPresetEntry[];
};

const PRESET_LOCALIZATION = presetLocalizationData as PresetLocalizationFile;

function normalizeQuery(value: string) {
  return value.trim().toLowerCase();
}

export function getLocalizedPresetEntries() {
  return PRESET_LOCALIZATION.entries;
}

export function getLocalizedPresetEntryById(id: string) {
  return PRESET_LOCALIZATION.entries.find((entry) => entry.id === id);
}

export function getLocalizedPresetQueryById(id: string, locale: UiLocale) {
  return getLocalizedPresetEntryById(id)?.query?.[locale] ?? null;
}

export function findLocalizedPresetEntryByQuery(query: string) {
  const normalized = normalizeQuery(query);

  return PRESET_LOCALIZATION.entries.find((entry) =>
    (["en", "cs", "ru"] as UiLocale[]).some((locale) =>
      normalizeQuery(entry.query[locale]) === normalized,
    ),
  );
}

export function getLocalizedPresetAnswerById(id: string, locale: UiLocale) {
  const entry = getLocalizedPresetEntryById(id);
  if (!entry?.answer || !entry?.sources) {
    return null;
  }

  return {
    query: entry.query[locale],
    answer: entry.answer[locale],
    sources: entry.sources[locale],
  };
}
