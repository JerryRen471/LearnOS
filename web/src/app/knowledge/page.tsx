"use client";

import { FormEvent, useCallback, useState } from "react";
import { useRouter } from "next/navigation";

import { GraphCanvas } from "@/components/knowledge/graph-canvas";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useLearningStore } from "@/stores/learning-store";
import { useSubgraphMutation } from "@/services/query/hooks";
import type { SubgraphData, SubgraphNode } from "@/types/api";

function nodeId(n: SubgraphNode): string {
  return (n.node_id as string | undefined) ?? (n.id as string) ?? "";
}

export default function KnowledgePage() {
  const router = useRouter();
  const graphPath = useLearningStore((s) => s.graphPath);

  const [query, setQuery] = useState("");
  const [concept, setConcept] = useState("");
  const [hops, setHops] = useState(1);
  const [maxNodes, setMaxNodes] = useState(80);
  const [subgraph, setSubgraph] = useState<SubgraphData | null>(null);
  const [selected, setSelected] = useState<{ id: string; name: string } | null>(null);

  const mutation = useSubgraphMutation();

  const onSelectNode = useCallback((id: string, name: string) => {
    setSelected({ id, name });
  }, []);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setSelected(null);
    mutation.mutate(
      {
        graph_path: graphPath,
        query: query.trim() || undefined,
        concept: concept.trim() || undefined,
        hops,
        max_nodes: maxNodes,
      },
      {
        onSuccess: (data) => {
          setSubgraph(data);
        },
      },
    );
  };

  const selectedNodePayload = subgraph?.nodes.find((n) => nodeId(n) === selected?.id);

  return (
    <section className="page">
      <header className="page-header">
        <h2>Knowledge</h2>
        <p>Query subgraph, explore the graph, jump to Ask or Learning.</p>
      </header>

      <form className="panel form-panel" onSubmit={onSubmit}>
        <p className="hint">graph_path: {graphPath}</p>
        <label htmlFor="kg-query">query</label>
        <input id="kg-query" value={query} onChange={(ev) => setQuery(ev.target.value)} placeholder="optional" />
        <label htmlFor="kg-concept">concept</label>
        <input id="kg-concept" value={concept} onChange={(ev) => setConcept(ev.target.value)} placeholder="optional" />
        <div className="inline-actions">
          <label htmlFor="kg-hops">hops</label>
          <input
            id="kg-hops"
            type="number"
            min={0}
            max={2}
            value={hops}
            onChange={(ev) => setHops(Number(ev.target.value) || 0)}
          />
          <label htmlFor="kg-max">max_nodes</label>
          <input
            id="kg-max"
            type="number"
            min={1}
            max={300}
            value={maxNodes}
            onChange={(ev) => setMaxNodes(Math.max(1, Number(ev.target.value) || 1))}
          />
          <button type="submit" disabled={mutation.isPending}>
            Fetch subgraph
          </button>
        </div>
      </form>

      {mutation.isPending && <LoadingState message="Loading subgraph..." />}
      {mutation.error && (
        <ErrorState message={(mutation.error as { detail?: string }).detail ?? "Subgraph request failed."} />
      )}

      {!subgraph && !mutation.isPending && (
        <EmptyState message="Submit the form to load nodes and edges from the API." />
      )}

      {subgraph && (
        <div className="knowledge-layout">
          <div className="panel graph-panel">
            <h3>Graph</h3>
            {!subgraph.nodes.length ? (
              <EmptyState message="No nodes in this subgraph." />
            ) : (
              <GraphCanvas data={subgraph} onSelectNode={onSelectNode} />
            )}
          </div>
          <aside className="panel node-detail-panel">
            <h3>Node detail</h3>
            {!selected ? (
              <p className="hint">Click a node in the graph.</p>
            ) : (
              <>
                <p>
                  <strong>{selected.name}</strong>
                </p>
                <p className="hint">id: {selected.id}</p>
                {selectedNodePayload && (
                  <pre className="node-json">{JSON.stringify(selectedNodePayload, null, 2)}</pre>
                )}
                <div className="form-actions">
                  <button
                    type="button"
                    onClick={() =>
                      router.push(`/ask?query=${encodeURIComponent(`Explain: ${selected.name}`)}`)
                    }
                  >
                    Open in Ask
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      router.push(`/learning?concept=${encodeURIComponent(selected.name)}`)
                    }
                  >
                    Open in Learning
                  </button>
                </div>
              </>
            )}
          </aside>
        </div>
      )}
    </section>
  );
}
