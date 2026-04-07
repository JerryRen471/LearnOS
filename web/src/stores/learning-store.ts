"use client";

import { create } from "zustand";

type LearningStoreState = {
  sessionId: string | null;
  userId: string;
  graphPath: string;
  answerDrafts: Record<string, string>;
  setSessionMeta: (meta: { sessionId: string | null; userId: string; graphPath: string }) => void;
  setAnswerDraft: (questionId: string, answer: string) => void;
  clearDrafts: () => void;
};

const STORAGE_KEY = "learnos-learning-store";
let memoryState: PersistedLearningState | null = null;

declare global {
  interface Window {
    __LEARNOS_LEARNING_STATE__?: PersistedLearningState;
  }
}

type PersistedLearningState = Pick<
  LearningStoreState,
  "sessionId" | "userId" | "graphPath" | "answerDrafts"
>;

const defaultPersistedState: PersistedLearningState = {
  sessionId: null,
  userId: "demo-user",
  graphPath: ".zhicore/graph.json",
  answerDrafts: {},
};

function readPersistedState(): PersistedLearningState {
  if (memoryState) {
    return memoryState;
  }
  if (typeof window === "undefined") {
    return defaultPersistedState;
  }

  if (window.__LEARNOS_LEARNING_STATE__) {
    memoryState = window.__LEARNOS_LEARNING_STATE__;
    return window.__LEARNOS_LEARNING_STATE__;
  }

  const fromLocalStorage = readFromLocalStorage();
  if (fromLocalStorage) {
    memoryState = fromLocalStorage;
    return fromLocalStorage;
  }

  const fromCookie = readFromCookie();
  if (fromCookie) {
    memoryState = fromCookie;
    return fromCookie;
  }

  memoryState = defaultPersistedState;
  return defaultPersistedState;
}

function readFromLocalStorage(): PersistedLearningState | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<PersistedLearningState>;
    return {
      sessionId: parsed.sessionId ?? defaultPersistedState.sessionId,
      userId: parsed.userId ?? defaultPersistedState.userId,
      graphPath: parsed.graphPath ?? defaultPersistedState.graphPath,
      answerDrafts: parsed.answerDrafts ?? {},
    };
  } catch {
    return null;
  }
}

function readFromCookie(): PersistedLearningState | null {
  try {
    const cookie = window.document.cookie
      .split("; ")
      .find((item) => item.startsWith(`${STORAGE_KEY}=`));
    if (!cookie) {
      return null;
    }
    const encoded = cookie.slice(STORAGE_KEY.length + 1);
    const parsed = JSON.parse(decodeURIComponent(encoded)) as Partial<PersistedLearningState>;
    return {
      sessionId: parsed.sessionId ?? defaultPersistedState.sessionId,
      userId: parsed.userId ?? defaultPersistedState.userId,
      graphPath: parsed.graphPath ?? defaultPersistedState.graphPath,
      answerDrafts: parsed.answerDrafts ?? {},
    };
  } catch {
    return null;
  }
}

function writePersistedState(state: PersistedLearningState): void {
  memoryState = state;
  if (typeof window === "undefined") {
    return;
  }
  window.__LEARNOS_LEARNING_STATE__ = state;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Ignore storage write failures to keep UI usable.
  }
  try {
    const encoded = encodeURIComponent(JSON.stringify(state));
    window.document.cookie = `${STORAGE_KEY}=${encoded}; path=/; max-age=86400; samesite=lax`;
  } catch {
    // Ignore cookie write failures to keep UI usable.
  }
}

export const useLearningStore = create<LearningStoreState>((set, get) => {
  const persisted = readPersistedState();

  return {
    ...persisted,
    setSessionMeta: ({ sessionId, userId, graphPath }) => {
      set({ sessionId, userId, graphPath });
      writePersistedState({
        ...get(),
        sessionId,
        userId,
        graphPath,
      });
    },
    setAnswerDraft: (questionId, answer) => {
      const nextAnswerDrafts = {
        ...get().answerDrafts,
        [questionId]: answer,
      };
      set({ answerDrafts: nextAnswerDrafts });
      writePersistedState({
        ...get(),
        answerDrafts: nextAnswerDrafts,
      });
    },
    clearDrafts: () => {
      set({ answerDrafts: {} });
      writePersistedState({
        ...get(),
        answerDrafts: {},
      });
    },
  };
});
