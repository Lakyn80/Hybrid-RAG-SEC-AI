export interface PromptGuardState {
  showWarning: boolean;
  matchedCategory: "joke" | "weather" | "sports" | "casual" | "general" | null;
}

const NON_DOMAIN_PATTERNS: Array<{
  category: PromptGuardState["matchedCategory"];
  pattern: RegExp;
}> = [
  { category: "joke", pattern: /\b(joke|funny story|make me laugh|meme)\b/i },
  { category: "weather", pattern: /\b(weather|forecast|temperature|rain|snow|sunny)\b/i },
  { category: "sports", pattern: /\b(world cup|nba|nfl|soccer|football score|match result|who won)\b/i },
  { category: "casual", pattern: /\b(hello|hi there|how are you|good morning|good evening|chat with me)\b/i },
  {
    category: "general",
    pattern: /\b(capital of|translate this|recipe|movie recommendation|best restaurant|tell me about history)\b/i,
  },
];

export function getPromptGuardState(query: string): PromptGuardState {
  const normalized = query.trim();
  if (!normalized) {
    return {
      showWarning: false,
      matchedCategory: null,
    };
  }

  const matched = NON_DOMAIN_PATTERNS.find(({ pattern }) => pattern.test(normalized));

  return {
    showWarning: Boolean(matched),
    matchedCategory: matched?.category ?? null,
  };
}
