"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { askQuestion } from "@/lib/api";
import { createInitialSteps } from "@/lib/pipelineMap";
import {
  ExecutionLogEntry,
  HistoryEntry,
  NormalizedStreamEvent,
  PipelineStepId,
  PipelineStepState,
  RunState,
} from "@/lib/types";
import { useEventStream } from "@/hooks/useEventStream";

const HISTORY_STORAGE_KEY = "hybrid-rag-sec-ai-history";
const HISTORY_LIMIT = 10;

function createLogEntry(
  message: string,
  raw: string,
  stepId?: PipelineStepId,
  severity: ExecutionLogEntry["severity"] = "info",
): ExecutionLogEntry {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    timestamp: new Date().toISOString(),
    message,
    raw,
    stepId,
    severity,
  };
}

function createEmptyRun(): RunState {
  return {
    query: "",
    steps: createInitialSteps(),
    logs: [],
    answer: null,
    error: null,
    isLoading: false,
    isStreaming: false,
    streamStatus: "idle",
    startedAt: null,
    observedStreamEvents: false,
  };
}

function markPromptActive(steps: PipelineStepState[]): PipelineStepState[] {
  return steps.map((step) =>
    step.id === "prompt"
      ? {
          ...step,
          status: "active",
        }
      : {
          ...step,
          status: "idle",
        },
  );
}

function advanceSteps(
  steps: PipelineStepState[],
  stepId: PipelineStepId | undefined,
  severity: NormalizedStreamEvent["severity"],
  terminal: boolean,
): PipelineStepState[] {
  if (!stepId) {
    return steps;
  }

  const index = steps.findIndex((step) => step.id === stepId);
  if (index === -1) {
    return steps;
  }

  return steps.map((step, currentIndex) => {
    if (currentIndex < index) {
      return step.status === "error" ? step : { ...step, status: "completed" };
    }

    if (currentIndex > index) {
      return step;
    }

    if (severity === "error") {
      return { ...step, status: "error" };
    }

    if (terminal || stepId === "answer") {
      return { ...step, status: "completed" };
    }

    return { ...step, status: "active" };
  });
}

function finalizeSteps(
  steps: PipelineStepState[],
  observedStreamEvents: boolean,
): PipelineStepState[] {
  return steps.map((step) => {
    if (step.id === "answer" || step.id === "prompt") {
      return { ...step, status: "completed" };
    }

    if (!observedStreamEvents) {
      return step;
    }

    if (step.status === "active") {
      return { ...step, status: "completed" };
    }

    return step;
  });
}

function appendHistoryEntry(history: HistoryEntry[], entry: HistoryEntry) {
  return [entry, ...history].slice(0, HISTORY_LIMIT);
}

