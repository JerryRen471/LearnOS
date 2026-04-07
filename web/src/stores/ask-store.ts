"use client";

import { create } from "zustand";

export type AskMode = "graph-rag" | "agent";

type AskStoreState = {
  mode: AskMode;
  isEvidencePanelOpen: boolean;
  isRunPanelOpen: boolean;
  latestRunId: string | null;
  setMode: (mode: AskMode) => void;
  toggleEvidencePanel: () => void;
  toggleRunPanel: () => void;
  setLatestRunId: (runId: string | null) => void;
};

const STORAGE_KEY = "learnos-ask-store";
let memoryState: PersistedAskState | null = null;

type PersistedAskState = Pick<
  AskStoreState,
  "mode" | "isEvidencePanelOpen" | "isRunPanelOpen" | "latestRunId"
>;

const defaultPersistedState: PersistedAskState = {
  mode: "graph-rag",
  isEvidencePanelOpen: true,
  isRunPanelOpen: true,
  latestRunId: null,
};

function readPersistedState(): PersistedAskState {
  if (memoryState) {
    return memoryState;
  }
  if (typeof window === "undefined") {
    return defaultPersistedState;
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

function readFromLocalStorage(): PersistedAskState | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<PersistedAskState>;
    return {
      mode: parsed.mode ?? defaultPersistedState.mode,
      isEvidencePanelOpen: parsed.isEvidencePanelOpen ?? defaultPersistedState.isEvidencePanelOpen,
      isRunPanelOpen: parsed.isRunPanelOpen ?? defaultPersistedState.isRunPanelOpen,
      latestRunId: parsed.latestRunId ?? defaultPersistedState.latestRunId,
    };
  } catch {
    return null;
  }
}

function readFromCookie(): PersistedAskState | null {
  try {
    const cookie = window.document.cookie
      .split("; ")
      .find((item) => item.startsWith(`${STORAGE_KEY}=`));
    if (!cookie) {
      return null;
    }
    const encoded = cookie.slice(STORAGE_KEY.length + 1);
    const parsed = JSON.parse(decodeURIComponent(encoded)) as Partial<PersistedAskState>;
    return {
      mode: parsed.mode ?? defaultPersistedState.mode,
      isEvidencePanelOpen: parsed.isEvidencePanelOpen ?? defaultPersistedState.isEvidencePanelOpen,
      isRunPanelOpen: parsed.isRunPanelOpen ?? defaultPersistedState.isRunPanelOpen,
      latestRunId: parsed.latestRunId ?? defaultPersistedState.latestRunId,
    };
  } catch {
    return null;
  }
}

function writePersistedState(state: PersistedAskState): void {
  memoryState = state;
  if (typeof window === "undefined") {
    return;
  }
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

export const useAskStore = create<AskStoreState>((set, get) => {
  const persisted = readPersistedState();
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(persisted));
  }

  return {
    ...persisted,
    setMode: (mode) => {
      set({ mode });
      writePersistedState({ ...get(), mode });
    },
    toggleEvidencePanel: () => {
      const nextValue = !get().isEvidencePanelOpen;
      set({ isEvidencePanelOpen: nextValue });
      writePersistedState({ ...get(), isEvidencePanelOpen: nextValue });
    },
    toggleRunPanel: () => {
      const nextValue = !get().isRunPanelOpen;
      set({ isRunPanelOpen: nextValue });
      writePersistedState({ ...get(), isRunPanelOpen: nextValue });
    },
    setLatestRunId: (latestRunId) => {
      set({ latestRunId });
      writePersistedState({ ...get(), latestRunId });
    },
  };
});
