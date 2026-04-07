import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/services/api/endpoints";

/**
 * Integration-style test for issue #35: exercises client parsing and error paths
 * against mocked HTTP responses (no live server).
 */
describe("ask + learning flow (mocked HTTP)", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("covers agent success, invalid run 404, learning submit missing answers", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: { get: () => null },
      text: async () =>
        JSON.stringify({
          run_id: "run-abc",
          query: "q",
          status: "succeeded",
          created_at: "t1",
          updated_at: "t2",
          plan: { query_type: "x", strategy: "y", retrieval_mode: "hybrid", use_graph: true },
          steps: [
            {
              name: "planner_agent",
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
            confidence: 0.7,
            confidence_band: "medium",
          },
          fallback: null,
          error: null,
        }),
    });

    const run = await api.queryAgent({ query: "test" });
    expect(run.run_id).toBe("run-abc");
    expect(run.evaluation.confidence_band).toBe("medium");

    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: "Not Found",
      headers: { get: () => null },
      text: async () => JSON.stringify({ detail: "Agent run not found: bad" }),
    });

    await expect(api.getAgentRun("bad")).rejects.toMatchObject({
      status: 404,
      detail: "Agent run not found: bad",
    });

    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: "Bad Request",
      headers: { get: () => null },
      text: async () => JSON.stringify({ detail: "Missing answers for question_ids: q1" }),
    });

    await expect(
      api.submitLearning({
        session_id: "s1",
        user_id: "u1",
        answers: [],
      }),
    ).rejects.toMatchObject({
      status: 400,
      detail: expect.stringContaining("Missing answers"),
    });

    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: "Bad Request",
      headers: { get: () => null },
      text: async () => JSON.stringify({ detail: "Invalid question_types: badtype" }),
    });

    await expect(
      api.createLearningSession({
        user_id: "u1",
        graph_path: "/g.json",
        question_count: 1,
        // Intentionally invalid payload for error-path coverage (#35)
        question_types: ["concept", "badtype"] as unknown as ["concept", "judgement"],
      }),
    ).rejects.toMatchObject({
      status: 400,
    });
  });
});
