export const queryKeys = {
  graphRag: (query: string) => ["graph-rag", query] as const,
  agentQuery: (query: string) => ["agent-query", query] as const,
  agentRun: (runId: string) => ["agent-run", runId] as const,
  learningPlan: (userId: string, graphPath: string) => ["learning-plan", userId, graphPath] as const,
  learningSession: (sessionId: string) => ["learning-session", sessionId] as const,
  learningSubmit: (sessionId: string) => ["learning-submit", sessionId] as const,
  masteryMap: (userId: string, graphPath: string) => ["mastery-map", userId, graphPath] as const,
};