export function useAskPipeline() {
  const [run, setRun] = useState<RunState>(createEmptyRun);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const { close, connect, status } = useEventStream();

  const activeRunIdRef = useRef<string | null>(null);
  const hasOpenedStreamRef = useRef(false);
  const observedStreamEventRef = useRef(false);
  const historyLoadedRef = useRef(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(HISTORY_STORAGE_KEY);
      if (!raw) {
        return;
      }

      const parsed = JSON.parse(raw) as HistoryEntry[];
      if (Array.isArray(parsed)) {
        setHistory(parsed);
      }
    } catch {
      // Ignore invalid local history.
    } finally {
      historyLoadedRef.current = true;
    }
  }, []);

  useEffect(() => {
    if (!historyLoadedRef.current) {
      return;
    }

    window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
  }, [history]);

  useEffect(() => {
    setRun((previousRun) => ({
      ...previousRun,
      streamStatus: status,
      isStreaming: status === "connecting" || status === "open",
    }));
  }, [status]);

  const addLog = useCallback((entry: ExecutionLogEntry) => {
    setRun((previousRun) => ({
      ...previousRun,
      logs: [...previousRun.logs, entry],
    }));
  }, []);

  const addHistory = useCallback((entry: HistoryEntry) => {
    setHistory((previousHistory) => appendHistoryEntry(previousHistory, entry));
  }, []);

  const submitQuery = useCallback(
    async (query: string) => {
      const trimmedQuery = query.trim();
      if (!trimmedQuery) {
        return;
      }

      const runId =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

      activeRunIdRef.current = runId;
      hasOpenedStreamRef.current = false;
      observedStreamEventRef.current = false;

      setRun({
        query: trimmedQuery,
        steps: markPromptActive(createInitialSteps()),
        logs: [
          createLogEntry(
            "Query submitted from frontend control room.",
            "frontend_query_submitted",
            "prompt",
            "system",
          ),
        ],
        answer: null,
        error: null,
        isLoading: true,
        isStreaming: true,
        streamStatus: "connecting",
        startedAt: new Date().toISOString(),
        observedStreamEvents: false,
      });

      connect(trimmedQuery, {
        onOpen: () => {
          if (activeRunIdRef.current !== runId) {
            return;
          }

          hasOpenedStreamRef.current = true;
          addLog(
            createLogEntry(
              "Live pipeline stream connected.",
              "frontend_stream_open",
              undefined,
              "system",
            ),
          );
        },
        onEvent: (event) => {
          if (activeRunIdRef.current !== runId) {
            return;
          }

          observedStreamEventRef.current = true;
          addLog(
            createLogEntry(event.message, event.raw, event.stepId, event.severity),
          );

          setRun((previousRun) => ({
            ...previousRun,
            observedStreamEvents: true,
            steps: advanceSteps(
              previousRun.steps,
              event.stepId,
              event.severity,
              event.terminal,
            ),
          }));

          if (event.terminal) {
            close();
          }
        },
        onError: () => {
          if (activeRunIdRef.current !== runId) {
            return;
          }

          const fallbackMessage = hasOpenedStreamRef.current
            ? "Live pipeline stream disconnected. Final answer request is still running."
            : "Live stream is unavailable. Falling back to answer-only mode.";

          addLog(
            createLogEntry(
              fallbackMessage,
              "frontend_stream_fallback",
              undefined,
              hasOpenedStreamRef.current ? "error" : "system",
            ),
          );
        },
        onException: () => {
          if (activeRunIdRef.current !== runId) {
            return;
          }

          addLog(
            createLogEntry(
              "Unable to initialize EventSource. Falling back to answer-only mode.",
              "frontend_stream_exception",
              undefined,
              "system",
            ),
          );
        },
      });

      try {
        const answer = await askQuestion({ query: trimmedQuery });
        if (activeRunIdRef.current !== runId) {
          return;
        }

        close();

        setRun((previousRun) => ({
          ...previousRun,
          answer,
          error: null,
          isLoading: false,
          isStreaming: false,
          observedStreamEvents: observedStreamEventRef.current,
          steps: finalizeSteps(previousRun.steps, observedStreamEventRef.current),
          logs: [
            ...previousRun.logs,
            createLogEntry(
              "Final answer received from /api/ask.",
              "frontend_answer_received",
              "answer",
              "system",
            ),
          ],
        }));

        addHistory({
          id: runId,
          query: trimmedQuery,
          createdAt: new Date().toISOString(),
          answer: answer.answer,
          mode: answer.mode,
          cacheHit: answer.cache_hit,
          status: "success",
        });
      } catch (error) {
        if (activeRunIdRef.current !== runId) {
          return;
        }

        close();

        const message =
          error instanceof Error
            ? error.message
            : "Request failed. The backend did not return a valid answer.";

        setRun((previousRun) => ({
          ...previousRun,
          answer: null,
          error: message,
          isLoading: false,
          isStreaming: false,
          logs: [
            ...previousRun.logs,
            createLogEntry(message, "frontend_answer_error", "answer", "error"),
          ],
          steps: previousRun.steps.map((step) =>
            step.status === "active" ? { ...step, status: "error" } : step,
          ),
        }));

        addHistory({
          id: runId,
          query: trimmedQuery,
          createdAt: new Date().toISOString(),
          status: "error",
        });
      }
    },
    [addHistory, addLog, close, connect],
  );

  return useMemo(
    () => ({
      history,
      run,
      submitQuery,
    }),
    [history, run, submitQuery],
  );
}
