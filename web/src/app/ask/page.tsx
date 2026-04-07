"use client";

import { FormEvent, useMemo, useState } from "react";

import { EmptyState, ErrorState, LoadingState, SuccessState } from "@/components/ui/states";
import { useAgentQuery, useAgentRun, useGraphRagQuery } from "@/services/query/hooks";
import { useAskStore } from "@/stores/ask-store";

function AskModeSwitch() {
  const mode = useAskStore((state) => state.mode);
  const setMode = useAskStore((state) => state.setMode);

  return (
    <div className="mode-switch" role="tablist" aria-label="ask mode switch">
      <button
        type="button"
        className={mode === "graph-rag" ? "active" : ""}
        onClick={() => setMode("graph-rag")}
      >
        Graph RAG
      </button>
      <button type="button" className={mode === "agent" ? "active" : ""} onClick={() => setMode("agent")}>
        Agent
      </button>
    </div>
  );
}

export default function AskPage() {
  const mode = useAskStore((state) => state.mode);
  const isEvidencePanelOpen = useAskStore((state) => state.isEvidencePanelOpen);
  const isRunPanelOpen = useAskStore((state) => state.isRunPanelOpen);
  const latestRunId = useAskStore((state) => state.latestRunId);
  const toggleEvidencePanel = useAskStore((state) => state.toggleEvidencePanel);
  const toggleRunPanel = useAskStore((state) => state.toggleRunPanel);
  const setLatestRunId = useAskStore((state) => state.setLatestRunId);

  const [query, setQuery] = useState("FastAPI 和 LearnOS 的关系是什么？");
  const [submittedQuery, setSubmittedQuery] = useState<string>("");

  const graphRagMutation = useGraphRagQuery(submittedQuery ? { query: submittedQuery } : null);
  const agentMutation = useAgentQuery(submittedQuery ? { query: submittedQuery } : null);
  const agentRunQuery = useAgentRun(latestRunId);

  const activeError = (graphRagMutation.error ?? agentMutation.error) as
    | { detail?: string; message?: string; code?: string }
    | undefined;

  const activeResult = mode === "graph-rag" ? graphRagMutation.data : agentMutation.data;

  const evidenceCount = useMemo(() => {
    if (!activeResult) {
      return 0;
    }
    return activeResult.text_evidence.length + activeResult.graph_evidence.length;
  }, [activeResult]);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      return;
    }
    setSubmittedQuery(trimmedQuery);

    if (mode === "graph-rag") {
      graphRagMutation.mutate({ query: trimmedQuery });
      return;
    }

    agentMutation.mutate(
      { query: trimmedQuery },
      {
        onSuccess: (data) => {
          setLatestRunId(data.run_id);
        },
      },
    );
  };

  return (
    <section className="page">
      <header className="page-header">
        <h2>Ask</h2>
        <p>Query by Graph RAG or Agent workflow.</p>
      </header>

      <AskModeSwitch />

      <form onSubmit={submit} className="panel form-panel">
        <label htmlFor="ask-query" className="field-label">
          Query
        </label>
        <textarea
          id="ask-query"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          rows={3}
          placeholder="Ask a question..."
        />
        <div className="form-actions">
          <button type="submit">Run</button>
          <button type="button" onClick={toggleEvidencePanel}>
            {isEvidencePanelOpen ? "Hide evidence" : "Show evidence"}
          </button>
          <button type="button" onClick={toggleRunPanel}>
            {isRunPanelOpen ? "Hide run panel" : "Show run panel"}
          </button>
        </div>
      </form>

      {(graphRagMutation.isPending || agentMutation.isPending || agentRunQuery.isFetching) && (
        <LoadingState message="Query is running..." />
      )}

      {activeError && (
        <ErrorState
          message={activeError.detail ?? activeError.message ?? "Unknown error when requesting backend."}
        />
      )}

      {!activeResult && !graphRagMutation.isPending && !agentMutation.isPending && (
        <EmptyState message="Submit your query to view answer and evidence." />
      )}

      {activeResult && (
        <div className="panel-stack">
          <section className="panel">
            <h3>Answer</h3>
            <p>{activeResult.answer}</p>
            <SuccessState message={`Answer returned with ${evidenceCount} evidence items.`} />
          </section>

          {isEvidencePanelOpen && (
            <section className="panel">
              <h3>Evidence</h3>
              <ul>
                {activeResult.text_evidence.map((item) => (
                  <li key={`text-${item.index}`}>
                    <strong>Text #{item.index}</strong> ({item.source}) - score {item.score.toFixed(3)}
                  </li>
                ))}
                {activeResult.graph_evidence.map((item) => (
                  <li key={`graph-${item.index}`}>
                    <strong>Graph #{item.index}</strong> {item.source} -[{item.edge_type}]-&gt; {item.target}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {mode === "agent" && isRunPanelOpen && latestRunId && (
            <section className="panel">
              <h3>Latest Run: {latestRunId}</h3>
              <p>Status: {agentRunQuery.data?.status ?? "loading"}</p>
              <ul>
                {(agentRunQuery.data?.steps ?? []).map((step) => (
                  <li key={`${step.name}-${step.started_at}`}>
                    <strong>{step.name}</strong>: {step.status}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </section>
  );
}
