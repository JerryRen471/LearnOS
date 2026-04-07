#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/import_frontend_tasks_issues.sh
#   bash scripts/import_frontend_tasks_issues.sh owner/repo
#
# Notes:
# - Requires GitHub CLI auth with issue write permission.
# - Re-runnable: if an issue with the same title already exists, it will be skipped.

REPO="${1:-}"
if [[ -n "$REPO" ]]; then
  REPO_ARGS=(--repo "$REPO")
else
  REPO_ARGS=()
fi

ensure_auth() {
  if ! gh auth status >/dev/null 2>&1; then
    echo "GitHub CLI is not authenticated. Run: gh auth login"
    exit 1
  fi
}

issue_exists() {
  local title="$1"
  local number
  number="$(gh issue list "${REPO_ARGS[@]}" --state all --search "\"$title\" in:title" --limit 1 --json number --jq '.[0].number // empty')"
  if [[ -n "$number" ]]; then
    echo "$number"
    return 0
  fi
  return 1
}

create_issue() {
  local title="$1"
  local body="$2"
  local existing
  if existing="$(issue_exists "$title")"; then
    echo "Skip existing issue #$existing: $title"
    return
  fi
  local url
  url="$(gh issue create "${REPO_ARGS[@]}" --title "$title" --body "$body")"
  echo "Created: $url"
}

ensure_auth

SOURCE_DOCS=$(
  cat <<'EOF'
- `docs/frontend/frontend_implementation_spec_v1.md`
- `docs/frontend/api_field_dictionary_v1.md`
- `docs/frontend/component_contracts_and_structure_v1.md`
EOF
)

create_issue \
  "[Frontend][P0][T01] 初始化前端工程骨架（Next.js + TS + App Router）" \
  "$(cat <<EOF
## 目标
建立前端基础工程骨架和核心路由。

