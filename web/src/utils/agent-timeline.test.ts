import { describe, expect, it } from "vitest";

import { formatAgentTimeline } from "@/utils/agent-timeline";

describe("formatAgentTimeline", () => {
  it("adds duration labels", () => {
    const steps = [
      {
        name: "a",
        status: "completed",
        detail: {},
        started_at: "2026-01-01T00:00:00+00:00",
        finished_at: "2026-01-01T00:00:01+00:00",
      },
    ];
    const out = formatAgentTimeline(steps);
    expect(out[0].durationLabel).toContain("→");
  });

  it("handles empty steps", () => {
    expect(formatAgentTimeline(undefined)).toEqual([]);
  });
});
