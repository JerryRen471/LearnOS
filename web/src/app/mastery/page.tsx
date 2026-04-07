"use client";

import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useMasteryMap } from "@/services/query/hooks";
import { useLearningStore } from "@/stores/learning-store";

export default function MasteryPage() {
  const userId = useLearningStore((state) => state.userId);
  const graphPath = useLearningStore((state) => state.graphPath);
  const masteryQuery = useMasteryMap({ user_id: userId, graph_path: graphPath });

  return (
    <section className="page">
      <header className="page-header">
        <h2>Mastery</h2>
        <p>Summary cards and concept mastery details.</p>
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

          <section className="panel">
            <h3>Concepts</h3>
            {!masteryQuery.data.concepts.length ? (
              <EmptyState message="No concepts available." />
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
                    {masteryQuery.data.concepts.map((concept) => (
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
