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

export const useAskStore = create<AskStoreState>((set) => ({
  mode: "graph-rag",
  isEvidencePanelOpen: true,
  isRunPanelOpen: true,
  latestRunId: null,
  setMode: (mode) => set({ mode }),
  toggleEvidencePanel: () => set((state) => ({ isEvidencePanelOpen: !state.isEvidencePanelOpen })),
  toggleRunPanel: () => set((state) => ({ isRunPanelOpen: !state.isRunPanelOpen })),
  setLatestRunId: (latestRunId) => set({ latestRunId }),
}));
