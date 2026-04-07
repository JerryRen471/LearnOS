# LearnOS 前端接口字段字典（v1）

## 1. 通用约定

- 返回错误体统一为：
  - `{ "detail": "..." }`
- 时间字段统一 ISO8601 字符串。
- 请求/响应字段建议在前端使用 zod 做运行时校验。

---

## 2. Ask 相关接口

## 2.1 `POST /query/graph-rag`

### Request
- `query: string`（必填）
- `index_path?: string`
- `graph_path?: string`
- `top_k?: number`（1~20）
- `dense_k?: number`（1~60）
- `sparse_k?: number`（1~60）
- `rrf_k?: number`（1~1000）
- `retrieval_mode?: "hybrid" | "dense" | "sparse"`
- `graph_hops?: number`（0~2）
- `embedding_provider?: string`
- `embedding_model?: string`
- `dense_backend?: string`

### Response
- `answer: string`
- `text_evidence: Array<{
  index: number;
  chunk_id: string;
  source: string;
  score: number;
  excerpt: string;
}>`
- `graph_evidence: Array<{
  index: number;
  edge_type: string;
  source: string;
  target: string;
  evidence_chunk_id: string;
}>`
- `subgraph: { nodes: any[]; edges: any[] }`

## 2.2 `POST /agent/query`

### Request
- `query: string`（必填）
- `index_path?: string`
- `graph_path?: string`
- `top_k?: number`
- `dense_k?: number`
- `sparse_k?: number`
- `rrf_k?: number`
- `embedding_provider?: string`
- `embedding_model?: string`
- `dense_backend?: string`

### Response（AgentRun）
- `run_id: string`
- `query: string`
- `status: string`（常见：`succeeded` / `failed`）
- `retry_of: string | null`
- `created_at: string`
- `updated_at: string`
- `plan: {
  query_type: string;
  strategy: string;
  retrieval_mode: string;
  use_graph: boolean;
}`
- `steps: Array<{
  name: string;
  status: string;
  detail: Record<string, any>;
  started_at: string;
  finished_at: string;
}>`
- `answer: string`
- `text_evidence: any[]`
- `graph_evidence: any[]`
- `subgraph: { nodes: any[]; edges: any[] }`
- `evaluation: {
  consistency_check: boolean;
  coverage_score: number;
  confidence: number;
  confidence_band: "high" | "medium" | "low";
}`
- `fallback: {
  triggered: boolean;
  mode: string;
  reason: string;
} | null`
- `error: string | null`

## 2.3 `GET /agent/runs/{run_id}`

### Path
- `run_id: string`

### Response
- 与 `/agent/query` 返回的 `AgentRun` 同结构。

## 2.4 `POST /agent/runs/{run_id}/retry`

### Path
- `run_id: string`

### Request（可选覆盖）
- `query?: string`
- `top_k?: number`
- `dense_k?: number`
- `sparse_k?: number`
- `rrf_k?: number`
- `embedding_provider?: string`
- `embedding_model?: string`
- `dense_backend?: string`

### Response
- 新的 `AgentRun`（`run_id` 不同，`retry_of` 指向原 run）。

---

## 3. Learning 相关接口

## 3.1 `POST /learning/plan`

### Request
- `user_id: string`（必填）
- `graph_path?: string`
- `max_concepts?: number`（1~50）

### Response
- `user_id: string`
- `generated_at: string`
- `strategy: "sm2_baseline"`
- `recommended_concepts: Array<{
  concept_id: string;
  concept_name: string;
  mastery: number;          // 0~1
  next_review_at: string | null;
  reason: string;
}>`

## 3.2 `POST /learning/session`

### Request
- `user_id: string`（必填）
- `graph_path?: string`
- `question_count?: number`（1~60）
- `question_types?: Array<"concept" | "judgement" | "cloze" | "derivation">`

### Response
- `user_id: string`
- `generated_at: string`
- `question_count: number`
- `questions: Array<{
  question_id: string;
  user_id: string;
  concept_id: string;
  concept_name: string;
  question_type: "concept" | "judgement" | "cloze" | "derivation";
  prompt: string;
  reference_answer: string;
  rubric: string;
  created_at: string;
}>`

## 3.3 `POST /learning/submit`

### Request
- `user_id: string`（必填）
- `answers: Array<{
  question_id: string;
  answer: string;
}>`（不能为空）

### Response
- `user_id: string`
- `submitted_at: string`
- `average_score: number` // 0~1
- `records: Array<{
  question_id: string;
  concept_id: string;
  concept_name: string;
  question_type: string;
  score: number;
  error_type: "none" | "表达不完整" | "推理错误" | "概念错误";
  feedback: string;
  mastery: number;
  next_review_at: string | null;
}>`
- `recommendation: string`

## 3.4 `GET /learning/mastery-map`

### Query
- `user_id: string`（必填）

### Response
- `user_id: string`
- `summary: {
  concept_count: number;
  average_mastery: number;
  due_count: number;
  record_count: number;
}`
- `concepts: Array<{
  concept_id: string;
  concept_name: string;
  mastery: number;
  last_review_at: string | null;
  next_review_at: string | null;
  repetition: number;
  interval_days: number;
  ease_factor: number;
  total_attempts: number;
  error_count: number;
}>`

---

## 4. 错误码处理建议

- `400` 参数错误：在当前表单区域显示后端 `detail`
- `404` 资源不存在：提示并给出返回入口
- `500+` 服务异常：toast + 重试按钮

前端错误对象建议统一：
- `ApiError = { status: number; detail: string; raw?: unknown }`

