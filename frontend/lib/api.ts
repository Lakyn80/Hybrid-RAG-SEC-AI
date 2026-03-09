import {
  AskRequest,
  AskResponse,
  CacheClearResponse,
  QuestionBankResponse,
} from "@/lib/types";

function delay(ms: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

export async function askQuestion(
  payload: AskRequest,
  options?: {
    runId?: string;
  },
): Promise<AskResponse> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(options?.runId ? { "X-Run-ID": options.runId } : {}),
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

      const runId = response.headers.get("X-Run-ID") || options?.runId || null;
      const answer = (await response.json()) as AskResponse;

      return {
        ...answer,
        run_id: runId,
      };
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

export async function clearSystemCache(): Promise<CacheClearResponse> {
  const response = await fetch("/api/cache/clear", {
    method: "POST",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Cache clear failed with status ${response.status}.`);
  }

  return (await response.json()) as CacheClearResponse;
}

export async function getQuestionBank(): Promise<QuestionBankResponse> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => {
    controller.abort();
  }, 180000);

  try {
    const response = await fetch("/api/question-bank", {
      method: "GET",
      cache: "no-store",
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`Question bank request failed with status ${response.status}.`);
    }

    return (await response.json()) as QuestionBankResponse;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Question bank request timed out.");
    }

    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}
