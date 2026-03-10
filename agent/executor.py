"""
Executor：按 ActionPlan 调用 ToolRegistry 执行工具。
不解析结果，仅返回 ToolResult 列表。
"""

from typing import List, Optional

from tools import ToolRegistry
from tools.base import ToolResult, ToolStatus

from .models import ActionPlan


class Executor:
    """
    执行器。
    按计划顺序调用工具，任一失败时可选停止或继续。
    """

    def __init__(self, stop_on_failure: bool = True) -> None:
        self.stop_on_failure = stop_on_failure

    def execute(
        self,
        plan: ActionPlan,
        registry: Optional[ToolRegistry] = None,
    ) -> List[ToolResult]:
        """
        执行计划。

        Args:
            plan: 动作计划
            registry: 工具注册表，默认从 get_registry() 获取

        Returns:
            各工具执行结果列表
        """
        if registry is None:
            from tools import get_registry
            registry = get_registry()

        results: List[ToolResult] = []
        for action in plan.actions:
            res = registry.run(action.tool, **action.kwargs)
            results.append(res)
            if self.stop_on_failure and res.status == ToolStatus.FAILED:
                break
        return results
