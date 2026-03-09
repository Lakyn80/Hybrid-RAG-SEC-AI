import { mapBackendEvent } from "@/lib/pipelineMap";
import { NormalizedStreamEvent } from "@/lib/types";

export interface StreamHandlers {
  onOpen?: () => void;
  onEvent?: (event: NormalizedStreamEvent) => void;
  onError?: (
    event: Event,
    context: {
      hasOpened: boolean;
    },
  ) => void;
  onException?: (error: unknown) => void;
}

export function buildStreamUrl(query: string, runId?: string) {
  const params = new URLSearchParams({
    query,
  });
  if (runId) {
    params.set("run_id", runId);
  }

  return `/api/stream?${params.toString()}`;
}

export function openPipelineStream(query: string, runId: string | undefined, handlers: StreamHandlers) {
  const eventSource = new EventSource(buildStreamUrl(query, runId));
  let hasOpened = false;
  let closedByClient = false;

  const handleMessage = (event: MessageEvent<string>) => {
    const payload = String(event.data ?? "").trim();
    if (!payload) {
      return;
    }

    const normalized = mapBackendEvent(payload);
    handlers.onEvent?.(normalized);

    if (normalized.terminal && !closedByClient) {
      closedByClient = true;
      eventSource.close();
    }
  };

  eventSource.onopen = () => {
    hasOpened = true;
    handlers.onOpen?.();
  };

  eventSource.onmessage = handleMessage;

  ["progress", "log", "pipeline", "status", "error"].forEach((eventName) => {
    eventSource.addEventListener(eventName, (event) => {
      handleMessage(event as MessageEvent<string>);
    });
  });

  eventSource.onerror = (event) => {
    if (closedByClient) {
      return;
    }
    handlers.onError?.(event, { hasOpened });
  };

  return eventSource;
}
