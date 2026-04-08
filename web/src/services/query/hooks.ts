"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/services/api/endpoints";
import { queryKeys } from "@/services/query/keys";
import type {
  AgentQueryRequest,
  AgentRetryRequest,
  GraphRagRequest,
  KGStatsResponse,
  KGSubgraphParams,
  LearningPlanRequest,
  LearningSessionRequest,
  LearningSubmitRequest,
  MasteryMapRequest,
} from "@/types/api";

export function useGraphRagQuery(payload: GraphRagRequest | null) {
  return useMutation({
    mutationFn: (data: GraphRagRequest) => api.queryGraphRag(data),
    mutationKey: payload ? queryKeys.graphRag(payload.query) : ["graph-rag"],
  });
}

export function useSubgraphQuery(params: KGSubgraphParams, enabled = true) {
  return useQuery({
    queryKey: ["kg-subgraph", params],
    queryFn: () => api.getSubgraph(params),
    enabled,
  });
}

export function useKgStats(graphPath: string | undefined, enabled = true) {
  return useQuery<KGStatsResponse>({
    queryKey: ["kg-stats", graphPath ?? ""],
    queryFn: () => api.getKgStats(graphPath),
    enabled,
  });
}

export function useAgentQuery(payload: AgentQueryRequest | null) {
  return useMutation({
    mutationFn: (data: AgentQueryRequest) => api.queryAgent(data),
    mutationKey: payload ? queryKeys.agentQuery(payload.query) : ["agent-query"],
  });
}

export function useAgentRun(runId: string | null) {
  return useQuery({
    queryKey: runId ? queryKeys.agentRun(runId) : ["agent-run"],
    queryFn: () => api.getAgentRun(runId as string),
    enabled: Boolean(runId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "running" ? 2000 : false;
    },
  });
}

export function useRetryAgentRun(runId: string | null) {
  return useMutation({
    mutationFn: (payload: AgentRetryRequest) => api.retryAgentRun(runId as string, payload),
    mutationKey: runId ? ["agent-retry", runId] : ["agent-retry"],
  });
}

export function useLearningPlan(payload: LearningPlanRequest | null, enabled = true) {
  return useQuery({
    queryKey: payload
      ? queryKeys.learningPlan(payload.user_id, payload.graph_path)
      : ["learning-plan"],
    queryFn: () => api.getLearningPlan(payload as LearningPlanRequest),
    enabled: Boolean(payload) && enabled,
  });
}

export function useLearningSession() {
  return useMutation({
    mutationFn: (payload: LearningSessionRequest) => api.createLearningSession(payload),
    mutationKey: ["learning-session"],
  });
}

export function useLearningSubmit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: LearningSubmitRequest) => api.submitLearning(payload),
    mutationKey: ["learning-submit"],
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["learning-plan"] });
      queryClient.invalidateQueries({ queryKey: ["mastery-map"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.learningSubmit(variables.session_id) });
    },
  });
}

export function useMasteryMap(payload: MasteryMapRequest | null, enabled = true) {
  return useQuery({
    queryKey: payload
      ? queryKeys.masteryMap(payload.user_id, payload.graph_path)
      : ["mastery-map"],
    queryFn: () => api.getMasteryMap(payload as MasteryMapRequest),
    enabled: Boolean(payload) && enabled,
  });
}
