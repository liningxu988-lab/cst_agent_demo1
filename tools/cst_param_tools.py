"""
CST 参数设置工具。
复用 scripts/cst_controller.py、cst_python_api_controller.py 等 set_parameters 逻辑。
"""

from typing import Any, Dict

from .base import BaseTool, ToolResult, ToolStatus
from .cst_context import get_controller


class SetParameterTool(BaseTool):
    """设置 CST 结构参数。复用现有控制器的 set_parameters。"""

    name = "set_parameter"

    def run(self, params: Dict[str, float] = None, controller: Any = None, **kwargs: Any) -> ToolResult:
        """
        Args:
            params: 参数字典，如 {"patch_length": 12.0, "patch_width": 10.0}
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
        params = params or kwargs.get("params") or {}
        if not params:
            return ToolResult(
                status=ToolStatus.FAILED,
                tool_name=self.name,
                message="params 不能为空",
                error="params is required",
            )
        # 过滤数值参数
        numeric_params = {k: float(v) for k, v in params.items() if isinstance(v, (int, float)) and k not in ["targets"] and not k.startswith("_")}
        if not numeric_params:
            return ToolResult(
                status=ToolStatus.FAILED,
                tool_name=self.name,
                message="无有效数值参数",
                data={"params": params},
                error="no numeric params",
            )
        try:
            ok = ctrl.set_parameters(numeric_params)
            if ok:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    tool_name=self.name,
                    message="参数已设置",
                    data={"params": numeric_params, "rebuilt": True},
                )
            return ToolResult(
                status=ToolStatus.FAILED,
                tool_name=self.name,
                message="设置参数失败",
                data={"params": numeric_params},
                error="set_parameters returned False",
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                tool_name=self.name,
                message=str(e),
                data={"params": numeric_params},
                error=str(e),
            )
