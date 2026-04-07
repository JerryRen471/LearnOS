"use client";

import { FormEvent, useMemo, useState } from "react";

import { EmptyState, ErrorState, LoadingState, SuccessState } from "@/components/ui/states";
import { useLearningPlan, useLearningSession, useLearningSubmit, useMasteryMap } from "@/services/query/hooks";
import { useLearningStore } from "@/stores/learning-store";

const QUESTION_TYPES: Array<"concept" | "judgement" | "cloze" | "derivation"> = [
  "concept",
  "judgement",
  "cloze",
  "derivation",
];

const SANDBOX_QUESTIONS = [
  { question_id: "sandbox-concept", type: "concept", prompt: "概念草稿编辑（本地）" },
  { question_id: "sandbox-judgement", type: "judgement", prompt: "判断题草稿编辑（本地）" },
] as const;

export default function LearningPage() {
  const sessionId = useLearningStore((state) => state.sessionId);
  const userId = useLearningStore((state) => state.userId);
  const graphPath = useLearningStore((state) => state.graphPath);
  const answerDrafts = useLearningStore((state) => state.answerDrafts);
  const setSessionMeta = useLearningStore((state) => state.setSessionMeta);
  const setAnswerDraft = useLearningStore((state) => state.setAnswerDraft);

  const [questionCount, setQuestionCount] = useState(6);
  const [selectedTypes, setSelectedTypes] = useState<Array<"concept" | "judgement" | "cloze" | "derivation">>([
    "concept",
    "judgement",
  ]);
  const [selectedQuestionId, setSelectedQuestionId] = useState<string | null>(null);
  const [validationMessage, setValidationMessage] = useState<string>("");

  const planQuery = useLearningPlan({ user_id: userId, graph_path: graphPath, top_k: 8 });
  const masteryQuery = useMasteryMap({ user_id: userId, graph_path: graphPath });
  const sessionMutation = useLearningSession();
  const submitMutation = useLearningSubmit();

  const questions = useMemo(() => sessionMutation.data?.questions ?? [], [sessionMutation.data]);

  const selectedQuestion = useMemo(() => {
    if (!questions.length || !selectedQuestionId) {
      return null;
    }
    return questions.find((item) => item.question_id === selectedQuestionId) ?? null;
  }, [questions, selectedQuestionId]);

  const missingQuestionIds = useMemo(() => {
    if (!questions.length) {
      return [];
    }
    return questions
      .filter((question) => !answerDrafts[question.question_id]?.trim())
      .map((question) => question.question_id);
  }, [answerDrafts, questions]);

  const onToggleType = (type: (typeof QUESTION_TYPES)[number]) => {
    setSelectedTypes((current) => {
      if (current.includes(type)) {
        return current.filter((item) => item !== type);
      }
      return [...current, type];
    });
  };

  const startSession = () => {
    setValidationMessage("");

    if (!selectedTypes.length) {
      setValidationMessage("至少选择一种题型。");
      return;
    }

    const invalidTypes = selectedTypes.filter((type) => !QUESTION_TYPES.includes(type));
    if (invalidTypes.length) {
      setValidationMessage(`非法题型：${invalidTypes.join(", ")}`);
      return;
    }

    sessionMutation.mutate(
      {
        user_id: userId,
        graph_path: graphPath,
        question_count: questionCount,
        question_types: selectedTypes,
      },
      {
        onSuccess: (data) => {
          setSessionMeta({ sessionId: data.session_id, userId, graphPath });
          setSelectedQuestionId(data.questions[0]?.question_id ?? null);
        },
      },
    );
  };

  const submitAnswers = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setValidationMessage("");

    if (!sessionMutation.data?.session_id) {
      setValidationMessage("请先生成 session。");
      return;
    }

    if (missingQuestionIds.length) {
      setValidationMessage(`以下题目未作答：${missingQuestionIds.join(", ")}`);
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
        <p>Plan → Session → Answer → Submit → Mastery refresh.</p>
      </header>

      <section className="panel">
        <h3>Header</h3>
        <p>
          user_id: <strong>{userId}</strong>
        </p>
        <p>
          graph_path: <strong>{graphPath}</strong>
        </p>
        <p>
          session_id: <strong>{sessionId ?? "none"}</strong>
        </p>
      </section>

      <section className="panel">
        <h3>PlanCard</h3>
        {planQuery.isLoading && <LoadingState message="Loading learning plan..." />}
        {planQuery.error && (
          <ErrorState message={(planQuery.error as { detail?: string }).detail ?? "Plan request failed."} />
        )}
        {planQuery.data && (
          <ul>
            {planQuery.data.recommended_concepts.map((concept) => (
              <li key={concept.concept_id}>
                <strong>{concept.concept_name}</strong> | mastery: {concept.mastery.toFixed(3)} | next:
                {" "}
                {concept.next_review_at ?? "-"} | reason: {concept.reason ?? "-"}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel">
        <h3>SessionConfigurator</h3>
        <div className="inline-actions">
          <label htmlFor="question-count">question_count</label>
          <input
            id="question-count"
            type="number"
            min={1}
            max={30}
            value={questionCount}
            onChange={(event) => setQuestionCount(Math.max(1, Number(event.target.value) || 1))}
          />
          <button type="button" onClick={startSession}>
            Generate Session
          </button>
        </div>
        <div className="checkbox-group">
          {QUESTION_TYPES.map((type) => (
            <label key={type}>
              <input
                type="checkbox"
                checked={selectedTypes.includes(type)}
                onChange={() => onToggleType(type)}
              />
              {type}
            </label>
          ))}
        </div>
        {validationMessage && <ErrorState message={validationMessage} />}
        {sessionMutation.isPending && <LoadingState message="Generating session..." />}
        {sessionMutation.error && (
          <ErrorState message={(sessionMutation.error as { detail?: string }).detail ?? "Session request failed."} />
        )}
        {sessionMutation.data?.distribution && (
          <p className="hint">distribution: {JSON.stringify(sessionMutation.data.distribution)}</p>
        )}
      </section>

      <section className="panel">
        <h3>QuestionList / Draft Editor</h3>
        {!questions.length && (
          <>
            <EmptyState message="No generated questions yet. You can still use local sandbox drafts." />
            <ul>
              {SANDBOX_QUESTIONS.map((question) => (
                <li key={question.question_id} className="question-item">
                  <p>
                    <strong>{question.type}</strong>: {question.prompt}
                  </p>
                  <textarea
                    value={answerDrafts[question.question_id] ?? ""}
                    onChange={(event) => setAnswerDraft(question.question_id, event.target.value)}
                    rows={3}
                    placeholder="Write local draft answer"
                  />
                </li>
              ))}
            </ul>
          </>
        )}

        {questions.length > 0 && (
          <>
            <div className="question-switcher">
              {questions.map((question, idx) => {
                const active = selectedQuestion?.question_id === question.question_id;
                const answered = Boolean(answerDrafts[question.question_id]?.trim());
                return (
                  <button
                    type="button"
                    key={question.question_id}
                    className={active ? "active" : ""}
                    onClick={() => setSelectedQuestionId(question.question_id)}
                  >
                    Q{idx + 1} {answered ? "✓" : "•"}
                  </button>
                );
              })}
            </div>

            {selectedQuestion ? (
              <div className="question-editor">
                <p>
                  <strong>{selectedQuestion.type}</strong>: {selectedQuestion.prompt}
                </p>
                <textarea
                  value={answerDrafts[selectedQuestion.question_id] ?? ""}
                  onChange={(event) => setAnswerDraft(selectedQuestion.question_id, event.target.value)}
                  rows={4}
                  placeholder="Write answer draft"
                />
              </div>
            ) : (
              <EmptyState message="Select a question to edit draft." />
            )}
          </>
        )}
      </section>

      <form className="panel" onSubmit={submitAnswers}>
        <h3>ResultPanel</h3>
        <button type="submit" disabled={submitMutation.isPending || !questions.length}>
          Submit Answers
        </button>
        {submitMutation.isPending && <LoadingState message="Submitting answers..." />}
        {submitMutation.error && (
          <ErrorState message={(submitMutation.error as { detail?: string }).detail ?? "Submit request failed."} />
        )}
        {submitMutation.data && (
          <>
            <SuccessState message={`Average score: ${submitMutation.data.average_score.toFixed(3)}`} />
            <p>
              recommendation: <strong>{submitMutation.data.recommendation ?? "-"}</strong>
            </p>
            <ul>
              {submitMutation.data.records.map((record) => (
                <li key={record.question_id}>
                  {record.question_id} | score: {record.score.toFixed(3)} | error_type: {record.error_type ?? "none"}
                  <div className="hint">{record.feedback ?? ""}</div>
                </li>
              ))}
            </ul>
          </>
        )}
      </form>

      <section className="panel">
        <h3>Mastery Snapshot (auto-refresh on submit)</h3>
        {masteryQuery.isLoading && <LoadingState message="Loading mastery map..." />}
        {masteryQuery.error && (
          <ErrorState message={(masteryQuery.error as { detail?: string }).detail ?? "Mastery request failed."} />
        )}
        {masteryQuery.data && (
          <p>
            concepts: {masteryQuery.data.summary.concept_count}, avg_mastery:
            {" "}
            {masteryQuery.data.summary.average_mastery.toFixed(3)}, due: {masteryQuery.data.summary.due_count},
            records: {masteryQuery.data.summary.record_count}
          </p>
        )}
      </section>
    </section>
  );
}
