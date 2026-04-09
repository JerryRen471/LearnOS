import { z } from "zod";

const subgraphNodeSchema = z.object({
  node_id: z.string(),
  node_type: z.string(),
  name: z.string(),
  description: z.string().optional(),
  metadata: z.record(z.string(), z.string()).optional(),
}).passthrough();

const subgraphEdgeSchema = z.object({
  edge_id: z.string(),
  source_id: z.string(),
  target_id: z.string(),
  edge_type: z.string(),
  evidence_chunk_id: z.string(),
  metadata: z.record(z.string(), z.string()).optional(),
}).passthrough();

export const subgraphSchema = z.object({
  nodes: z.array(subgraphNodeSchema),
  edges: z.array(subgraphEdgeSchema),
});

export const textEvidenceSchema = z.object({
  index: z.number(),
  chunk_id: z.string(),
  source: z.string(),
  score: z.number(),
  excerpt: z.string(),
});

export const graphEvidenceSchema = z.object({
  index: z.number(),
  edge_type: z.string(),
  source: z.string(),
  target: z.string(),
  evidence_chunk_id: z.string().nullable().optional(),
});

export const graphRagResponseSchema = z.object({
  answer: z.string(),
  text_evidence: z.array(textEvidenceSchema),
  graph_evidence: z.array(graphEvidenceSchema),
  subgraph: subgraphSchema,
});

export const agentStepSchema = z.object({
  name: z.string(),
  status: z.string(),
  detail: z.record(z.string(), z.unknown()),
  started_at: z.string(),
  finished_at: z.string(),
});

export const agentPlanSchema = z.object({
  query_type: z.string(),
  strategy: z.string(),
  retrieval_mode: z.string(),
  use_graph: z.boolean(),
});

export const agentEvaluationSchema = z.object({
  consistency_check: z.boolean(),
  coverage_score: z.number(),
  confidence: z.number(),
  confidence_band: z.string(),
});

export const agentFallbackSchema = z.object({
  triggered: z.boolean(),
  mode: z.string(),
  reason: z.string(),
});

export const agentRunResponseSchema = z.object({
  run_id: z.string(),
  query: z.string(),
  status: z.string(),
  retry_of: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
  plan: agentPlanSchema,
  steps: z.array(agentStepSchema),
  answer: z.string(),
  text_evidence: z.array(textEvidenceSchema),
  graph_evidence: z.array(graphEvidenceSchema),
  subgraph: subgraphSchema,
  evaluation: agentEvaluationSchema,
  fallback: agentFallbackSchema.nullable().optional(),
  error: z.string().nullable().optional(),
});

export const kgBuildResponseSchema = z.object({
  documents: z.number(),
  chunks: z.number(),
  nodes: z.number(),
  edges: z.number(),
});

export const kgStatsHubSchema = z.object({
  node_id: z.string(),
  name: z.string(),
  node_type: z.string(),
  degree: z.number(),
});

export const kgStatsResponseSchema = z.object({
  nodes: z.number(),
  edges: z.number(),
  edge_types: z.record(z.string(), z.number()),
  related_to_ratio: z.number(),
  top_hubs: z.array(kgStatsHubSchema),
});

export const learningConceptSchema = z.object({
  concept_id: z.string(),
  concept_name: z.string(),
  mastery: z.number(),
  next_review_at: z.string().optional(),
  reason: z.string().optional(),
});

export const learningPlanResponseSchema = z.object({
  user_id: z.string(),
  recommended_concepts: z.array(learningConceptSchema),
});

export const learningQuestionSchema = z.object({
  question_id: z.string(),
  prompt: z.string(),
  type: z.enum(["concept", "judgement", "cloze", "derivation"]),
  concept_id: z.string().optional(),
});

export const learningSessionResponseSchema = z.object({
  session_id: z.string(),
  questions: z.array(learningQuestionSchema),
});

export const learningRecordSchema = z.object({
  question_id: z.string(),
  score: z.number(),
  error_type: z.string().optional(),
  feedback: z.string().optional(),
});

export const learningSubmitResponseSchema = z.object({
  average_score: z.number(),
  records: z.array(learningRecordSchema),
  recommendation: z.string().optional(),
});

export const masterySummarySchema = z.object({
  concept_count: z.number(),
  average_mastery: z.number(),
  due_count: z.number(),
  record_count: z.number(),
});

export const masteryConceptSchema = z.object({
  concept_id: z.string(),
  concept_name: z.string(),
  mastery: z.number(),
  due: z.boolean(),
  next_review_at: z.string().optional(),
});

export const masteryMapResponseSchema = z.object({
  summary: masterySummarySchema,
  concepts: z.array(masteryConceptSchema),
});
