import { HistoryEntry, PipelineStepId, StreamConnectionStatus } from "@/lib/types";

export type UiLocale = "en" | "cs" | "ru";

type StepCopy = Record<
  PipelineStepId,
  {
    label: string;
    description: string;
  }
>;

type LocaleMessages = {
  metadata: {
    lang: string;
    title: string;
    description: string;
  };
  common: {
    streamStatuses: Record<StreamConnectionStatus, string>;
    historyStatuses: Record<HistoryEntry["status"], string>;
    answerModes: Record<string, string>;
    cacheHit: string;
    cacheMiss: string;
    activeRun: string;
    ready: string;
    standby: string;
    yes: string;
    no: string;
    notAvailable: string;
    streamLabel: string;
  };
  dashboard: {
    defaultQuery: string;
    heroTitle: string;
    runtimeProfileLabel: string;
    runtimeProfileText: string;
    cacheClearedMessage: (redisKeysDeleted: number, cacheReset: boolean) => string;
    cacheClearError: string;
  };
  promptPanel: {
    eyebrow: string;
    title: string;
    description: string;
    queryLabel: string;
    helperTitle: string;
    helperExamples: string[];
    placeholder: string;
    warningTitle: string;
    warningText: string;
    transportLabel: string;
    transportText: string;
    refresh: string;
    running: string;
    askPipeline: string;
  };
  suggestedQuestions: {
    eyebrow: string;
    title: string;
    loading: string;
    refresh: string;
    empty: string;
    loadError: string;
  };
  queryHistory: {
    eyebrow: string;
    title: string;
    stored: (count: number) => string;
    deletingCache: string;
    deleteCache: string;
    clearAll: string;
    empty: string;
    open: string;
    runAgain: string;
    delete: string;
    cacheLabel: (hit: boolean) => string;
  };
  pipeline: {
    eyebrow: string;
    title: string;
    steps: StepCopy;
    events: {
      empty: string;
      query: string;
      embedding: string;
      retrieval: string;
      rerank: string;
      context: string;
      llm: string;
      answer: string;
    };
  };
  executionLog: {
    eyebrow: string;
    title: string;
    empty: string;
  };
  answerResult: {
    eyebrow: string;
    title: string;
    waiting: string;
    query: string;
    answer: string;
    llmRunInfo: string;
    runId: string;
    source: string;
    pipeline: string;
    cache: string;
    sources: string;
    noSources: string;
  };
  hookMessages: {
    legacySnapshotMissing: string;
    querySubmitted: string;
    streamConnected: string;
    streamDisconnected: string;
    streamUnavailable: string;
    streamInitFailed: string;
    answerReceived: string;
    requestFailed: string;
    presetSelected: string;
    presetLlmSkipped: string;
    presetAnswerReady: string;
    presetAnswerMissing: string;
  };
  apiErrors: {
    backendRequestFailedStatus: (status: number) => string;
    backendRequestFailed: string;
    cacheClearFailedStatus: (status: number) => string;
    questionBankFailedStatus: (status: number) => string;
    questionBankTimedOut: string;
  };
};

