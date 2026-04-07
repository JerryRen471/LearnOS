import { describe, expect, it } from "vitest";

import {
  agentRunResponseSchema,
  learningPlanResponseSchema,
  learningSessionResponseSchema,
  masteryMapResponseSchema,
  subgraphSchema,
} from "@/services/api/schemas";

describe("schemas", () => {
  it("parses subgraph with node_id/name", () => {
    const raw = {
      nodes: [{ node_id: "c1", name: "Alpha", node_type: "Concept" }],
      edges: [{ source_id: "c1", target_id: "c2", edge_type: "related-to", evidence_chunk_id: "x" }],
    };
    const parsed = subgraphSchema.parse(raw);
    expect(parsed.nodes[0].node_id).toBe("c1");
    expect(parsed.edges[0].source_id).toBe("c1");
  });

  it("throws on invalid learning session question type", () => {
    const raw = {
      session_id: "s1",
      user_id: "u1",
      question_count: 1,
      question_types: ["concept"],
      questions: [{ question_id: "q1", prompt: "p", type: "bad" }],
    };
    expect(() => learningSessionResponseSchema.parse(raw)).toThrow();
  });

  it("parses learning plan with optional fields", () => {
    const raw = {
      user_id: "u1",
      generated_at: "2026-01-01T00:00:00+00:00",
      recommended_concepts: [
        {
          concept_id: "c1",
          concept_name: "RAG",
          mastery: 0.5,
          next_review_at: "2026-01-02T00:00:00+00:00",
          reason: "due",
          due: true,
        },
      ],
    };
    expect(() => learningPlanResponseSchema.parse(raw)).not.toThrow();
  });

  it("parses mastery map", () => {
    const raw = {
      summary: { concept_count: 2, average_mastery: 0.4, due_count: 1, record_count: 3 },
      concepts: [
        {
          concept_id: "c1",
          concept_name: "A",
          mastery: 0.3,
          due: true,
          last_review_at: null,
          next_review_at: "2026-01-01T00:00:00+00:00",
        },
      ],
    };
    const parsed = masteryMapResponseSchema.parse(raw);
    expect(parsed.summary.record_count).toBe(3);
  });

  it("parses agent run with steps", () => {
    const raw = {
      run_id: "run-1",
      query: "q",
      status: "succeeded",
      created_at: "t1",
      updated_at: "t2",
      plan: { query_type: "x", strategy: "y", retrieval_mode: "hybrid", use_graph: true },
      steps: [
        {
          name: "planner",
          status: "completed",
          detail: {},
          started_at: "a",
          finished_at: "b",
        },
      ],
      answer: "ans",
      text_evidence: [],
      graph_evidence: [],
      subgraph: { nodes: [], edges: [] },
      evaluation: {
        consistency_check: true,
        coverage_score: 0.5,
        confidence: 0.8,
        confidence_band: "high",
      },
    };
    expect(() => agentRunResponseSchema.parse(raw)).not.toThrow();
  });
});
