"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { openPipelineStream, StreamHandlers } from "@/lib/streamClient";
import { StreamConnectionStatus } from "@/lib/types";

export function useEventStream() {
  const sourceRef = useRef<EventSource | null>(null);
  const [status, setStatus] = useState<StreamConnectionStatus>("idle");

  const close = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
    }

    setStatus((currentStatus) => {
      if (currentStatus === "idle" || currentStatus === "fallback" || currentStatus === "error") {
        return currentStatus;
      }

      return "closed";
    });
  }, []);

  const connect = useCallback(
    (query: string, handlers: StreamHandlers) => {
      close();
      setStatus("connecting");

      try {
        const source = openPipelineStream(query, {
          onOpen: () => {
            setStatus("open");
            handlers.onOpen?.();
          },
          onEvent: (event) => {
            handlers.onEvent?.(event);
          },
          onError: (event, context) => {
            if (sourceRef.current === source) {
              source.close();
              sourceRef.current = null;
            }

            setStatus(context.hasOpened ? "error" : "fallback");
            handlers.onError?.(event, context);
          },
        });

        sourceRef.current = source;
      } catch (error) {
        setStatus("fallback");
        handlers.onException?.(error);
      }
    },
    [close],
  );

  useEffect(() => {
    return () => {
      if (sourceRef.current) {
        sourceRef.current.close();
      }
    };
  }, []);

  return {
    close,
    connect,
    status,
  };
}
