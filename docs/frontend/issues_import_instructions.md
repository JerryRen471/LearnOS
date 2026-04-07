# 前端任务列表导入 GitHub Issues（操作说明）

本仓库已提供导入脚本：`scripts/import_frontend_tasks_issues.sh`。

## 前置条件

- 本地已安装并登录 `gh`（GitHub CLI）。
- 当前目录为仓库根目录。
- 你有该仓库的 issue 写权限。

## 快速使用

1) 登录（如尚未登录）：

`gh auth login`

2) 在仓库根目录执行：

`bash scripts/import_frontend_tasks_issues.sh`

3) 导入完成后，脚本会输出创建结果与 issue URL。

## 导入内容

脚本会创建以下分组任务（含验收标准）：

- P0 基础工程（T01-T06）
- P1 Ask 工作台（T11-T15）
- P1 Learning 学习中心（T21-T26）
- P1 Mastery 掌握度（T31-T32）
- P2 Knowledge 图谱浏览（T41-T43）
- 质量保障（T51-T53）

## 说明

- 已包含基础标签：`frontend`、`planning`，以及优先级标签（如 `P0`、`P1`、`P2`）。
- 若标签不存在，脚本会先尝试创建标签，再创建 issue。
- 默认按任务顺序逐条创建，便于后续看板编排。

