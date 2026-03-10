"""
CST 求解器工具。
复用 scripts/cst_controller.py、cst_python_api_controller.py 等 run_simulation 逻辑。
"""

from typing import Any

from .base import BaseTool, ToolResult, ToolStatus
from .cst_context import get_controller


class RunSolverTool(BaseTool):
    """运行 CST 仿真。复用现有控制器的 run_simulation。"""

    name = "run_solver"

    def run(
        self,
        wait_complete: bool = True,
        timeout: int = 600,
        controller: Any = None,
        **kwargs: Any,
    ) -> ToolResult:
        """
        Args:
            wait_complete: 是否等待仿真完成
            timeout: 超时时间（秒）
            controller: 可选，未传则从上下文获取
        """
        ctrl = controller or get_controller()
        if ctrl is None:
            return ToolResult(
                status=ToolStatus.FAILED,
                tool_name=self.name,
                message="未注入 CST 控制器",
                error="controller not set",
            )
        timeout = kwargs.get("timeout", timeout)
        wait_complete = kwargs.get("wait_complete", wait_complete)
        try:
            ok = ctrl.run_simulation(wait_complete=wait_complete, timeout=timeout)
            if ok:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    tool_name=self.name,
                    message="仿真完成",
                    data={"wait_complete": wait_complete, "timeout": timeout},
                )
            return ToolResult(
                status=ToolStatus.FAILED,
                tool_name=self.name,
                message="仿真失败或超时",
                data={"wait_complete": wait_complete, "timeout": timeout},
                error="run_simulation returned False",
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                tool_name=self.name,
                message=str(e),
                data={"wait_complete": wait_complete, "timeout": timeout},
                error=str(e),
            )
