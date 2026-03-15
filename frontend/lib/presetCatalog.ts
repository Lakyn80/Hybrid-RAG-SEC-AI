import presetQuestionCatalog from "@/lib/presetQuestionCatalog.json";

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

export function getPresetQuestionCatalog() {
  return PRESET_QUESTION_CATALOG;
}

export function getSuggestedPresetQuestions(limit = 20) {
  return PRESET_QUESTION_CATALOG.filter((item) => item.kind === "suggested").slice(0, limit);
}

export function getQuickAuditPresets() {
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
  );
}

export function getPresetQuestionByQuery(query: string) {
  const normalized = normalizeQuery(query);
  return PRESET_QUESTION_CATALOG.find(
    (item) => normalizeQuery(item.query) === normalized,
  );
}
