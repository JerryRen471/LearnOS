import type { AgentStep } from "@/types/api";

export type TimelineEntry = AgentStep & {
  durationLabel: string;
};

/** Formats agent steps for readable timeline UI (issue #34). */
export function formatAgentTimeline(steps: AgentStep[] | undefined): TimelineEntry[] {
  return (steps ?? []).map((step) => ({
    ...step,
    durationLabel:
      step.started_at && step.finished_at
        ? `${step.started_at} → ${step.finished_at}`
        : "time unavailable",
  }));
}
