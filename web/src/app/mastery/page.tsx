"use client";

import { useMemo, useState } from "react";

import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { applyMasteryView } from "@/utils/mastery-view";
import { useMasteryMap } from "@/services/query/hooks";
import { useLearningStore } from "@/stores/learning-store";

export default function MasteryPage() {
  const userId = useLearningStore((state) => state.userId);
  const graphPath = useLearningStore((state) => state.graphPath);
  const masteryQuery = useMasteryMap({ user_id: userId, graph_path: graphPath });

  const [dueOnly, setDueOnly] = useState(false);
  const [sortMasteryAsc, setSortMasteryAsc] = useState(true);

  const filteredConcepts = useMemo(() => {
    if (!masteryQuery.data) {
      return [];
    }
    return applyMasteryView(masteryQuery.data.concepts, { dueOnly, sortMasteryAsc });
  }, [masteryQuery.data, dueOnly, sortMasteryAsc]);

  const viewSummary = useMemo(() => {
    if (!filteredConcepts.length) {
      return {
        concept_count: 0,
        average_mastery: 0,
        due_count: 0,
      };
    }
    const sum = filteredConcepts.reduce((acc, c) => acc + c.mastery, 0);
    const due = filteredConcepts.filter((c) => c.due).length;
    return {
      concept_count: filteredConcepts.length,
      average_mastery: Math.round((sum / filteredConcepts.length) * 1000) / 1000,
      due_count: due,
    };
  }, [filteredConcepts]);

  return (
    <section className="page">
      <header className="page-header">
        <h2>Mastery</h2>
        <p>Summary cards, filters, and concept table.</p>
      </header>

      {masteryQuery.isLoading && <LoadingState message="Loading mastery map..." />}
      {masteryQuery.error && (
        <ErrorState message={(masteryQuery.error as { detail?: string }).detail ?? "Mastery request failed."} />
      )}

      {masteryQuery.data && (
        <>
          <section className="summary-grid">
            <article className="panel">
              <h3>concept_count</h3>
              <p>{masteryQuery.data.summary.concept_count}</p>
            </article>
            <article className="panel">
              <h3>average_mastery</h3>
              <p>{masteryQuery.data.summary.average_mastery.toFixed(3)}</p>
            </article>
            <article className="panel">
              <h3>due_count</h3>
              <p>{masteryQuery.data.summary.due_count}</p>
            </article>
            <article className="panel">
              <h3>record_count</h3>
              <p>{masteryQuery.data.summary.record_count}</p>
            </article>
          </section>

          <section className="panel mastery-filters">
            <h3>Table filters</h3>
            <label className="checkbox-inline">
              <input type="checkbox" checked={dueOnly} onChange={(e) => setDueOnly(e.target.checked)} />
              Due only
            </label>
            <label className="checkbox-inline">
              <input type="checkbox" checked={sortMasteryAsc} onChange={(e) => setSortMasteryAsc(e.target.checked)} />
              Sort mastery ascending
            </label>
            <p className="hint">
              Visible rows: {viewSummary.concept_count} | avg mastery: {viewSummary.average_mastery.toFixed(3)} | due
              in view: {viewSummary.due_count}
              {dueOnly && (
                <>
                  {" "}
                  (API due_count: {masteryQuery.data.summary.due_count})
                </>
              )}
            </p>
          </section>

          <section className="panel">
            <h3>Concepts</h3>
            {!filteredConcepts.length ? (
              <EmptyState message="No concepts match the current filters." />
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>concept_id</th>
                      <th>concept_name</th>
                      <th>mastery</th>
                      <th>due</th>
                      <th>last_review_at</th>
                      <th>next_review_at</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredConcepts.map((concept) => (
                      <tr key={concept.concept_id}>
                        <td>{concept.concept_id}</td>
                        <td>{concept.concept_name}</td>
                        <td>{concept.mastery.toFixed(3)}</td>
                        <td>{concept.due ? "yes" : "no"}</td>
                        <td>{concept.last_review_at ?? "-"}</td>
                        <td>{concept.next_review_at ?? "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </section>
  );
}
