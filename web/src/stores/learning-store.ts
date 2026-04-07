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

export const useLearningStore = create<LearningStoreState>((set) => ({
  sessionId: null,
  userId: "demo-user",
  graphPath: ".zhicore/graph.json",
  answerDrafts: {},
  setSessionMeta: ({ sessionId, userId, graphPath }) => set({ sessionId, userId, graphPath }),
  setAnswerDraft: (questionId, answer) =>
    set((state) => ({ answerDrafts: { ...state.answerDrafts, [questionId]: answer } })),
  clearDrafts: () => set({ answerDrafts: {} }),
}));