const LOCALES: Record<UiLocale, LocaleMessages> = {
  en: {
    metadata: {
      lang: "en",
      title: "Hybrid RAG SEC AI Control Room",
      description: "Live execution dashboard for the Hybrid RAG SEC AI pipeline.",
    },
    common: {
      streamStatuses: {
        idle: "idle",
        connecting: "connecting",
        open: "live stream",
        fallback: "answer only",
        closed: "closed",
        error: "stream error",
      },
      historyStatuses: {
        pending: "pending",
        success: "success",
        error: "error",
      },
      answerModes: {
        cache: "cache",
        pipeline: "pipeline",
        history: "history",
        preset: "preset",
      },
      cacheHit: "cache hit",
      cacheMiss: "cache miss",
      activeRun: "active run",
      ready: "ready",
      standby: "standby",
      yes: "yes",
      no: "no",
      notAvailable: "n/a",
      streamLabel: "stream",
    },
    dashboard: {
      defaultQuery: "What legal risks did Apple mention in its 10-K filings?",
      heroTitle: "Live pipeline control room for AI-powered SEC filing retrieval and answer generation.",
      runtimeProfileLabel: "Runtime profile",
      runtimeProfileText:
        "Two-panel dashboard for demos, debugging, and technical presentations. The UI listens to live pipeline events and renders the final grounded answer from the production backend.",
      cacheClearedMessage: (redisKeysDeleted, cacheReset) =>
        `Cache cleared. Redis keys deleted: ${redisKeysDeleted}. Answer cache file reset: ${cacheReset ? "yes" : "no"}.`,
      cacheClearError: "Failed to clear backend cache.",
    },
    promptPanel: {
      eyebrow: "Prompt panel",
      title: "Run a live filing query",
      description:
        "Send a prompt to the production RAG backend and watch each pipeline stage update in real time.",
      queryLabel: "Query",
      helperTitle: "Ask questions about SEC filings and financial reports.",
      helperExamples: [
        "What legal risks did Apple mention in its 10-K filings?",
        "Summarize risk factors in NVIDIA's annual report.",
        "What litigation risks appear in the filings?",
      ],
      placeholder: "What legal risks did Apple mention in its 10-K filings?",
      warningTitle: "This system is designed to analyze SEC filings and financial documents.",
      warningText: "Please ask questions related to company filings or financial reports.",
      transportLabel: "Transport",
      transportText: "SSE for live execution and POST for the final answer.",
      refresh: "Refresh",
      running: "Running...",
      askPipeline: "Ask pipeline",
    },
    suggestedQuestions: {
      eyebrow: "Suggested questions",
      title: "Top 20 questions",
      loading: "Loading...",
      refresh: "Refresh",
      empty: "No suggested questions available.",
      loadError: "Failed to load suggested questions.",
    },
    queryHistory: {
      eyebrow: "Query history",
      title: "Previous runs",
      stored: (count) => `${count} stored`,
      deletingCache: "Deleting cache...",
      deleteCache: "Delete cache",
      clearAll: "Clear all",
      empty: "No queries yet. Submit a prompt to create a replayable session history.",
      open: "Open",
      runAgain: "Run again",
      delete: "Delete",
      cacheLabel: (hit) => (hit ? "cache hit" : "cache miss"),
    },
    pipeline: {
      eyebrow: "Pipeline view",
      title: "Execution map",
      steps: {
        prompt: {
          label: "Prompt",
          description: "Incoming user request enters the runtime graph.",
        },
        embedding: {
          label: "Embedding",
          description: "Query gets transformed into vector space for retrieval.",
        },
        retrieval: {
          label: "Hybrid Retrieval",
          description: "Qdrant and BM25 search run and merge their candidates.",
        },
        rerank: {
          label: "Rerank",
          description: "CrossEncoder rescoring refines the highest-value chunks.",
        },
        context: {
          label: "Context Build",
          description: "Top grounded excerpts are formatted for answer generation.",
        },
        llm: {
          label: "LLM",
          description: "LLM generates the final grounded response.",
        },
        answer: {
          label: "Answer",
          description: "Final answer and sources are returned to the interface.",
        },
      },
      events: {
        empty: "Empty event",
        query: "Query received",
        embedding: "Embedding completed",
        retrieval: "Retrieval completed",
        rerank: "Rerank completed",
        context: "Context built",
        llm: "LLM is generating the answer",
        answer: "Answer ready",
      },
    },
    executionLog: {
      eyebrow: "Execution log",
      title: "Live pipeline trace",
      empty: "Start a query to watch backend events arrive here in real time.",
    },
    answerResult: {
      eyebrow: "Final answer",
      title: "Grounded response",
      waiting: "The final answer will appear here once the backend completes the run.",
      query: "Query",
      answer: "Answer",
      llmRunInfo: "LLM Run Info",
      runId: "run_id",
      source: "source",
      pipeline: "pipeline",
      cache: "cache",
      sources: "Sources",
      noSources: "No sources returned.",
    },
    hookMessages: {
      legacySnapshotMissing: "This older history entry does not contain a complete saved run snapshot.",
      querySubmitted: "Query submitted from frontend control room.",
      streamConnected: "Live pipeline stream connected.",
      streamDisconnected: "Live pipeline stream disconnected. Final answer request is still running.",
      streamUnavailable: "Live stream is unavailable. Falling back to answer-only mode.",
      streamInitFailed: "Unable to initialize EventSource. Falling back to answer-only mode.",
      answerReceived: "Final answer received from /api/ask.",
      requestFailed: "Request failed. The backend did not return a valid answer.",
      presetSelected: "Local preset selected. Backend and LLM remain disabled.",
      presetLlmSkipped: "LLM step skipped. Preset response loaded locally.",
      presetAnswerReady: "Preset answer is ready.",
      presetAnswerMissing: "Preset answer bank is missing an entry for this query.",
    },
    apiErrors: {
      backendRequestFailedStatus: (status) => `Backend request failed with status ${status}.`,
      backendRequestFailed: "Backend request failed.",
      cacheClearFailedStatus: (status) => `Cache clear failed with status ${status}.`,
      questionBankFailedStatus: (status) => `Question bank request failed with status ${status}.`,
      questionBankTimedOut: "Question bank request timed out.",
    },
  },
  cs: {
    metadata: {
      lang: "cs",
      title: "DocBrain",
      description: "Prémiové auditní rozhraní pro ověřování SEC dokumentů a finančních rizik.",
    },
    common: {
      streamStatuses: {
        idle: "nečinný",
        connecting: "připojování",
        open: "živý přenos",
        fallback: "jen odpověď",
        closed: "uzavřen",
        error: "chyba přenosu",
      },
      historyStatuses: {
        pending: "čeká",
        success: "hotovo",
        error: "chyba",
      },
      answerModes: {
        cache: "cache",
        pipeline: "živé ověření",
        history: "historie",
        preset: "preset",
      },
      cacheHit: "zásah cache",
      cacheMiss: "bez cache",
      activeRun: "aktivní běh",
      ready: "připraveno",
      standby: "pohotovost",
      yes: "ano",
      no: "ne",
      notAvailable: "není k dispozici",
      streamLabel: "stream",
    },
    dashboard: {
      defaultQuery: "Jaká právní rizika Apple uvedl ve svých 10-K filings?",
      heroTitle: "DocBrain převádí SEC filings na ověřené investiční poznatky v jednom auditním toku.",
      runtimeProfileLabel: "Auditní režim",
      runtimeProfileText:
        "Rozhraní pro due diligence nad SEC filings. Sleduje auditní stopu retrieval pipeline, zachovává zdroje a vrací finální odpověď podloženou produkčním backendem.",
      cacheClearedMessage: (redisKeysDeleted, cacheReset) =>
        `Cache vyčištěna. Smazané Redis klíče: ${redisKeysDeleted}. Soubor answer cache resetován: ${cacheReset ? "ano" : "ne"}.`,
      cacheClearError: "Vyčištění backend cache se nepodařilo.",
    },
    promptPanel: {
      eyebrow: "Intelligence Input",
      title: "Zadejte dotaz pro finanční audit",
      description:
        "Zadejte vlastní zadání nebo spusťte rychlý audit. Funkční logika RAG, API i SEC vyhledávání zůstává beze změny.",
      queryLabel: "Auditní zadání",
      helperTitle: "Rychlý audit",
      helperExamples: [
        "Právní rizika společnosti Apple v posledním 10-K.",
        "Finanční zdraví NVIDIA podle nejnovější výroční zprávy.",
        "Kyberbezpečnostní expozice a rizika dodavatelského řetězce.",
      ],
      placeholder: "Např. porovnej právní, finanční a provozní riziko firmy podle posledního SEC 10-K.",
      warningTitle: "DocBrain analyzuje SEC filings a finanční dokumenty.",
      warningText: "Pokládejte dotazy k právním rizikům, finančnímu zdraví, kyberbezpečnosti nebo dodavatelskému řetězci.",
      transportLabel: "Přenos",
      transportText: "Živá telemetrie přes SSE, finální odpověď přes POST.",
      refresh: "Obnovit panel",
      running: "Ověřuji...",
      askPipeline: "Spustit audit",
    },
    suggestedQuestions: {
      eyebrow: "Prednastavené dotazy",
      title: "20 prednastavenych otazek",
      loading: "Načítání...",
      refresh: "Obnovit",
      empty: "Nejsou dostupné žádné doporučené dotazy.",
      loadError: "Načtení doporučených dotazů se nepodařilo.",
    },
    queryHistory: {
      eyebrow: "Sidebar",
      title: "Historie analýz",
      stored: (count) => `${count} záznamů`,
      deletingCache: "Mažu cache...",
      deleteCache: "Vyčistit cache",
      clearAll: "Smazat vše",
      empty: "Zatím nebyla spuštěna žádná analýza. Po prvním auditu se zde objeví historie i reporty.",
      open: "Otevřít",
      runAgain: "Spustit znovu",
      delete: "Smazat",
      cacheLabel: (hit) => (hit ? "zásah cache" : "bez cache"),
    },
    pipeline: {
      eyebrow: "Auditní stopa",
      title: "Auditní stopa",
      steps: {
        prompt: {
          label: "Příjem dotazu",
          description: "Vstupní zadání je zařazeno do auditního toku.",
        },
        embedding: {
          label: "Embedding",
          description: "Dotaz se převádí do vektorového prostoru pro ověřené vyhledání.",
        },
        retrieval: {
          label: "Retrieval",
          description: "Qdrant a BM25 dohledají relevantní filingy a sloučí kandidáty.",
        },
        rerank: {
          label: "Rerank",
          description: "CrossEncoder vytřídí nejdůležitější pasáže pro investiční audit.",
        },
        context: {
          label: "Validace kontextu",
          description: "Vybrané pasáže jsou připraveny pro odpověď se zachovanými zdroji.",
        },
        llm: {
          label: "LLM",
          description: "LLM sestaví finální, zdrojově podloženou odpověď.",
        },
        answer: {
          label: "Výstup",
          description: "Ověřené poznatky a citace jsou vráceny do rozhraní.",
        },
      },
      events: {
        empty: "Prázdná událost",
        query: "Dotaz přijat do auditní stopy",
        embedding: "Embedding dokončen",
        retrieval: "Retrieval dokončen",
        rerank: "Rerank dokončen",
        context: "Kontext validován",
        llm: "LLM připravuje ověřené poznatky",
        answer: "Odpověď připravena",
      },
    },
    executionLog: {
      eyebrow: "Provozní telemetrie",
      title: "Tok ověřování",
      empty: "Spusťte audit a sledujte, jak do rozhraní přichází živé backendové události.",
    },
    answerResult: {
      eyebrow: "Výsledky",
      title: "Ověřené poznatky",
      waiting: "Po dokončení backendového běhu se zde zobrazí finální auditní výstup.",
      query: "Auditní zadání",
      answer: "Poznatky",
      llmRunInfo: "Auditní metadata",
      runId: "run_id",
      source: "zdroj",
      pipeline: "živé ověření",
      cache: "cache",
      sources: "Zdroje",
      noSources: "Nebyly vráceny žádné zdroje.",
    },
    hookMessages: {
      legacySnapshotMissing: "Tato starší položka historie neobsahuje kompletní uložený snapshot běhu.",
      querySubmitted: "Auditní zadání bylo odesláno z rozhraní DocBrain.",
      streamConnected: "Živý stream auditní stopy byl připojen.",
      streamDisconnected: "Živý stream auditní stopy se odpojil. Finální odpověď se stále zpracovává.",
      streamUnavailable: "Živý stream není dostupný. Přepínám do režimu pouze s odpovědí.",
      streamInitFailed: "Inicializace EventSource selhala. Přepínám do režimu pouze s odpovědí.",
      answerReceived: "Finální auditní odpověď byla přijata z /api/ask.",
      requestFailed: "Požadavek selhal. Backend nevrátil platnou odpověď.",
      presetSelected: "Byl zvolen lokalni preset. Backend i LLM zustavaji vypnute.",
      presetLlmSkipped: "Krok LLM byl preskocen. Preset odpoved byla nactena lokalne.",
      presetAnswerReady: "Preset odpoved je pripravena.",
      presetAnswerMissing: "V bance preset odpovedi chybi zaznam pro tento dotaz.",
    },
    apiErrors: {
      backendRequestFailedStatus: (status) => `Požadavek na backend selhal se statusem ${status}.`,
      backendRequestFailed: "Požadavek na backend selhal.",
      cacheClearFailedStatus: (status) => `Vyčištění cache selhalo se statusem ${status}.`,
      questionBankFailedStatus: (status) => `Načtení banky dotazů selhalo se statusem ${status}.`,
      questionBankTimedOut: "Načítání banky dotazů vypršelo.",
    },
  },
  ru: {
    metadata: {
      lang: "ru",
      title: "Панель Управления Hybrid RAG SEC AI",
      description: "Живой дашборд выполнения пайплайна Hybrid RAG SEC AI.",
    },
    common: {
      streamStatuses: {
        idle: "ожидание",
        connecting: "подключение",
        open: "живой поток",
        fallback: "только ответ",
        closed: "закрыт",
        error: "ошибка потока",
      },
      historyStatuses: {
        pending: "в ожидании",
        success: "готово",
        error: "ошибка",
      },
      answerModes: {
        cache: "кэш",
        pipeline: "пайплайн",
        history: "история",
        preset: "пресет",
      },
      cacheHit: "попадание в кэш",
      cacheMiss: "мимо кэша",
      activeRun: "активный запуск",
      ready: "готово",
      standby: "ожидание",
      yes: "да",
      no: "нет",
      notAvailable: "недоступно",
      streamLabel: "поток",
    },
    dashboard: {
      defaultQuery: "Какие юридические риски Apple указала в своих 10-K filings?",
      heroTitle: "Живой центр управления пайплайном для AI-поиска по SEC filings и генерации ответов.",
      runtimeProfileLabel: "Профиль выполнения",
      runtimeProfileText:
        "Двухпанельный дашборд для демо, отладки и технических презентаций. Интерфейс слушает живые события пайплайна и отображает финальный обоснованный ответ с production backend.",
      cacheClearedMessage: (redisKeysDeleted, cacheReset) =>
        `Кэш очищен. Удалено ключей Redis: ${redisKeysDeleted}. Файл кэша ответов сброшен: ${cacheReset ? "да" : "нет"}.`,
      cacheClearError: "Не удалось очистить кэш backend.",
    },
    promptPanel: {
      eyebrow: "Панель запроса",
      title: "Запустить живой запрос по filings",
      description:
        "Отправьте prompt в production RAG backend и наблюдайте, как этапы пайплайна обновляются в реальном времени.",
      queryLabel: "Запрос",
      helperTitle: "Задавайте вопросы по SEC filings и финансовым отчетам.",
      helperExamples: [
        "Какие юридические риски Apple упоминала в своих 10-K filings?",
        "Суммируй факторы риска в годовом отчете NVIDIA.",
        "Какие риски судебных разбирательств встречаются в filings?",
      ],
      placeholder: "Какие юридические риски Apple упоминала в своих 10-K filings?",
      warningTitle: "Эта система предназначена для анализа SEC filings и финансовых документов.",
      warningText: "Пожалуйста, задавайте вопросы, связанные с корпоративными filings или финансовыми отчетами.",
      transportLabel: "Транспорт",
      transportText: "Живое выполнение через SSE и финальный ответ через POST.",
      refresh: "Обновить",
      running: "Запуск...",
      askPipeline: "Запустить пайплайн",
    },
    suggestedQuestions: {
      eyebrow: "Рекомендуемые вопросы",
      title: "20 готовых вопросов",
      loading: "Загрузка...",
      refresh: "Обновить",
      empty: "Нет доступных рекомендуемых вопросов.",
      loadError: "Не удалось загрузить рекомендуемые вопросы.",
    },
    queryHistory: {
      eyebrow: "История запросов",
      title: "Предыдущие запуски",
      stored: (count) => `${count} сохранено`,
      deletingCache: "Удаление кэша...",
      deleteCache: "Удалить кэш",
      clearAll: "Очистить всё",
      empty: "Запросов пока нет. Отправьте prompt, чтобы создать историю с возможностью повторного запуска.",
      open: "Открыть",
      runAgain: "Запустить снова",
      delete: "Удалить",
      cacheLabel: (hit) => (hit ? "попадание в кэш" : "мимо кэша"),
    },
    pipeline: {
      eyebrow: "Вид пайплайна",
      title: "Карта выполнения",
      steps: {
        prompt: {
          label: "Prompt",
          description: "Входящий пользовательский запрос попадает в граф выполнения.",
        },
        embedding: {
          label: "Embedding",
          description: "Запрос преобразуется в векторное пространство для retrieval.",
        },
        retrieval: {
          label: "Гибридный retrieval",
          description: "Qdrant и BM25 выполняют поиск и объединяют кандидатов.",
        },
        rerank: {
          label: "Rerank",
          description: "CrossEncoder пересчитывает самые ценные chunks.",
        },
        context: {
          label: "Сборка контекста",
          description: "Наиболее релевантные фрагменты форматируются для генерации ответа.",
        },
        llm: {
          label: "LLM",
          description: "LLM генерирует финальный обоснованный ответ.",
        },
        answer: {
          label: "Ответ",
          description: "Финальный ответ и источники возвращаются в интерфейс.",
        },
      },
      events: {
        empty: "Пустое событие",
        query: "Запрос получен",
        embedding: "Embedding завершен",
        retrieval: "Retrieval завершен",
        rerank: "Rerank завершен",
        context: "Контекст собран",
        llm: "LLM генерирует ответ",
        answer: "Ответ готов",
      },
    },
    executionLog: {
      eyebrow: "Лог выполнения",
      title: "Живая трассировка пайплайна",
      empty: "Запустите запрос, чтобы наблюдать, как сюда в реальном времени приходят события backend.",
    },
    answerResult: {
      eyebrow: "Финальный ответ",
      title: "Обоснованный ответ",
      waiting: "Финальный ответ появится здесь после завершения работы backend.",
      query: "Запрос",
      answer: "Ответ",
      llmRunInfo: "Информация о запуске LLM",
      runId: "run_id",
      source: "источник",
      pipeline: "пайплайн",
      cache: "кэш",
      sources: "Источники",
      noSources: "Источники не были возвращены.",
    },
    hookMessages: {
      legacySnapshotMissing: "Эта старая запись истории не содержит полный сохраненный snapshot запуска.",
      querySubmitted: "Запрос отправлен из панели управления frontend.",
      streamConnected: "Живой поток пайплайна подключен.",
      streamDisconnected: "Живой поток пайплайна отключился. Запрос финального ответа все еще выполняется.",
      streamUnavailable: "Живой поток недоступен. Переключение в режим только ответа.",
      streamInitFailed: "Не удалось инициализировать EventSource. Переключение в режим только ответа.",
      answerReceived: "Финальный ответ получен из /api/ask.",
      requestFailed: "Запрос завершился ошибкой. Backend не вернул корректный ответ.",
      presetSelected: "Выбран локальный пресет. Backend и LLM не вызываются.",
      presetLlmSkipped: "Шаг LLM пропущен. Локальный пресет загружен.",
      presetAnswerReady: "Preset-ответ готов.",
      presetAnswerMissing: "В банке preset-ответов нет записи для этого запроса.",
    },
    apiErrors: {
      backendRequestFailedStatus: (status) => `Запрос к backend завершился ошибкой со статусом ${status}.`,
      backendRequestFailed: "Запрос к backend завершился ошибкой.",
      cacheClearFailedStatus: (status) => `Очистка кэша завершилась ошибкой со статусом ${status}.`,
      questionBankFailedStatus: (status) => `Загрузка банка вопросов завершилась ошибкой со статусом ${status}.`,
      questionBankTimedOut: "Время ожидания загрузки банка вопросов истекло.",
    },
  },
};

