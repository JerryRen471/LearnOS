import type {
  AgentQueryRequest,
  AgentRetryRequest,
  AgentRunResponse,
  GraphRagRequest,
  GraphRagResponse,
  KGBuildRequest,
  KGBuildResponse,
  KGSubgraphParams,
  KGStatsResponse,
  LearningPlanRequest,
  LearningPlanResponse,
  LearningSessionRequest,
  LearningSessionResponse,
  LearningSubmitRequest,
  LearningSubmitResponse,
  MasteryMapRequest,
  MasteryMapResponse,
  SubgraphData,
} from "@/types/api";

import {
  agentRunResponseSchema,
  graphRagResponseSchema,
  kgBuildResponseSchema,
  learningPlanResponseSchema,
  learningSessionResponseSchema,
  learningSubmitResponseSchema,
  masteryMapResponseSchema,
  kgStatsResponseSchema,
  subgraphSchema,
} from "@/services/api/schemas";
import { request } from "@/services/api/client";

export function buildSubgraphQuery(params: KGSubgraphParams): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") {
      continue;
    }
    search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `/kg/subgraph?${query}` : "/kg/subgraph";
}

export const api = {
  buildKg: (payload: KGBuildRequest): Promise<KGBuildResponse> =>
    request({ method: "POST", path: "/kg/build", body: payload }, kgBuildResponseSchema),

  getSubgraph: (params: KGSubgraphParams): Promise<SubgraphData> =>
    request({ method: "GET", path: buildSubgraphQuery(params) }, subgraphSchema),

  getKgStats: (graphPath?: string): Promise<KGStatsResponse> => {
    const search = new URLSearchParams();
    if (graphPath) {
      search.set("graph_path", graphPath);
    }
    const query = search.toString();
    return request({ method: "GET", path: query ? `/kg/stats?${query}` : "/kg/stats" }, kgStatsResponseSchema);
  },

  queryGraphRag: (payload: GraphRagRequest): Promise<GraphRagResponse> =>
    request({ method: "POST", path: "/query/graph-rag", body: payload }, graphRagResponseSchema),

  queryAgent: (payload: AgentQueryRequest): Promise<AgentRunResponse> =>
    request({ method: "POST", path: "/agent/query", body: payload }, agentRunResponseSchema),

  getAgentRun: (runId: string): Promise<AgentRunResponse> =>
    request({ method: "GET", path: `/agent/runs/${runId}` }, agentRunResponseSchema),

  retryAgentRun: (runId: string, payload: AgentRetryRequest): Promise<AgentRunResponse> =>
    request({ method: "POST", path: `/agent/runs/${runId}/retry`, body: payload }, agentRunResponseSchema),

  // Placeholder routes for upcoming backend endpoints in Phase 4.
  getLearningPlan: (payload: LearningPlanRequest): Promise<LearningPlanResponse> =>
    request({ method: "POST", path: "/learning/plan", body: payload }, learningPlanResponseSchema),

  createLearningSession: (payload: LearningSessionRequest): Promise<LearningSessionResponse> =>
    request({ method: "POST", path: "/learning/session", body: payload }, learningSessionResponseSchema),

  submitLearning: (payload: LearningSubmitRequest): Promise<LearningSubmitResponse> =>
    request({ method: "POST", path: "/learning/submit", body: payload }, learningSubmitResponseSchema),

  getMasteryMap: (payload: MasteryMapRequest): Promise<MasteryMapResponse> =>
    request({ method: "POST", path: "/learning/mastery-map", body: payload }, masteryMapResponseSchema),
};
