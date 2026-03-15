import presetQuestionCatalog from "@/lib/presetQuestionCatalog.json";
import type { UiLocale } from "@/lib/i18n";
import {
  findLocalizedPresetEntryByQuery,
  getLocalizedPresetEntryById,
} from "@/lib/presetLocalization";

export type PresetQuestionKind = "suggested" | "quick_audit";

export interface PresetQuestionDefinition {
  id: string;
  kind: PresetQuestionKind;
  query: string;
  generationQuery?: string;
  compositeQueries?: Array<{
    label: string;
    query: string;
  }>;
  icon?: string;
  title?: string;
  description?: string;
}

const PRESET_QUESTION_CATALOG =
  presetQuestionCatalog as PresetQuestionDefinition[];

function normalizeQuery(value: string) {
  return value.trim().toLowerCase();
}

function withLocalizedFields(
  item: PresetQuestionDefinition,
  locale?: UiLocale,
): PresetQuestionDefinition {
  if (!locale) {
    return item;
  }

  const localized = getLocalizedPresetEntryById(item.id);
  if (!localized) {
    return item;
  }

  return {
    ...item,
    query: localized.query[locale] ?? item.query,
    title: localized.title?.[locale] ?? item.title,
    description: localized.description?.[locale] ?? item.description,
  };
}

export function getPresetQuestionCatalog() {
  return PRESET_QUESTION_CATALOG;
}

export function getSuggestedPresetQuestions(limit = 20, locale?: UiLocale) {
  return PRESET_QUESTION_CATALOG
    .filter((item) => item.kind === "suggested")
    .slice(0, limit)
    .map((item) => withLocalizedFields(item, locale));
}

export function getQuickAuditPresets(locale?: UiLocale) {
  return PRESET_QUESTION_CATALOG.filter(
    (item): item is PresetQuestionDefinition & {
      kind: "quick_audit";
      icon: string;
      title: string;
      description: string;
    } =>
      item.kind === "quick_audit" &&
      typeof item.icon === "string" &&
      typeof item.title === "string" &&
      typeof item.description === "string",
  ).map((item) => withLocalizedFields(item, locale));
}

export function getPresetQuestionByQuery(query: string) {
  const normalized = normalizeQuery(query);
  const directMatch = PRESET_QUESTION_CATALOG.find(
    (item) => normalizeQuery(item.query) === normalized,
  );

  if (directMatch) {
    return directMatch;
  }

  const localizedMatch = findLocalizedPresetEntryByQuery(query);
  if (!localizedMatch) {
    return undefined;
  }

  return PRESET_QUESTION_CATALOG.find((item) => item.id === localizedMatch.id);
}
