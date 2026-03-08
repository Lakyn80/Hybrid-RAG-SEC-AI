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

export function buildStreamUrl(query: string) {
  const params = new URLSearchParams({
    query,
  });

  return `/api/stream?${params.toString()}`;
}

export function openPipelineStream(query: string, handlers: StreamHandlers) {
  const eventSource = new EventSource(buildStreamUrl(query));
  let hasOpened = false;
  let closedByClient = false;

  const handleMessage = (event: MessageEvent<string>) => {
    const normalized = mapBackendEvent(event.data);
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
