"""
CST 结果读取工具。
复用 scripts/cst_controller.py、cst_python_api_controller.py 等 get_s11_parameters / get_s_parameters_full 逻辑。
"""

from typing import Any

from .base import BaseTool, ToolResult, ToolStatus
from .cst_context import get_controller


class ReadS11Tool(BaseTool):
    """读取 S11 参数。复用现有控制器的 get_s11_parameters 或 get_s_parameters_full。"""

    name = "read_s11"

    def run(self, full: bool = False, controller: Any = None, **kwargs: Any) -> ToolResult:
        """
        Args:
            full: True 时尝试读取全部 S 参数（S11/S12/S21/S22），需控制器支持 get_s_parameters_full
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
        full = kwargs.get("full", full)
        try:
            if full and hasattr(ctrl, "get_s_parameters_full"):
                result = ctrl.get_s_parameters_full()
            else:
                result = ctrl.get_s11_parameters()

            if result.get("success"):
                data = {
                    "frequencies_GHz": result.get("frequencies_GHz", []),
                    "s11_dB": result.get("s11_dB", []),
                    "s11_min_dB": result.get("s11_min_dB"),
                    "freq_at_min_GHz": result.get("freq_at_min_GHz"),
                    "bandwidth_10dB_MHz": result.get("bandwidth_10dB_MHz"),
                }
                if "channels" in result:
                    data["channels"] = result["channels"]
                if "summary" in result:
                    data["summary"] = result["summary"]
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    tool_name=self.name,
                    message=result.get("message", "成功读取 S11"),
                    data=data,
                )
            return ToolResult(
                status=ToolStatus.FAILED,
                tool_name=self.name,
                message=result.get("message", "读取 S11 失败"),
                error=result.get("message", "unknown"),
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                tool_name=self.name,
                message=str(e),
                error=str(e),
            )
