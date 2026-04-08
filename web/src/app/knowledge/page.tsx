"use client";

import { FormEvent, useMemo, useState } from "react";

import { EmptyState, ErrorState, LoadingState, SuccessState } from "@/components/ui/states";
import { useGraphRagQuery, useKgStats, useSubgraphQuery } from "@/services/query/hooks";

export default function KnowledgePage() {
  const [term, setTerm] = useState("线性空间");
  const [submitted, setSubmitted] = useState<string>("");
  const [subgraphMode, setSubgraphMode] = useState<"query" | "concept">("concept");
  const graphPath = ".zhicore/graph.json";
  const indexPath = ".zhicore/index.json";

  const statsQuery = useKgStats(graphPath, true);
  const subgraphParams = useMemo(() => {
    const trimmed = submitted.trim();
    if (!trimmed) {
      return { graph_path: graphPath, hops: 1, max_nodes: 80 };
    }
    return subgraphMode === "concept"
      ? { graph_path: graphPath, concept: trimmed, hops: 1, max_nodes: 80 }
      : { graph_path: graphPath, query: trimmed, hops: 1, max_nodes: 80 };
  }, [submitted, subgraphMode, graphPath]);
  const subgraphQuery = useSubgraphQuery(subgraphParams, Boolean(submitted));

  const graphRagMutation = useGraphRagQuery(submitted ? { query: submitted, graph_path: graphPath, index_path: indexPath } : null);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = term.trim();
    if (!trimmed) {
      return;
    }
    setSubmitted(trimmed);
  };

  const nodes = subgraphQuery.data?.nodes ?? [];
  const edges = subgraphQuery.data?.edges ?? [];
  const relatedRatio = statsQuery.data?.related_to_ratio;

  return (
    <section className="page">
      <header className="page-header">
        <h2>Knowledge</h2>
        <p>Explore KG stats, query subgraphs, and run Graph-RAG against the same term.</p>
      </header>

      <section className="panel form-panel">
        <form onSubmit={submit}>
          <label htmlFor="kg-term" className="field-label">
            Query / Concept
          </label>
          <textarea
            id="kg-term"
            value={term}
            onChange={(event) => setTerm(event.target.value)}
            rows={2}
            placeholder="e.g. 线性空间 / 群论 / representation"
          />
          <div className="form-actions">
            <button type="submit">Load subgraph</button>
            <button
              type="button"
              onClick={() => setSubgraphMode((value) => (value === "concept" ? "query" : "concept"))}
            >
              Mode: {subgraphMode}
            </button>
            <button
              type="button"
              onClick={() => {
                const trimmed = term.trim();
                if (!trimmed) {
                  return;
                }
                setSubmitted(trimmed);
                graphRagMutation.mutate({ query: trimmed });
              }}
            >
              Run Graph-RAG
            </button>
          </div>
        </form>
      </section>

      {(statsQuery.isFetching || subgraphQuery.isFetching || graphRagMutation.isPending) && (
        <LoadingState message="Loading knowledge graph data..." />
      )}

      {(statsQuery.error || subgraphQuery.error || graphRagMutation.error) && (
        <ErrorState
          message={
            (statsQuery.error as { detail?: string })?.detail ??
            (subgraphQuery.error as { detail?: string })?.detail ??
            (graphRagMutation.error as { detail?: string })?.detail ??
            "Unknown error."
          }
        />
      )}

      {statsQuery.data && (
        <section className="panel">
          <h3>KG Stats</h3>
          <ul>
            <li>
              <strong>Nodes</strong>: {statsQuery.data.nodes}
            </li>
            <li>
              <strong>Edges</strong>: {statsQuery.data.edges}
            </li>
            <li>
              <strong>related-to ratio</strong>: {typeof relatedRatio === "number" ? relatedRatio.toFixed(3) : "n/a"}
            </li>
          </ul>
          <details>
            <summary>Edge types</summary>
            <pre>{JSON.stringify(statsQuery.data.edge_types, null, 2)}</pre>
          </details>
          <details>
            <summary>Top hubs</summary>
            <pre>{JSON.stringify(statsQuery.data.top_hubs, null, 2)}</pre>
          </details>
        </section>
      )}

      {!submitted && <EmptyState message="Enter a concept or query to load a subgraph." />}

      {submitted && subgraphQuery.data && (
        <div className="panel-stack">
          <section className="panel">
            <h3>Subgraph</h3>
            <p>
              Term: <strong>{submitted}</strong> · Nodes: {nodes.length} · Edges: {edges.length}
            </p>
            {nodes.length === 0 && <EmptyState message="No nodes found. Try another term (e.g. 线性空间 / 满射 / 单同态)." />}
            {nodes.length > 0 && (
              <>
                <details open>
                  <summary>Nodes</summary>
                  <ul>
                    {nodes.slice(0, 40).map((node) => (
                      <li key={node.id}>
                        <strong>{node.label ?? node.id}</strong> {node.type ? `(${node.type})` : null}
                      </li>
                    ))}
                  </ul>
                </details>
                <details>
                  <summary>Edges</summary>
                  <ul>
                    {edges.slice(0, 80).map((edge, idx) => (
                      <li key={`${edge.source}-${edge.target}-${idx}`}>
                        {edge.source} -[{edge.type ?? "related"}]-&gt; {edge.target}
                      </li>
                    ))}
                  </ul>
                </details>
              </>
            )}
          </section>

          {graphRagMutation.data && (
            <section className="panel">
              <h3>Graph-RAG Answer</h3>
              <p>{graphRagMutation.data.answer}</p>
              <SuccessState message={`Answer returned with ${graphRagMutation.data.text_evidence.length + graphRagMutation.data.graph_evidence.length} evidence items.`} />
              <details>
                <summary>Evidence</summary>
                <ul>
                  {graphRagMutation.data.text_evidence.map((item) => (
                    <li key={`text-${item.index}`}>
                      <strong>Text #{item.index}</strong> ({item.source}) score {item.score.toFixed(3)}
                    </li>
                  ))}
                  {graphRagMutation.data.graph_evidence.map((item) => (
                    <li key={`graph-${item.index}`}>
                      <strong>Graph #{item.index}</strong> {item.source} -[{item.edge_type}]-&gt; {item.target}
                    </li>
                  ))}
                </ul>
              </details>
            </section>
          )}
        </div>
      )}
    </section>
  );
}
