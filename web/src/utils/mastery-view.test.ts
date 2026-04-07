import { describe, expect, it } from "vitest";

import { applyMasteryView } from "@/utils/mastery-view";
import type { MasteryConcept } from "@/types/api";

const sample: MasteryConcept[] = [
  { concept_id: "a", concept_name: "A", mastery: 0.9, due: false, last_review_at: null, next_review_at: "t" },
  { concept_id: "b", concept_name: "B", mastery: 0.2, due: true, last_review_at: null, next_review_at: "t" },
  { concept_id: "c", concept_name: "C", mastery: 0.5, due: true, last_review_at: null, next_review_at: "t" },
];

describe("applyMasteryView", () => {
  it("filters due only", () => {
    const out = applyMasteryView(sample, { dueOnly: true, sortMasteryAsc: false });
    expect(out.every((c) => c.due)).toBe(true);
    expect(out).toHaveLength(2);
  });

  it("sorts mastery ascending", () => {
    const out = applyMasteryView(sample, { dueOnly: false, sortMasteryAsc: true });
    expect(out[0].mastery).toBeLessThanOrEqual(out[1].mastery);
  });
});
