export type ApiErrorCode =
  | "BAD_REQUEST"
  | "NOT_FOUND"
  | "TIMEOUT"
  | "NETWORK_ERROR"
  | "SERVER_ERROR"
  | "SCHEMA_VALIDATION_ERROR"
  | "UNKNOWN_ERROR";

export type ApiError = {
  code: ApiErrorCode;
  status: number;
  detail: string;
  message: string;
  requestId?: string;
  raw?: unknown;
};

export type TextEvidence = {
  index: number;
  chunk_id: string;
  source: string;
  score: number;
  excerpt: string;
};

export type GraphEvidence = {
  index: number;
  edge_type: string;
  source: string;
  target: string;
  evidence_chunk_id?: string | null;
};

export type SubgraphNode = {
  id: string;
  label?: string;
  type?: string;
  [key: string]: unknown;
};

export type SubgraphEdge = {
  source: string;
  target: string;
  type?: string;
  [key: string]: unknown;
};

export type SubgraphData = {
  nodes: SubgraphNode[];
  edges: SubgraphEdge[];
};

export type GraphRagRequest = {
  query: string;
  index_path?: string;
  graph_path?: string;
  top_k?: number;
  dense_k?: number;
  sparse_k?: number;
  rrf_k?: number;
  retrieval_mode?: "hybrid" | "dense" | "sparse";
  graph_hops?: number;
  embedding_provider?: string;
  embedding_model?: string;
  dense_backend?: string;
};

export type GraphRagResponse = {
  answer: string;
  text_evidence: TextEvidence[];
  graph_evidence: GraphEvidence[];
  subgraph: SubgraphData;
};

export type AgentQueryRequest = {
  query: string;
  index_path?: string;
  graph_path?: string;
  top_k?: number;
  dense_k?: number;
  sparse_k?: number;
  rrf_k?: number;
  embedding_provider?: string;
  embedding_model?: string;
  dense_backend?: string;
};

export type AgentRetryRequest = {
  query?: string;
  top_k?: number;
  dense_k?: number;
  sparse_k?: number;
  rrf_k?: number;
  embedding_provider?: string;
  embedding_model?: string;
  dense_backend?: string;
};

export type AgentStep = {
  name: string;
  status: string;
  detail: Record<string, unknown>;
  started_at: string;
  finished_at: string;
};

export type AgentPlan = {
  query_type: string;
  strategy: string;
  retrieval_mode: string;
  use_graph: boolean;
};

export type AgentFallback = {
  triggered: boolean;
  mode: string;
  reason: string;
};

export type AgentEvaluation = {
  consistency_check: boolean;
  coverage_score: number;
  confidence: number;
  confidence_band: string;
};

export type AgentRunResponse = {
  run_id: string;
  query: string;
  status: string;
  retry_of?: string | null;
  created_at: string;
  updated_at: string;
  plan: AgentPlan;
  steps: AgentStep[];
  answer: string;
  text_evidence: TextEvidence[];
  graph_evidence: GraphEvidence[];
  subgraph: SubgraphData;
  evaluation: AgentEvaluation;
  fallback?: AgentFallback | null;
  error?: string | null;
};

export type KGBuildRequest = {
  inputs: string[];
  graph_path?: string;
  index_path?: string;
  chunk_size?: number;
  overlap?: number;
  embedding_provider?: string;
  embedding_model?: string;
  dense_backend?: string;
  incremental?: boolean;
};

export type KGBuildResponse = {
  documents: number;
  chunks: number;
  nodes: number;
  edges: number;
};

export type KGSubgraphParams = {
  graph_path?: string;
  query?: string;
  concept?: string;
  hops?: number;
  max_nodes?: number;
};

// Backend endpoints for learning/mastery are planned in issues, keep DTOs now.
export type LearningPlanRequest = {
  user_id: string;
  graph_path: string;
  top_k?: number;
};

export type LearningConcept = {
  concept_id: string;
  concept_name: string;
  mastery: number;
  next_review_at?: string;
  reason?: string;
};

export type LearningPlanResponse = {
  user_id: string;
  recommended_concepts: LearningConcept[];
};

export type LearningSessionRequest = {
  user_id: string;
  graph_path: string;
  question_count: number;
  question_types: Array<"concept" | "judgement" | "cloze" | "derivation">;
};

export type LearningQuestion = {
  question_id: string;
  prompt: string;
  type: "concept" | "judgement" | "cloze" | "derivation";
  concept_id?: string;
};

export type LearningSessionResponse = {
  session_id: string;
  questions: LearningQuestion[];
};

export type LearningSubmitAnswer = {
  question_id: string;
  answer: string;
};

export type LearningSubmitRequest = {
  session_id: string;
  user_id: string;
  answers: LearningSubmitAnswer[];
};

export type LearningRecord = {
  question_id: string;
  score: number;
  error_type?: string;
  feedback?: string;
};

export type LearningSubmitResponse = {
  average_score: number;
  records: LearningRecord[];
  recommendation?: string;
};

export type MasteryMapRequest = {
  user_id: string;
  graph_path: string;
};

export type MasterySummary = {
  concept_count: number;
  average_mastery: number;
  due_count: number;
  record_count: number;
};

export type MasteryConcept = {
  concept_id: string;
  concept_name: string;
  mastery: number;
  due: boolean;
  next_review_at?: string;
};

export type MasteryMapResponse = {
  summary: MasterySummary;
  concepts: MasteryConcept[];
};
