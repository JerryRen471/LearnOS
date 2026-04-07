# agent.md

## 项目当前状态

- 源码目录：`src/zhicore`
- 测试目录：`tests`
- 项目配置：`pyproject.toml`
- CLI 入口：`zhicore = zhicore.cli:main`

## 环境信息

- Python：`3.12.3`（系统可用命令为 `python3`）
- 项目要求：`requires-python = ">=3.10"`
- 依赖来源：`pyproject.toml`
- 本地核心测试不依赖外部服务

## 常用安装命令

- `python3 -m pip install -e ".[dev]"`
- `python3 -m pip install -e ".[pdf]"`
- `python3 -m pip install -e ".[rag]"`
- `python3 -m pip install -e ".[cloud]"`

## 常用验证命令

- `pytest tests`
- `pytest tests/test_pipeline.py`
- `python3 -m zhicore.cli --help`
- `PYTHONPATH=src python3 -m zhicore.cli --help`

## 维护约定

- 仅按用户明确请求改动。
- 文档变更后至少回读一次确认内容准确。
- 当目录结构、依赖或运行方式变化时同步更新本文件。
