import { AskRequest, AskResponse } from "@/lib/types";

function delay(ms: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

export async function askQuestion(payload: AskRequest): Promise<AskResponse> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
        cache: "no-store",
      });

      if (!response.ok) {
        if (response.status >= 500 && attempt === 0) {
          await delay(900);
          continue;
        }

        throw new Error(`Backend request failed with status ${response.status}.`);
      }

      return (await response.json()) as AskResponse;
    } catch (error) {
      lastError = error instanceof Error ? error : new Error("Backend request failed.");
      if (attempt === 0) {
        await delay(900);
        continue;
      }
      break;
    }
  }

  throw lastError ?? new Error("Backend request failed.");
}
