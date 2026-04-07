# LearnOS 前端组件契约与工程结构规范（v1）

## 1. 页面组件树与契约

## 1.1 `/ask`

### 组件树
- `AskPage`
  - `AskModeSwitch`
  - `AskQueryForm`
  - `AnswerPanel`
    - `TextEvidenceList`
    - `GraphEvidenceList`
  - `AgentRunPanel`
    - `AgentPlanCard`
    - `AgentStepTimeline`
    - `FallbackBanner`
    - `EvaluationCard`
    - `RetryRunButton`

### Props 契约
- `AskQueryForm`
  - `mode: "graph-rag" | "agent"`
  - `defaults: AskDefaults`
  - `onSubmit(payload: AskSubmitPayload): void`
- `AgentRunPanel`
  - `run: AgentRunDTO`
  - `loading: boolean`
  - `onRetry(payload: AgentRetryPayload): void`

### Events
- `ASK_SUBMIT`
- `ASK_RETRY`
- `ASK_STEP_EXPAND`
- `ASK_COPY_EVIDENCE`

---

## 1.2 `/learning`

### 组件树
- `LearningPage`
  - `LearningHeader`（user_id / graph_path）
  - `LearningPlanCard`
  - `LearningSessionConfigurator`
  - `QuestionList`
    - `QuestionCard`
      - `AnswerEditor`
  - `SubmitAnswersBar`
  - `SubmissionResultPanel`

### Props 契约
- `LearningPlanCard`
  - `plan?: LearningPlanDTO`
  - `loading: boolean`
  - `onGenerate(payload: LearningPlanPayload): void`
- `LearningSessionConfigurator`
  - `questionCount: number`
  - `questionTypes: QuestionType[]`
  - `onGenerate(payload: LearningSessionPayload): void`
- `QuestionCard`
  - `question: QuestionDTO`
  - `value: string`
  - `onChange(questionId: string, answer: string): void`
- `SubmitAnswersBar`
  - `disabled: boolean`
  - `onSubmit(): void`

### Events
- `LEARNING_PLAN_GENERATE`
- `LEARNING_SESSION_GENERATE`
- `LEARNING_ANSWER_CHANGE`
- `LEARNING_SUBMIT`
- `LEARNING_FEEDBACK_VIEW`

---

## 1.3 `/mastery`

### 组件树
- `MasteryPage`
  - `MasterySummaryCards`
  - `MasteryFilterBar`
  - `MasteryTable`
  - `MasteryDetailDrawer`（可选）

### Props 契约
- `MasterySummaryCards`
  - `summary: MasterySummaryDTO`
- `MasteryTable`
  - `rows: MasteryConceptRow[]`
  - `sortBy: MasterySortKey`
  - `onSortChange(sortBy: MasterySortKey): void`
  - `onSelectConcept(conceptId: string): void`

### Events
- `MASTERY_REFRESH`
- `MASTERY_FILTER_CHANGE`
- `MASTERY_SORT_CHANGE`

---

## 1.4 `/knowledge`

### 组件树
- `KnowledgePage`
  - `SubgraphQueryForm`
  - `KnowledgeGraphCanvas`
  - `NodeDetailPanel`

### Props 契约
- `SubgraphQueryForm`
  - `query: string`
  - `concept: string`
  - `hops: number`
  - `maxNodes: number`
  - `onSearch(payload: SubgraphQueryPayload): void`
- `KnowledgeGraphCanvas`
  - `nodes: GraphNodeDTO[]`
  - `edges: GraphEdgeDTO[]`
  - `onNodeClick(nodeId: string): void`

### Events
- `KG_QUERY`
- `KG_NODE_CLICK`
- `KG_JUMP_TO_ASK`

---

## 2. DTO 与类型约束

建议在 `src/types/api.ts` 维护以下类型：
- `GraphRagRequestDTO` / `GraphRagResponseDTO`
- `AgentRunDTO` / `AgentStepDTO` / `AgentFallbackDTO` / `AgentEvaluationDTO`
- `LearningPlanDTO` / `LearningSessionDTO` / `LearningSubmitDTO`
- `MasteryMapDTO`
- `ApiErrorDTO = { detail: string }`

建议在 `src/types/domain.ts` 维护页面层映射：
- `AskViewModel`
- `LearningViewModel`
- `MasteryViewModel`

---

## 3. 工程目录结构规范（Next.js App Router）

建议目录：

- `src/app/(main)/ask/page.tsx`
- `src/app/(main)/learning/page.tsx`
- `src/app/(main)/mastery/page.tsx`
- `src/app/(main)/knowledge/page.tsx`
- `src/app/(main)/layout.tsx`

- `src/components/ask/*`
- `src/components/learning/*`
- `src/components/mastery/*`
- `src/components/knowledge/*`
- `src/components/common/*`

- `src/services/api/client.ts`
- `src/services/api/endpoints.ts`
- `src/services/api/schemas.ts`  // zod schema

- `src/hooks/query/useGraphRag.ts`
- `src/hooks/query/useAgentRun.ts`
- `src/hooks/query/useLearningPlan.ts`
- `src/hooks/query/useLearningSession.ts`
- `src/hooks/query/useLearningSubmit.ts`
- `src/hooks/query/useMasteryMap.ts`

- `src/store/askStore.ts`
- `src/store/learningStore.ts`

- `src/types/api.ts`
- `src/types/domain.ts`

- `src/lib/error-map.ts`
- `src/lib/time.ts`
- `src/lib/logger.ts`

- `src/styles/tokens.css`

---

## 4. API Client 骨架规范（不含业务实现）

## 4.1 `client.ts` 职责
- 统一 `fetch` 封装（baseURL、headers、timeout）
- 统一错误解析：非 2xx 转 `ApiError`
- 支持 request id 注入（可选）

## 4.2 `endpoints.ts` 职责
- 每个后端接口一个方法：
  - `postGraphRag`
  - `postAgentQuery`
  - `getAgentRun`
  - `postAgentRetry`
  - `postLearningPlan`
  - `postLearningSession`
  - `postLearningSubmit`
  - `getLearningMasteryMap`
  - `getKgSubgraph`

## 4.3 `schemas.ts` 职责
- 用 zod 校验所有响应结构
- parse 失败时抛 `SchemaError`

---

## 5. Query Key 与缓存策略

建议 query key：
- `["graph-rag", hash(payload)]`
- `["agent-run", runId]`
- `["learning-plan", userId, graphPath]`
- `["learning-session", userId, hash(payload)]`
- `["mastery-map", userId]`

缓存策略建议：
- `agent-run`: `staleTime: 0`（可轮询）
- `learning-plan/mastery-map`: `staleTime: 30s`
- submit 成功后 `invalidate`：
  - `learning-plan`
  - `mastery-map`

---

## 6. 测试规范（前端）

## 6.1 单元测试
- API 错误映射与 schema 解析
- `learningStore` 草稿更新
- Agent timeline 格式化器

## 6.2 集成测试
- Ask：提交 agent 查询并渲染 step + evaluation
- Learning：plan -> session -> submit -> mastery 刷新
- 错误用例：空 answers、非法题型、无效 run_id

## 6.3 验收回归清单
- [ ] Ask 双模式可用
- [ ] Retry 行为正确并替换 run 展示
- [ ] Learning 三步流无断点
- [ ] Mastery 指标与列表一致
- [ ] 统一错误提示可见

