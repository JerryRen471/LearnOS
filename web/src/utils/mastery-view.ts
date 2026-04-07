import type { MasteryConcept } from "@/types/api";

export type MasteryViewOptions = {
  dueOnly: boolean;
  sortMasteryAsc: boolean;
};

/** Client-side view over mastery concepts (#29): filter due-only, sort by mastery ascending. */
export function applyMasteryView(concepts: MasteryConcept[], options: MasteryViewOptions): MasteryConcept[] {
  let rows = [...concepts];
  if (options.dueOnly) {
    rows = rows.filter((c) => c.due);
  }
  if (options.sortMasteryAsc) {
    rows.sort((a, b) => {
      if (a.mastery !== b.mastery) {
        return a.mastery - b.mastery;
      }
      return a.concept_name.localeCompare(b.concept_name);
    });
  }
  return rows;
}
