"use client";

import { FormEvent, Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { EmptyState, ErrorState, LoadingState, SuccessState } from "@/components/ui/states";
import { formatAgentTimeline } from "@/utils/agent-timeline";
import { showToast } from "@/utils/toast-store";
import { useAgentQuery, useAgentRun, useGraphRagQuery, useRetryAgentRun } from "@/services/query/hooks";
import { useAskStore } from "@/stores/ask-store";
import type { AgentRunResponse, GraphRagResponse } from "@/types/api";

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

function confidencePercent(confidence: number | undefined): number {
  if (confidence === undefined || Number.isNaN(confidence)) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round(confidence * 100)));
}

function AskPageContent() {
  const searchParams = useSearchParams();
  const mode = useAskStore((state) => state.mode);
  const isEvidencePanelOpen = useAskStore((state) => state.isEvidencePanelOpen);
  const isRunPanelOpen = useAskStore((state) => state.isRunPanelOpen);
  const latestRunId = useAskStore((state) => state.latestRunId);
  const toggleEvidencePanel = useAskStore((state) => state.toggleEvidencePanel);
  const toggleRunPanel = useAskStore((state) => state.toggleRunPanel);
  const setLatestRunId = useAskStore((state) => state.setLatestRunId);

  const [query, setQuery] = useState("FastAPI 和 LearnOS 的关系是什么？");
  const [manualRunId, setManualRunId] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [formError, setFormError] = useState("");

  const graphRagMutation = useGraphRagQuery(null);
  const agentMutation = useAgentQuery(null);
  const retryMutation = useRetryAgentRun(latestRunId);
  const agentRunQuery = useAgentRun(latestRunId);

  const activeRun: AgentRunResponse | undefined =
    agentRunQuery.data ?? retryMutation.data ?? agentMutation.data;
  const activeGraph: GraphRagResponse | undefined = graphRagMutation.data;

  const activeError = (graphRagMutation.error ?? agentMutation.error ?? retryMutation.error ?? agentRunQuery.error) as
    | { detail?: string; message?: string; code?: string }
    | undefined;

  const fallbackTriggered = Boolean(
    activeRun?.fallback?.triggered ||
      activeRun?.steps.some((step) => step.status === "failed_with_fallback"),
  );

  const stepTimeline = useMemo(() => formatAgentTimeline(activeRun?.steps), [activeRun?.steps]);

  // Sync textarea from URL when navigating from Knowledge (#32).
  /* eslint-disable react-hooks/set-state-in-effect -- URL searchParams drive initial query text */
  useEffect(() => {
    const q = searchParams.get("query");
    const c = searchParams.get("concept");
    if (q) {
      setQuery(q);
    } else if (c) {
      setQuery(`Explain the concept: ${c}`);
    }
  }, [searchParams]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) {
      setFormError("Please enter a query before submitting.");
      showToast({ title: "Validation", detail: "Query cannot be empty.", variant: "info" });
      return;
    }
    setFormError("");
    setSubmitted(true);

    if (mode === "graph-rag") {
      graphRagMutation.mutate({ query: trimmed, retrieval_mode: "hybrid", graph_hops: 1 });
      return;
    }

    agentMutation.mutate(
      { query: trimmed },
      {
        onSuccess: (data) => {
          setLatestRunId(data.run_id);
          setManualRunId(data.run_id);
        },
      },
    );
  };

  const onRetry = () => {
    if (!latestRunId) {
      return;
    }
    retryMutation.mutate(
      { query: query.trim() || undefined },
      {
        onSuccess: (data) => {
          setLatestRunId(data.run_id);
          setManualRunId(data.run_id);
        },
      },
    );
  };

  const onLoadRun = () => {
    const next = manualRunId.trim();
    if (!next) {
      return;
    }
    setLatestRunId(next);
  };

  const isLoading =
    graphRagMutation.isPending ||
    agentMutation.isPending ||
    retryMutation.isPending ||
    agentRunQuery.isFetching;

  return (
    <section className="page">
      <header className="page-header">
        <h2>Ask</h2>
        <p>Graph-RAG / Agent mode with run timeline, retry and fallback UX.</p>
      </header>

      <AskModeSwitch />

      <form onSubmit={onSubmit} className="panel form-panel">
        <label htmlFor="ask-query" className="field-label">
          Query
        </label>
        <textarea
          id="ask-query"
          value={query}
          onChange={(event) => {
            setFormError("");
            setQuery(event.target.value);
          }}
          rows={3}
          placeholder="Ask a question..."
          aria-invalid={Boolean(formError)}
        />
        {formError ? <p className="form-field-error">{formError}</p> : null}
        <div className="form-actions">
          <button type="submit">Submit</button>
          <button type="button" onClick={toggleEvidencePanel}>
            {isEvidencePanelOpen ? "Hide evidence" : "Show evidence"}
          </button>
          <button type="button" onClick={toggleRunPanel}>
            {isRunPanelOpen ? "Hide run panel" : "Show run panel"}
          </button>
        </div>
      </form>

      {mode === "agent" && (
        <section className="panel">
          <h3>Run Lookup / Retry</h3>
          <div className="inline-actions">
            <input
              value={manualRunId}
              onChange={(event) => setManualRunId(event.target.value)}
              placeholder="run_id"
            />
            <button type="button" onClick={onLoadRun}>
              Load Run
            </button>
            <button type="button" onClick={onRetry} disabled={!latestRunId || retryMutation.isPending}>
              Retry Run
            </button>
          </div>
          {activeRun?.retry_of ? (
            <p className="hint">
              latest run_id: <strong>{activeRun.run_id}</strong> (retry_of: {activeRun.retry_of})
            </p>
          ) : (
            latestRunId && (
              <p className="hint">
                latest run_id: <strong>{latestRunId}</strong>
              </p>
            )
          )}
        </section>
      )}

      {isLoading && <LoadingState message="Running query..." />}

      {!submitted && <EmptyState message="Select mode and submit a query." />}

      {activeError && (
        <ErrorState message={activeError.detail ?? activeError.message ?? "Request failed."} />
      )}

      {fallbackTriggered && (
        <section className="panel warning-banner">
          <h3>Fallback Activated</h3>
          <p>
            Agent run triggered fallback to RAG mode.
            {activeRun?.fallback?.reason ? ` reason: ${activeRun.fallback.reason}` : ""}
          </p>
        </section>
      )}

      {mode === "graph-rag" && activeGraph && (
        <div className="panel-stack">
          <section className="panel">
            <h3>Answer</h3>
            <p>{activeGraph.answer}</p>
            <SuccessState
              message={`Text evidence ${activeGraph.text_evidence.length}, graph evidence ${activeGraph.graph_evidence.length}.`}
            />
          </section>

          {isEvidencePanelOpen && (
            <section className="panel">
              <h3>Text Evidence</h3>
              {activeGraph.text_evidence.length ? (
                <ul>
                  {activeGraph.text_evidence.map((item) => (
                    <li key={`text-${item.index}`}>
                      <strong>#{item.index}</strong> {item.source} | score {item.score.toFixed(3)}
                      <div className="hint">{item.excerpt}</div>
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState message="No text evidence returned." />
              )}

              <h3>Graph Evidence</h3>
              {activeGraph.graph_evidence.length ? (
                <ul>
                  {activeGraph.graph_evidence.map((item) => (
                    <li key={`graph-${item.index}`}>
                      <strong>#{item.index}</strong> {item.source} -[{item.edge_type}]-&gt; {item.target}
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState message="No graph evidence returned." />
              )}

              <h3>Subgraph</h3>
              <p>
                nodes: {activeGraph.subgraph.nodes.length}, edges: {activeGraph.subgraph.edges.length}
              </p>
            </section>
          )}
        </div>
      )}

      {mode === "agent" && activeRun && (
        <div className="panel-stack">
          <section className="panel">
            <h3>Agent Answer</h3>
            <p>{activeRun.answer || "(empty answer)"}</p>

            <h3>Evaluation</h3>
            <p>
              confidence: {(activeRun.evaluation?.confidence ?? 0).toFixed(3)} (
              {activeRun.evaluation?.confidence_band ?? "unknown"})
            </p>
            <div className="confidence-bar">
              <div
                className="confidence-fill"
                style={{ width: `${confidencePercent(activeRun.evaluation?.confidence)}%` }}
              />
            </div>
          </section>

          {isRunPanelOpen && (
            <section className="panel">
              <h3>Run Timeline</h3>
              <p>
                run_id: <strong>{activeRun.run_id}</strong> | status: {activeRun.status}
              </p>
              <p>
                plan: {activeRun.plan?.query_type} / {activeRun.plan?.strategy}
              </p>
              <ul className="timeline-list">
                {stepTimeline.map((step) => (
                  <li key={`${step.name}-${step.started_at}`} className={`timeline-item status-${step.status}`}>
                    <strong>{step.name}</strong> - {step.status}
                    <div className="hint">{step.durationLabel}</div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {activeRun.status === "failed" && (
            <section className="panel">
              <ErrorState message={activeRun.error ?? "Agent run failed."} />
              <button type="button" onClick={onRetry}>
                Retry Failed Run
              </button>
            </section>
          )}
        </div>
      )}
    </section>
  );
}

export default function AskPage() {
  return (
    <Suspense fallback={<LoadingState message="Loading Ask..." />}>
      <AskPageContent />
    </Suspense>
  );
}