function normalizeLocale(value: string | undefined): UiLocale {
  const normalized = value?.toLowerCase();
  if (normalized === "cs" || normalized === "ru" || normalized === "en") {
    return normalized;
  }
  return "cs";
}

export const LOCALE_STORAGE_KEY = "hybrid-rag-sec-ai-ui-locale";
export const uiLocale: UiLocale = "cs";
export const copy = LOCALES.cs;
let currentRuntimeLocale: UiLocale = uiLocale;

export function getCopyForLocale(locale: UiLocale) {
  return LOCALES[locale];
}

export function getRuntimeLocale(): UiLocale {
  if (typeof window !== "undefined") {
    const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
    if (stored) {
      currentRuntimeLocale = normalizeLocale(stored);
      return currentRuntimeLocale;
    }
  }

  return currentRuntimeLocale;
}

export function setRuntimeLocale(locale: UiLocale) {
  currentRuntimeLocale = normalizeLocale(locale);
}

export function getRuntimeCopy() {
  return getCopyForLocale(getRuntimeLocale());
}

export function translateStreamStatus(
  status: StreamConnectionStatus,
  locale: UiLocale = getRuntimeLocale(),
) {
  return getCopyForLocale(locale).common.streamStatuses[status] ?? status;
}

export function translateHistoryStatus(
  status: HistoryEntry["status"],
  locale: UiLocale = getRuntimeLocale(),
) {
  return getCopyForLocale(locale).common.historyStatuses[status] ?? status;
}

