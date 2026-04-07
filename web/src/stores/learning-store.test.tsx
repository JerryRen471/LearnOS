import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useLearningStore } from "@/stores/learning-store";

function DraftReader({ questionId }: { questionId: string }) {
  const draft = useLearningStore((s) => s.answerDrafts[questionId] ?? "");
  return <span data-testid="draft">{draft}</span>;
}

describe("learning store", () => {
  it("updates answer draft", () => {
    const { setAnswerDraft } = useLearningStore.getState();
    setAnswerDraft("q1", "hello");
    render(<DraftReader questionId="q1" />);
    expect(screen.getByTestId("draft").textContent).toBe("hello");
  });
});
