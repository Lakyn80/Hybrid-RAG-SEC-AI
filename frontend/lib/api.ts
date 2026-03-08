import { AskRequest, AskResponse } from "@/lib/types";

export async function askQuestion(payload: AskRequest): Promise<AskResponse> {
  const response = await fetch("/api/ask", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Backend request failed with status ${response.status}.`);
  }

  return (await response.json()) as AskResponse;
}