## 实现范围
- 初始化 Next.js App Router + TypeScript 工程
- 创建页面路由：\`/ask\`、\`/learning\`、\`/mastery\`、\`/knowledge\`、\`/settings\`
- 建立主布局与导航壳层

## 验收标准
- [ ] 路由可访问且可切换
- [ ] 页面壳层（导航 + 内容区）稳定

## 依赖
- 无

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P0][T02] 建立设计 Token 与基础样式层" \
  "$(cat <<EOF
## 目标
统一视觉语义，建立可复用样式基础。

## 实现范围
- 定义语义色：info/success/warn/danger
- 定义排版层级 token
- 定义 loading/empty/error 三态样式规范

## 验收标准
- [ ] 基础 token 可全局复用
- [ ] 至少一个页面已接入三态样式

## 依赖
- T01

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P0][T03] 实现统一 API Client 与错误映射" \
  "$(cat <<EOF
## 目标
统一网络访问与错误处理行为。

## 实现范围
- 封装 \`client.ts\`（baseURL、headers、timeout）
- 非 2xx 响应统一解析为 \`ApiError\`
- 标准读取后端 \`detail\` 字段

## 验收标准
- [ ] 400/404/5xx 均可映射为统一错误对象
- [ ] 组件层可直接消费统一错误结构

## 依赖
- T01

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P0][T04] 定义 DTO 与 zod schema 校验层" \
  "$(cat <<EOF
## 目标
保证请求/响应类型安全与运行时校验。

## 实现范围
- 建立 \`src/types/api.ts\`
- 建立 \`src/services/api/schemas.ts\`
- 覆盖 Ask/Agent/Learning/Mastery/KG 关键接口

## 验收标准
- [ ] 核心接口响应均有 zod schema
- [ ] parse 失败可抛可观测错误

## 依赖
- T03

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P0][T05] 实现 React Query hooks 与 query key 体系" \
  "$(cat <<EOF
## 目标
建立统一服务端状态管理。

## 实现范围
- 新增 hooks：GraphRag/AgentRun/LearningPlan/LearningSession/LearningSubmit/MasteryMap
- 落地 query key 规范
- 配置缓存与失效策略

## 验收标准
- [ ] hooks 可在页面直接调用
- [ ] submit 成功后可触发 mastery/plan 刷新

## 依赖
- T03, T04

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P0][T06] 实现本地交互 store（ask/learning）" \
  "$(cat <<EOF
## 目标
管理草稿与页面局部 UI 状态。

## 实现范围
- \`askStore\`：模式、面板开关、最近 run
- \`learningStore\`：answer 草稿映射、会话元信息

## 验收标准
- [ ] 作答草稿不会因局部刷新丢失
- [ ] Ask 页面局部状态可持久于页面生命周期

## 依赖
- T01

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P1][T11] 实现 Ask 页面骨架与模式切换" \
  "$(cat <<EOF
## 目标
完成 Ask 页面结构与 Graph-RAG/Agent 模式切换。

## 实现范围
- AskModeSwitch
- AskQueryForm
- AnswerPanel
- AgentRunPanel（占位）

## 验收标准
- [ ] 两种模式可切换并提交
- [ ] 页面具备 loading/empty/error 三态

## 依赖
- T01, T05

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P1][T12] Ask 对接 /query/graph-rag 并展示证据" \
  "$(cat <<EOF
## 目标
完成 Graph-RAG 请求与结果展示。

## 实现范围
- 调用 \`POST /query/graph-rag\`
- 展示 \`answer/text_evidence/graph_evidence/subgraph\`

## 验收标准
- [ ] 核心字段完整渲染
- [ ] 空证据场景可正常展示

## 依赖
- T11

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P1][T13] Ask 对接 /agent/query 并展示 AgentRun" \
  "$(cat <<EOF
## 目标
展示 Agent 编排结果与可解释信息。

## 实现范围
- 调用 \`POST /agent/query\`
- 渲染 \`plan/steps/evaluation/fallback/error\`

## 验收标准
- [ ] step 时间线可读
- [ ] confidence/confidence_band 可视化

## 依赖
- T11

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P1][T14] Ask 对接 run 查询与 retry" \
  "$(cat <<EOF
## 目标
支持查看 run 与按策略重试。

## 实现范围
- \`GET /agent/runs/{run_id}\`
- \`POST /agent/runs/{run_id}/retry\`

## 验收标准
- [ ] retry 后展示新 run_id
- [ ] 新 run 的 retry_of 指向旧 run

## 依赖
- T13

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P1][T15] Ask fallback 与失败态 UX 完善" \
  "$(cat <<EOF
## 目标
完善失败与降级体验。

## 实现范围
- FallbackBanner（降级到 RAG）
- 失败态错误展示与重试按钮

## 验收标准
- [ ] failed_with_fallback 有显著 warning 提示
- [ ] failed 状态有可恢复操作

## 依赖
- T13

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P1][T21] 实现 Learning 页面骨架与基础表单" \
  "$(cat <<EOF
## 目标
搭建学习闭环页面基础结构。

## 实现范围
- Header（user_id / graph_path）
- PlanCard / SessionConfigurator / QuestionList / ResultPanel

## 验收标准
- [ ] 页面结构完整
- [ ] 各模块可独立 loading

## 依赖
- T01, T05, T06

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P1][T22] Learning 对接 /learning/plan" \
  "$(cat <<EOF
## 目标
支持生成并展示个性化学习计划。

## 实现范围
- 调用 \`POST /learning/plan\`
- 渲染 recommended_concepts 列表

## 验收标准
- [ ] mastery/next_review_at/reason 显示正确

## 依赖
- T21

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P1][T23] Learning 对接 /learning/session 与题型配置" \
  "$(cat <<EOF
## 目标
支持题目会话生成与题型选择。

## 实现范围
- 调用 \`POST /learning/session\`
- 支持 \`concept/judgement/cloze/derivation\` 配置

## 验收标准
- [ ] question_count 与题型分布正确
- [ ] 非法题型可被拦截或提示

## 依赖
- T22

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P1][T24] 实现作答草稿编辑与提交前校验" \
  "$(cat <<EOF
## 目标
保证作答体验稳定可控。

## 实现范围
- questionId -> answer 草稿映射
- 提交前完整性校验

## 验收标准
- [ ] 切换题目不丢失草稿
- [ ] 提交时可提示缺失项

## 依赖
- T23, T06

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P1][T25] Learning 对接 /learning/submit 与反馈展示" \
  "$(cat <<EOF
## 目标
完成提交评估与反馈可视化。

## 实现范围
- 调用 \`POST /learning/submit\`
- 渲染 average_score、records、recommendation

## 验收标准
- [ ] 逐题 score/error_type/feedback 可读
- [ ] recommendation 显示明确

## 依赖
- T24

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P1][T26] Learning 提交后自动刷新 plan/mastery" \
  "$(cat <<EOF
## 目标
形成完整学习闭环数据联动。

## 实现范围
- submit 成功后 invalidate：
  - learning-plan
  - mastery-map

## 验收标准
- [ ] 提交后无需手动刷新即可看到新状态

## 依赖
- T25, T05

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P1][T31] Mastery 对接 /learning/mastery-map" \
  "$(cat <<EOF
## 目标
展示掌握度总览与概念明细。

## 实现范围
- summary cards
- concepts table

## 验收标准
- [ ] concept_count/average_mastery/due_count/record_count 正确展示
- [ ] 概念行字段齐全

## 依赖
- T05

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P1][T32] Mastery 筛选与排序（due-only + mastery）" \
  "$(cat <<EOF
## 目标
提升掌握度页可操作性。

## 实现范围
- due-only 过滤
- mastery 升序排序

## 验收标准
- [ ] 筛选/排序结果正确
- [ ] 与 summary 数据一致

## 依赖
- T31

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P2][T41] Knowledge 对接 /kg/subgraph 查询" \
  "$(cat <<EOF
## 目标
支持知识子图查询。

## 实现范围
- query/concept/hops/max_nodes 表单
- 调用 \`GET /kg/subgraph\`

## 验收标准
- [ ] 参数可控
- [ ] 返回 nodes/edges 可消费

## 依赖
- T05

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P2][T42] Knowledge 图渲染与节点详情面板" \
  "$(cat <<EOF
## 目标
完成图谱可视化与节点信息浏览。

## 实现范围
- GraphCanvas（Cytoscape.js 或 D3.js）
- NodeDetailPanel

## 验收标准
- [ ] 点击节点可查看详情
- [ ] 大图仍可交互

## 依赖
- T41

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P2][T43] Knowledge 到 Ask/Learning 跨页联动" \
  "$(cat <<EOF
## 目标
让图谱浏览能驱动后续问答/学习动作。

## 实现范围
- 节点点击后跳转 Ask 或 Learning
- 携带 query/concept 参数

## 验收标准
- [ ] 跳转成功且上下文正确带入

## 依赖
- T42

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P0][T51] 全局错误处理与提示规范落地" \
  "$(cat <<EOF
## 目标
统一 400/404/5xx 前端提示行为。

## 实现范围
- 就近表单错误
- 页面内错误区
- toast 级提示

## 验收标准
- [ ] 所有接口错误都可见 \`detail\`
- [ ] 用户有明确恢复路径

## 依赖
- T03

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P1][T52] 单元测试：api/store/formatter" \
  "$(cat <<EOF
## 目标
建立基础单测护栏。

## 实现范围
- API schema parse
- error map
- store 更新逻辑
- Agent timeline 格式化

## 验收标准
- [ ] 关键模块单测通过
- [ ] 异常分支覆盖

## 依赖
- T03, T04, T06

## 参考文档
$SOURCE_DOCS
EOF
)"

create_issue \
  "[Frontend][P1][T53] 集成测试：Ask + Learning 闭环主链路" \
  "$(cat <<EOF
## 目标
验证核心业务链路端到端可用。

## 实现范围
- Ask: agent 查询 + step/evaluation/fallback 展示
- Learning: plan -> session -> submit -> mastery 刷新
- 错误场景：空 answers、非法题型、无效 run_id

## 验收标准
- [ ] 主链路通过
- [ ] 关键错误链路通过

## 依赖
- T11~T32

## 参考文档
$SOURCE_DOCS
EOF
)"

echo "All frontend implementation issues have been processed."
