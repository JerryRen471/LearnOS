"use client";

import { FormEvent, useMemo, useState } from "react";

import { EmptyState, ErrorState, LoadingState, SuccessState } from "@/components/ui/states";
import { useLearningPlan, useLearningSession, useLearningSubmit } from "@/services/query/hooks";
import { useLearningStore } from "@/stores/learning-store";

const DEFAULT_TYPES: Array<"concept" | "judgement" | "cloze" | "derivation"> = ["concept", "judgement"];

export default function LearningPage() {
  const sessionId = useLearningStore((state) => state.sessionId);
  const userId = useLearningStore((state) => state.userId);
  const graphPath = useLearningStore((state) => state.graphPath);
  const answerDrafts = useLearningStore((state) => state.answerDrafts);
  const setSessionMeta = useLearningStore((state) => state.setSessionMeta);
  const setAnswerDraft = useLearningStore((state) => state.setAnswerDraft);

  const [questionCount, setQuestionCount] = useState(3);

  const planQuery = useLearningPlan({ user_id: userId, graph_path: graphPath });
  const sessionMutation = useLearningSession();
  const submitMutation = useLearningSubmit();

  const questions = useMemo(() => sessionMutation.data?.questions ?? [], [sessionMutation.data]);

  const submitDisabled = useMemo(() => {
    if (!questions.length) {
      return true;
    }
    return questions.some((question) => !answerDrafts[question.question_id]?.trim());
  }, [answerDrafts, questions]);

  const startSession = () => {
    sessionMutation.mutate(
      {
        user_id: userId,
        graph_path: graphPath,
        question_count: questionCount,
        question_types: DEFAULT_TYPES,
      },
      {
        onSuccess: (data) => {
          setSessionMeta({ sessionId: data.session_id, userId, graphPath });
        },
      },
    );
  };

  const submitAnswers = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!sessionMutation.data?.session_id) {
      return;
    }

    submitMutation.mutate({
      session_id: sessionMutation.data.session_id,
      user_id: userId,
      answers: questions.map((question) => ({
        question_id: question.question_id,
        answer: answerDrafts[question.question_id] ?? "",
      })),
    });
  };

  return (
    <section className="page">
      <header className="page-header">
        <h2>Learning</h2>
        <p>Plan, session and draft editing baseline.</p>
      </header>

      <section className="panel">
        <h3>Session Config</h3>
        <p>
          user_id: <strong>{userId}</strong>
        </p>
        <p>
          graph_path: <strong>{graphPath}</strong>
        </p>
        <p>
          current session_id: <strong>{sessionId ?? "none"}</strong>
        </p>
        <div className="inline-actions">
          <label htmlFor="question-count">question_count</label>
          <input
            id="question-count"
            type="number"
            min={1}
            max={10}
            value={questionCount}
            onChange={(event) => setQuestionCount(Number(event.target.value) || 1)}
          />
          <button type="button" onClick={startSession}>
            Start Session
          </button>
        </div>
      </section>

      {planQuery.isLoading && <LoadingState message="Loading learning plan..." />}
      {planQuery.error && <ErrorState message={(planQuery.error as { detail?: string }).detail ?? "Plan request failed"} />}
      {planQuery.data && (
        <section className="panel">
          <h3>Recommended Concepts</h3>
          <ul>
            {planQuery.data.recommended_concepts.map((concept) => (
              <li key={concept.concept_id}>
                {concept.concept_name} (mastery: {concept.mastery})
              </li>
            ))}
          </ul>
        </section>
      )}

      {!questions.length && !sessionMutation.isPending && (
        <EmptyState message="No question session yet. Start a session first." />
      )}

      {sessionMutation.isPending && <LoadingState message="Generating learning session..." />}
      {sessionMutation.error && (
        <ErrorState message={(sessionMutation.error as { detail?: string }).detail ?? "Session request failed"} />
      )}

      {questions.length > 0 && (
        <form className="panel-stack" onSubmit={submitAnswers}>
          <section className="panel">
            <h3>Questions</h3>
            <ul>
              {questions.map((question) => (
                <li key={question.question_id} className="question-item">
                  <p>
                    <strong>{question.type}</strong>: {question.prompt}
                  </p>
                  <textarea
                    value={answerDrafts[question.question_id] ?? ""}
                    onChange={(event) => setAnswerDraft(question.question_id, event.target.value)}
                    rows={3}
                    placeholder="Write your answer draft here"
                  />
                </li>
              ))}
            </ul>
          </section>
          <section className="panel">
            <button type="submit" disabled={submitDisabled || submitMutation.isPending}>
              Submit Answers
            </button>
            {submitDisabled && (
              <p className="hint">Complete all drafts before submitting (draft map persists in page lifecycle).</p>
            )}
            {submitMutation.isPending && <LoadingState message="Submitting answers..." />}
            {submitMutation.error && (
              <ErrorState message={(submitMutation.error as { detail?: string }).detail ?? "Submit request failed"} />
            )}
            {submitMutation.data && (
              <SuccessState message={`Average score: ${submitMutation.data.average_score.toFixed(2)}`} />
            )}
          </section>
        </form>
      )}
    </section>
  );
}
