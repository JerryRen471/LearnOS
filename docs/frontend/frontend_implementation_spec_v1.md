# LearnOS 前端可实施规范（v1）

## 1. 文档目标与边界

本规范用于指导 LearnOS 前端从 0 到 1 实现，覆盖信息架构、页面职责、状态模型、交互流程与验收标准。  
重点对齐当前后端已实现能力：Phase 2（Graph-RAG）、Phase 3（Agent 编排）、Phase 4（学习闭环）。

非目标（v1 不做）：
- 多租户权限系统
- 移动端专属布局
- 复杂运营后台

## 2. 产品目标

前端目标不是“仅问答”，而是“问答 + 学习强化”闭环：
1. 提问并理解证据（文本 + 图谱 + Agent 轨迹）
2. 进入练习（自动出题）
3. 获得评估与反馈（评分 + 错误归因）
4. 查看掌握度并进入下一轮复习

## 3. 信息架构（IA）

一级导航建议：
1. `Ask`（问答工作台）
2. `Learning`（学习中心）
3. `Mastery`（掌握度）
4. `Knowledge`（图谱浏览）

建议路由：
- `/ask`
- `/learning`
- `/mastery`
- `/knowledge`
- `/settings`（可选：默认参数与路径配置）

## 4. 页面职责与实现要求

## 4.1 Ask 页面

核心目标：完成 Graph-RAG 与 Agent 问答，并展示可解释证据。

页面布局建议（三栏）：
- 左栏：查询输入、模式切换
- 中栏：答案与文本证据
- 右栏：图谱关系、Agent 执行轨迹

必须功能：
- Graph-RAG 模式调用 `/query/graph-rag`
- Agent 模式调用 `/agent/query`
- 支持 run 详情刷新：`/agent/runs/{run_id}`
- 支持 retry：`/agent/runs/{run_id}/retry`
- 若 `fallback.triggered=true`，显示“降级到 RAG”提示条

## 4.2 Learning 页面

核心目标：跑通“计划 -> 出题 -> 作答 -> 提交评估”。

流程规范：
1. 生成学习计划（`/learning/plan`）
2. 生成题目会话（`/learning/session`）
3. 逐题作答（前端草稿态）
4. 提交答案（`/learning/submit`）
5. 展示总分、逐题反馈、推荐动作

题型支持：
- `concept`
- `judgement`
- `cloze`
- `derivation`

## 4.3 Mastery 页面

核心目标：可视化用户掌握状态与复习调度。

必须展示：
- summary 指标：`concept_count` / `average_mastery` / `due_count` / `record_count`
- concepts 表格：掌握度、复习时间、SM-2 参数、错误统计

建议交互：
- due-only 过滤
- 按 mastery 升序排序（默认）

## 4.4 Knowledge 页面

核心目标：按 query/concept 浏览子图，支撑“理解关系”。

功能规范：
- 调用 `/kg/subgraph`
- 控制参数：`hops`、`max_nodes`
- 点击节点可联动跳转到 `/ask` 或 `/learning`

## 5. 状态管理规范

采用“远程状态 + 本地交互状态”双层模型：

1) 远程状态（React Query）
- `graphRagResult`
- `agentRun`
- `learningPlan`
- `learningSession`
- `learningSubmitResult`
- `masteryMap`

2) 本地状态（轻量 store）
- Ask 输入草稿与筛选器
- Learning 题目作答草稿（`{ [questionId]: answer }`）
- 页面面板开关（证据/轨迹展开）

统一三态：
- `loading`
- `empty`
- `error`

## 6. 交互状态机规范

## 6.1 Agent 流

`idle -> submitting -> run_loaded -> success | failed`

特殊分支：
- `success_with_fallback`（显示 warning 样式）

## 6.2 Learning 流

`idle -> plan_ready -> session_ready -> drafting -> submitting -> feedback_ready -> mastery_refreshed`

## 7. 错误处理规范

HTTP 映射建议：
- `400`: 参数错误（就近表单报错）
- `404`: run/question 不存在（可操作提示 + 返回上一步）
- `5xx/网络`: toast + 重试按钮

错误文案源统一读取后端 `detail` 字段。

## 8. 前端实现技术建议

- 框架：Next.js + React + TypeScript
- 数据层：React Query
- 运行时校验：zod
- 图谱：Cytoscape.js（优先）
- UI：设计 token + 语义色（info/success/warn/danger）

## 9. 验收标准（DoD）

- Ask 可显示 plan/steps/evaluation/fallback
- Agent retry 可返回并展示新 `run_id`
- Learning 可完整跑通 plan/session/submit
- Mastery 可稳定显示 summary + concepts
- 所有页面有 loading/empty/error 状态
- 接口错误均可见 `detail` 文案

