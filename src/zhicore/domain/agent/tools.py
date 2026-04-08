"""Agent tool interfaces: registry + execution contracts.

This module is intentionally small and dependency-free so agent orchestration
can remain decoupled from specific tool implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol, TypeVar


@dataclass(frozen=True, slots=True)
class ToolResult:
    ok: bool
    data: Any = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ToolContext:
    """Shared tool context passed by the orchestrator."""

    store: Any
    graph: Any


class Tool(Protocol):
    name: str

    def run(self, ctx: ToolContext, payload: dict[str, Any]) -> ToolResult: ...


_ToolFn = Callable[[ToolContext, dict[str, Any]], ToolResult]


class _FnTool:
    def __init__(self, name: str, fn: _ToolFn) -> None:
        self.name = name
        self._fn = fn

    def run(self, ctx: ToolContext, payload: dict[str, Any]) -> ToolResult:
        return self._fn(ctx, payload)


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register_tool(tool)

    def register_tool(self, tool: Tool) -> None:
        if not getattr(tool, "name", ""):
            raise ValueError("Tool.name must be set.")
        self._tools[tool.name] = tool

    def register(self, name: str, fn: _ToolFn) -> None:
        """Register a lightweight function tool (convenience API)."""
        self._tools[name] = _FnTool(name=name, fn=fn)

    def has(self, name: str) -> bool:
        return name in self._tools

    def run(self, name: str, *, ctx: ToolContext, payload: dict[str, Any]) -> ToolResult:
        tool = self.get(name)
        return tool.run(ctx, payload)

    def get(self, name: str) -> Tool:
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Tool not found: {name}")
        return tool

