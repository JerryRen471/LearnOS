# 知枢 ZhiCore / CogniCore

> 一个面向个人深度学习的 Knowledge Operating System：
> **结构化知识 + 可检索语义层 + 主动学习闭环**

---

## 1. 项目定位

**知枢（ZhiCore）** 本质上不是传统问答型 RAG 工具，而是一个以知识组织、推理与学习强化为目标的系统平台。

- 中文推荐名：**知枢（ZhiCore）**
- 英文推荐名：**CogniCore**
- 定位关键词：`RAG`、`Knowledge Graph`、`Agent Orchestration`、`Learning Loop`

---

## 2. 项目简介

### 中文简介

知枢（ZhiCore）是一个基于大语言模型（LLM）、检索增强生成（RAG）与知识图谱（Knowledge Graph）的智能个人知识系统。
系统将 PDF/Markdown/网页等非结构化知识解析为可检索、可推理的语义与图谱表示，并通过 Agent 协同实现高质量问答和关系推理。
在此基础上，系统进一步加入自动出题、学习评估和反馈强化，形成“学习-评估-强化”的闭环。

### English Overview

**CogniCore** is an intelligent personal knowledge system powered by LLMs, RAG, and Knowledge Graphs.
It converts unstructured sources (PDFs, markdown, web content) into structured semantic representations and graph-based knowledge networks.
With agent-oriented orchestration, it supports advanced retrieval, reasoning, and interactive exploration, and closes the loop with automated assessment and feedback.

---

## 3. 核心架构（四层）

```text
数据层 → 表示层 → 推理层 → 学习层
```

### 3.1 数据层（Ingestion Pipeline）

**输入数据**
- PDF（论文/教材）
- Markdown / 网页
- 笔记

**关键流程**
1. 文档解析：`PyMuPDF` / `pdfplumber`
2. 结构提取：标题、段落、公式等
3. 语义切分：
   - recursive chunking + overlap（推荐默认）
   - semantic chunking（可选进阶）

### 3.2 表示层（Representation Layer）

#### A. 向量语义层（RAG 核心）
- 向量库：`FAISS` / `Chroma` / `Milvus` / `Weaviate`
- Embedding：`text-embedding-3-large` 或 `bge-large` / `e5`

#### B. 知识图谱层（系统亮点）
- 节点类型：`Concept` / `Entity` / `Theorem` / `Definition` / `Formula` / `Question`
- 边类型：`is-a` / `related-to` / `derived-from` / `used-in` / `explains`
- 构建方式：
  - LLM structured output（JSON schema）抽取实体与关系
  - 可选 spaCy + LLM 混合抽取
- 图数据库：**Neo4j（推荐）**，可替代 `ArangoDB` / `NebulaGraph`

### 3.3 推理层（RAG + Agent）

#### A. RAG 基础流程

```text
Query → Embedding → Vector Search → Context Assembly → LLM Response
```

**增强策略**
- Hybrid Search（向量 + BM25 关键词）
- Graph-RAG（先定位相关节点，再扩展邻居子图后交给 LLM）

#### B. Agent 协同架构
- Planner Agent：任务拆解与策略选择
- Retrieval Agent：向量/关键词检索
- Graph Agent：图谱路径与关系扩展
- Evaluation Agent：结果质量评估与自检

可选框架：`LangChain` / `LlamaIndex` / `AutoGen` / `CrewAI`

### 3.4 学习层（Learning Loop，核心差异化）

- 自动出题：概念题、推导题、判断题、填空题
- 用户知识状态建模：记录 concept mastery 与错误历史
- 自适应学习：spaced repetition + 知识追踪（KT）
- 反馈闭环：LLM 批改 + 错误归因（概念错误/推理错误）

---

## 4. 技术栈建议

- 后端：`Python` + `FastAPI`
- 元数据：`PostgreSQL`
- 向量检索：`FAISS` / `Milvus`
- 知识图谱：`Neo4j`
- LLM：`OpenAI` / `Claude` / 开源 `LLaMA`
- 前端：`React` + `Next.js`
- 图谱可视化：`D3.js` / `Cytoscape.js`

---

## 5. 系统架构图（抽象）

```text
                ┌──────────────┐
                │   Frontend   │
                └──────┬───────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   Query Agent   Learning Agent   Graph Agent
        │              │              │
        └──────┬───────┴───────┬──────┘
               │               │
         Vector DB        Graph DB
           (RAG)           (KG)
               │               │
               └──────┬────────┘
                      │
                 Document Store
```

