import { afterEach, describe, expect, it, vi } from "vitest";

import { request } from "@/services/api/client";
import { subgraphSchema } from "@/services/api/schemas";

describe("request", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("maps 404 detail from JSON body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: "Not Found",
        headers: { get: () => null },
        text: async () => JSON.stringify({ detail: "Agent run not found" }),
      }),
    );

    await expect(request({ path: "/agent/runs/x" })).rejects.toMatchObject({
      status: 404,
      detail: "Agent run not found",
    });
  });

  it("parses success with schema", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        headers: { get: () => null },
        text: async () => JSON.stringify({ nodes: [], edges: [] }),
      }),
    );

    const data = await request({ path: "/kg/subgraph" }, subgraphSchema);
    expect(data.nodes).toEqual([]);
  });
});
