import presetAnswerBankData from "@/lib/presetAnswerBank.generated.json";
import type { UiLocale } from "@/lib/i18n";
import {
  findLocalizedPresetEntryByQuery,
  getLocalizedPresetAnswerById,
} from "@/lib/presetLocalization";

export interface StoredPresetAnswerEntry {
  id: string;
  query: string;
  answer: string;
  sources: string;
  mode: string;
  cache_hit: boolean;
  run_id?: string | null;
  captured_at: string;
}

type PresetAnswerBankFile = {
  version: number;
  generated_at: string | null;
  backend_url: string | null;
  entries: StoredPresetAnswerEntry[];
};

const PRESET_ANSWER_BANK = presetAnswerBankData as PresetAnswerBankFile;

function normalizeQuery(value: string) {
  return value.trim().toLowerCase();
}

export function getStoredPresetAnswerByQuery(query: string, locale?: UiLocale) {
  const normalized = normalizeQuery(query);
  const directEntry = PRESET_ANSWER_BANK.entries.find(
    (entry) => normalizeQuery(entry.query) === normalized,
  );

  if (directEntry) {
    if (!locale) {
      return directEntry;
    }

    const localized = getLocalizedPresetAnswerById(directEntry.id, locale);
    if (!localized) {
      return directEntry;
    }

    return {
      ...directEntry,
      query: localized.query,
      answer: localized.answer,
      sources: localized.sources,
    };
  }

  const localizedMatch = findLocalizedPresetEntryByQuery(query);
  if (!localizedMatch) {
    return undefined;
  }

  const canonicalEntry = PRESET_ANSWER_BANK.entries.find(
    (entry) => entry.id === localizedMatch.id,
  );
  if (!canonicalEntry) {
    return undefined;
  }

  const localized = getLocalizedPresetAnswerById(
    localizedMatch.id,
    locale ?? "cs",
  );
  if (!localized) {
    return canonicalEntry;
  }

  return {
    ...canonicalEntry,
    query: localized.query,
    answer: localized.answer,
    sources: localized.sources,
  };
}

export function hasStoredPresetAnswers() {
  return PRESET_ANSWER_BANK.entries.length > 0;
}

export function getStoredPresetAnswerCount() {
  return PRESET_ANSWER_BANK.entries.length;
}

export function getStoredPresetAnswerBankMeta() {
  return {
    version: PRESET_ANSWER_BANK.version,
    generatedAt: PRESET_ANSWER_BANK.generated_at,
    backendUrl: PRESET_ANSWER_BANK.backend_url,
  };
}