---

## 6. 关键创新点（论文/申报可用）

1. Graph-RAG 融合检索与推理
2. 知识解析 → 图谱建模 → 题目生成的闭环
3. Agent-based 知识调度与多角色协作
4. 用户知识状态建模与自适应学习策略
5. 从“查询系统”升级为“学习系统”

---

## 7. 务实开发路线（推荐）

### Phase 1：最小闭环（MVP）
- PDF → Chunk → Embedding → RAG 问答

### Phase 2：知识图谱增强
- 目标：从“仅向量召回”升级为“向量 + 图谱联合检索”。
- 核心实现：
  1. 抽取管线：`chunk -> LLM JSON schema extraction -> concept/entity/relation`。
  2. 图模型落库（Neo4j）：
     - Node：`Concept` `Entity` `Definition` `Formula`
     - Edge：`related-to` `is-a` `derived-from` `used-in`
  3. 建立 chunk 与图节点映射（`chunk_id <-> concept_id[]`），实现向量语义与图结构互跳。
  4. Graph-RAG 检索链路：
     - 先向量召回 top-k chunk
     - 再定位相关 concept 节点并扩展 1~2 跳子图
     - 合并上下文后生成答案
- API 建议：
  - `POST /kg/build`：按文档构建/增量更新图谱
  - `GET /kg/subgraph`：按 query 或 concept 返回子图
  - `POST /query/graph-rag`：执行 Graph-RAG 问答
- 验收标准：
  - 回答中可给出“文本证据 + 图谱关系证据”
  - 对概念关系类问题优于纯向量 RAG

### Phase 3：Agent 调度
- 目标：实现可解释、可观测、可回退的多 Agent 编排。
- 核心实现：
  1. `Planner Agent`：识别问题类型（定义解释/关系推理/综合问答），选择执行策略。
  2. `Retrieval Agent`：执行 hybrid search（Vector + BM25），返回候选证据。
  3. `Graph Agent`：执行图路径扩展与关系压缩（子图摘要）。
  4. `Evaluation Agent`：对答案做一致性检查、证据覆盖评分、置信度输出。
  5. 编排与状态管理：
     - 建议采用 `LangGraph`（或等价框架）定义状态机
     - 统一 `run_id`、步骤日志、失败回退（例如降级到纯 RAG）
- API 建议：
  - `POST /agent/query`：启动一次 Agent 编排问答
  - `GET /agent/runs/{run_id}`：查看执行轨迹（plan、tool calls、evidence）
  - `POST /agent/runs/{run_id}/retry`：按策略重试
- 验收标准：
  - 每次回答都可追踪到执行路径和证据来源
  - 编排失败时可自动降级并返回可用结果

### Phase 4：学习闭环
- 目标：从“会回答”升级为“能持续提升用户掌握度”。
- 核心实现：
  1. 自动出题服务：
     - 以 `薄弱concept + 关联子图 + 原文chunk` 生成题目
     - 题型覆盖：概念题/判断题/填空题/推导题
  2. 用户知识状态建模（PostgreSQL）：
     - `user_concept_state(user_id, concept_id, mastery, last_review_at, next_review_at)`
     - `practice_record(question_id, answer, score, error_type, timestamp)`
  3. 自适应调度：
     - 基线使用 SM-2（spaced repetition）
     - 可逐步替换为 BKT/DKT 等知识追踪模型
  4. 批改与反馈：
     - LLM + rubric 评分
     - 错误归因：概念错误/推理错误/表达不完整
     - 输出下一轮学习建议与推荐复习路径
- API 建议：
  - `POST /learning/plan`：生成个性化学习计划
  - `POST /learning/session`：生成一组练习题
  - `POST /learning/submit`：提交答案并返回评估与反馈
  - `GET /learning/mastery-map`：返回用户概念掌握度图
- 验收标准：
  - 系统能稳定输出“出题-作答-评估-复习推荐”闭环
  - 用户掌握度曲线可被持续记录和解释

---

## 8. 成功标准（建议）

- 能稳定回答来源于文档的问题，并给出可追溯上下文
- 能展示关键概念之间的图谱关系
- 能按用户薄弱点生成题目并反馈掌握度变化
- 能形成“提问-学习-评估-再学习”的持续闭环
