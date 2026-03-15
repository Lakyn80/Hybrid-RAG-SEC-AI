import presetAnswerBankData from "@/lib/presetAnswerBank.generated.json";

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

export function getStoredPresetAnswerByQuery(query: string) {
  const normalized = normalizeQuery(query);
  return PRESET_ANSWER_BANK.entries.find(
    (entry) => normalizeQuery(entry.query) === normalized,
  );
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
