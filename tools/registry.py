"""
工具注册表。
集中管理所有 Agent 工具，支持按名称调用与发现。
"""

from typing import Any, Dict, Optional

from .base import BaseTool, ToolResult, ToolStatus
from .cst_project_tools import OpenProjectTool
from .cst_param_tools import SetParameterTool
from .cst_solver_tools import RunSolverTool
from .cst_result_tools import ReadS11Tool


def register_cst_tools(registry: "ToolRegistry") -> None:
    """注册 CST 相关工具：open_project, set_parameter, run_solver, read_s11"""
    registry.register(OpenProjectTool())
    registry.register(SetParameterTool())
    registry.register(RunSolverTool())
    registry.register(ReadS11Tool())


class ToolRegistry:
    """工具注册表"""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """按名称获取工具"""
        return self._tools.get(name)

    def run(self, name: str, **kwargs: Any) -> ToolResult:
        """执行指定工具"""
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                status=ToolStatus.FAILED,
                tool_name=name,
                message=f"Tool not found: {name}",
                error=f"Tool '{name}' not registered",
            )
        return tool.run(**kwargs)

    def list_tools(self) -> list[str]:
        """列出所有已注册工具名称"""
        return list(self._tools.keys())


# 全局单例
_registry: Optional[ToolRegistry] = None


def get_registry(register_defaults: bool = True) -> ToolRegistry:
    """获取全局工具注册表。register_defaults=True 时自动注册 CST 工具。"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        if register_defaults:
            register_cst_tools(_registry)
    return _registry
