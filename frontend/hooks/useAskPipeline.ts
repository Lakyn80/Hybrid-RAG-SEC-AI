"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useEventStream } from "@/hooks/useEventStream";
import { askQuestion } from "@/lib/api";
import { createInitialSteps } from "@/lib/pipelineMap";
import {
  AskResponse,
  ExecutionLogEntry,
  HistoryEntry,
  NormalizedStreamEvent,
  PipelineStepId,
  PipelineStepState,
  RunState,
  StreamConnectionStatus,
} from "@/lib/types";

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

function cloneAnswer(answer: AskResponse | null): AskResponse | null {
  return answer ? { ...answer } : null;
}

function cloneRunState(run: RunState): RunState {
  return {
    ...run,
    answer: cloneAnswer(run.answer),
    logs: run.logs.map((entry) => ({ ...entry })),
    steps: run.steps.map((step) => ({ ...step })),
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

function createLegacySnapshot(rawEntry: Record<string, unknown>): RunState {
  const query = typeof rawEntry.query === "string" ? rawEntry.query : "";
  const createdAt =
    typeof rawEntry.createdAt === "string" ? rawEntry.createdAt : new Date().toISOString();
  const status = rawEntry.status === "error" ? "error" : "success";
  const answerText = typeof rawEntry.answer === "string" ? rawEntry.answer : "";
  const mode = typeof rawEntry.mode === "string" ? rawEntry.mode : "history";
  const cacheHit = typeof rawEntry.cacheHit === "boolean" ? rawEntry.cacheHit : false;

  return {
    query,
    steps: createInitialSteps().map((step) => ({
      ...step,
      status:
        status === "success" && (step.id === "prompt" || step.id === "answer")
          ? "completed"
          : "idle",
    })),
    logs: [],
    answer: answerText
      ? {
          query,
          answer: answerText,
          mode,
          sources: "",
          cache_hit: cacheHit,
        }
      : null,
    error:
      status === "error"
        ? "This older history entry does not contain a complete saved run snapshot."
        : null,
    isLoading: false,
    isStreaming: false,
    streamStatus: "closed",
    startedAt: createdAt,
    observedStreamEvents: false,
  };
}

function normalizeStreamStatus(status: unknown): StreamConnectionStatus {
  return status === "idle" ||
    status === "connecting" ||
    status === "open" ||
    status === "fallback" ||
    status === "closed" ||
    status === "error"
    ? status
    : "closed";
}

function coerceSnapshot(
  value: unknown,
  fallbackEntry: Record<string, unknown>,
): RunState {
  if (!value || typeof value !== "object") {
    return createLegacySnapshot(fallbackEntry);
  }

  const snapshot = value as Partial<RunState>;
  const legacy = createLegacySnapshot(fallbackEntry);

  return {
    query: typeof snapshot.query === "string" ? snapshot.query : legacy.query,
    steps: Array.isArray(snapshot.steps)
      ? snapshot.steps.map((step) => ({ ...step }))
      : legacy.steps,
    logs: Array.isArray(snapshot.logs)
      ? snapshot.logs.map((entry) => ({ ...entry }))
      : legacy.logs,
    answer:
      snapshot.answer && typeof snapshot.answer === "object"
        ? { ...(snapshot.answer as AskResponse) }
        : legacy.answer,
    error: typeof snapshot.error === "string" ? snapshot.error : legacy.error,
    isLoading: false,
    isStreaming: false,
    streamStatus: normalizeStreamStatus(snapshot.streamStatus),
    startedAt: typeof snapshot.startedAt === "string" ? snapshot.startedAt : legacy.startedAt,
    observedStreamEvents: Boolean(snapshot.observedStreamEvents),
  };
}

function coerceHistoryEntry(value: unknown): HistoryEntry | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const rawEntry = value as Record<string, unknown>;
  const snapshot = coerceSnapshot(rawEntry.snapshot, rawEntry);
  const query = typeof rawEntry.query === "string" ? rawEntry.query : snapshot.query;

  if (!query) {
    return null;
  }

  const mode =
    typeof rawEntry.mode === "string"
      ? rawEntry.mode
      : snapshot.answer?.mode;

  const cacheHit =
    typeof rawEntry.cacheHit === "boolean"
      ? rawEntry.cacheHit
      : snapshot.answer?.cache_hit;

  return {
    id:
      typeof rawEntry.id === "string"
        ? rawEntry.id
        : `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    query,
    createdAt:
      typeof rawEntry.createdAt === "string"
        ? rawEntry.createdAt
        : snapshot.startedAt ?? new Date().toISOString(),
    answer:
      typeof rawEntry.answer === "string"
        ? rawEntry.answer
        : snapshot.answer?.answer,
    mode,
    cacheHit,
    status: rawEntry.status === "error" ? "error" : "success",
    snapshot,
  };
}

function buildHistoryEntry(
  id: string,
  run: RunState,
  status: HistoryEntry["status"],
): HistoryEntry {
  const snapshot = cloneRunState(run);

  return {
    id,
    query: snapshot.query,
    createdAt: snapshot.startedAt ?? new Date().toISOString(),
    answer: snapshot.answer?.answer,
    mode: snapshot.answer?.mode,
    cacheHit: snapshot.answer?.cache_hit,
    status,
    snapshot,
  };
}

export function useAskPipeline() {
  const [run, setRun] = useState<RunState>(createEmptyRun);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [activeHistoryId, setActiveHistoryId] = useState<string | null>(null);
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

      const parsed = JSON.parse(raw) as unknown;
      if (!Array.isArray(parsed)) {
        return;
      }

      setHistory(
        parsed
          .map((entry) => coerceHistoryEntry(entry))
          .filter((entry): entry is HistoryEntry => entry !== null),
      );
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
    setRun((previousRun) => {
      if (!previousRun.isLoading && !previousRun.isStreaming) {
        return previousRun;
      }

      return {
        ...previousRun,
        streamStatus: status,
        isStreaming: status === "connecting" || status === "open",
      };
    });
  }, [status]);

  const addLog = useCallback((entry: ExecutionLogEntry) => {
    setRun((previousRun) => ({
      ...previousRun,
      logs: [...previousRun.logs, entry],
    }));
  }, []);

  const addHistory = useCallback((entry: HistoryEntry) => {
    setHistory((previousHistory) => appendHistoryEntry(previousHistory, entry));
    setActiveHistoryId(entry.id);
  }, []);

  const restoreHistoryEntry = useCallback(
    (entryId: string) => {
      const entry = history.find((item) => item.id === entryId);
      if (!entry) {
        return null;
      }

      activeRunIdRef.current = `history-${entryId}`;
      hasOpenedStreamRef.current = false;
      observedStreamEventRef.current = false;
      close();
      setActiveHistoryId(entry.id);
      setRun(cloneRunState(entry.snapshot));

      return entry;
    },
    [close, history],
  );

  const deleteHistoryEntry = useCallback(
    (entryId: string) => {
      setHistory((previousHistory) =>
        previousHistory.filter((entry) => entry.id !== entryId),
      );

      setActiveHistoryId((previousActiveId) => {
        if (previousActiveId !== entryId) {
          return previousActiveId;
        }

        activeRunIdRef.current = null;
        hasOpenedStreamRef.current = false;
        observedStreamEventRef.current = false;
        close();
        setRun(createEmptyRun());
        return null;
      });
    },
    [close],
  );

  const clearHistory = useCallback(() => {
    activeRunIdRef.current = null;
    hasOpenedStreamRef.current = false;
    observedStreamEventRef.current = false;
    close();
    setHistory([]);
    setActiveHistoryId(null);
    setRun(createEmptyRun());
    window.localStorage.removeItem(HISTORY_STORAGE_KEY);
  }, [close]);

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
      setActiveHistoryId(null);

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

        let historyEntry: HistoryEntry | null = null;
        setRun((previousRun) => {
          const nextRun: RunState = {
            ...previousRun,
            query: trimmedQuery,
            answer,
            error: null,
            isLoading: false,
            isStreaming: false,
            streamStatus: observedStreamEventRef.current ? "closed" : "fallback",
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
          };

          historyEntry = buildHistoryEntry(runId, nextRun, "success");
          return nextRun;
        });

        if (historyEntry) {
          addHistory(historyEntry);
        }
      } catch (error) {
        if (activeRunIdRef.current !== runId) {
          return;
        }

        close();

        const message =
          error instanceof Error
            ? error.message
            : "Request failed. The backend did not return a valid answer.";

        let historyEntry: HistoryEntry | null = null;
        setRun((previousRun) => {
          const nextRun: RunState = {
            ...previousRun,
            answer: null,
            error: message,
            isLoading: false,
            isStreaming: false,
            streamStatus: hasOpenedStreamRef.current ? "error" : "fallback",
            logs: [
              ...previousRun.logs,
              createLogEntry(message, "frontend_answer_error", "answer", "error"),
            ],
            steps: previousRun.steps.map((step) =>
              step.status === "active" ? { ...step, status: "error" } : step,
            ),
          };

          historyEntry = buildHistoryEntry(runId, nextRun, "error");
          return nextRun;
        });

        if (historyEntry) {
          addHistory(historyEntry);
        }
      }
    },
    [addHistory, addLog, close, connect],
  );

  const rerunHistoryEntry = useCallback(
    async (entryId: string) => {
      const entry = history.find((item) => item.id === entryId);
      if (!entry) {
        return;
      }

      await submitQuery(entry.query);
    },
    [history, submitQuery],
  );

  return useMemo(
    () => ({
      activeHistoryId,
      clearHistory,
      deleteHistoryEntry,
      history,
      restoreHistoryEntry,
      rerunHistoryEntry,
      run,
      submitQuery,
    }),
    [
      activeHistoryId,
      clearHistory,
      deleteHistoryEntry,
      history,
      restoreHistoryEntry,
      rerunHistoryEntry,
      run,
      submitQuery,
    ],
  );
}