export function translateAnswerMode(
  mode: string | null | undefined,
  locale: UiLocale = getRuntimeLocale(),
) {
  if (!mode) {
    return mode;
  }

  return getCopyForLocale(locale).common.answerModes[mode] ?? mode;
}

export function translateCacheState(
  hit: boolean,
  locale: UiLocale = getRuntimeLocale(),
) {
  const activeCopy = getCopyForLocale(locale);
  return hit ? activeCopy.common.cacheHit : activeCopy.common.cacheMiss;
}

export function translatePipelineStep(
  stepId: PipelineStepId,
  locale: UiLocale = getRuntimeLocale(),
) {
  return getCopyForLocale(locale).pipeline.steps[stepId]?.label ?? stepId;
}

export function translateBackendEvent(
  message: string,
  locale: UiLocale = getRuntimeLocale(),
) {
  const activeCopy = getCopyForLocale(locale);
  const normalized = message.trim().toLowerCase();

  if (!normalized) {
    return activeCopy.pipeline.events.empty;
  }

  if (/\bquery_received\b|\bquery_started\b|\bquery_submitted\b/.test(normalized)) {
    return activeCopy.pipeline.events.query;
  }

  if (/\bembedding_created\b|\bembedding_started\b|\bembedding_generated\b/.test(normalized)) {
    return activeCopy.pipeline.events.embedding;
  }

  if (/\bparallel_retrieval_rows\b|\bretrieved_rows\b|\bretrieval_result\b|\bhybrid_retrieval\b|\bvector_search\b|\bbm25\b|\bretrieval_started\b/.test(normalized)) {
    return activeCopy.pipeline.events.retrieval;
  }

  if (/\breranked_top_k\b|\breranking\b|\brerank_score\b|\brerank_result\b/.test(normalized)) {
    return activeCopy.pipeline.events.rerank;
  }

  if (/\bcontext_length\b|\bcontext_built\b|\bcontext_build\b/.test(normalized)) {
    return activeCopy.pipeline.events.context;
  }

  if (/\bcalling_llm\b|\bllm_generation_started\b|\bllm_ms\b|\bllm_generation\b|\bllm_error\b/.test(normalized)) {
    return activeCopy.pipeline.events.llm;
  }

  if (/\banswer_generated\b|\banswer_ready\b|\bcompleted\b|\bdone\b/.test(normalized)) {
    return activeCopy.pipeline.events.answer;
  }

  if (normalized === "empty_event") {
    return activeCopy.pipeline.events.empty;
  }

  return null;
}
