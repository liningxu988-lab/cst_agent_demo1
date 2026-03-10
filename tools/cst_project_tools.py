"""
CST 项目相关工具。
复用 scripts/cst_controller.py、cst_python_api_controller.py 等 open_project 逻辑。
"""

from typing import Any

from .base import BaseTool, ToolResult, ToolStatus
from .cst_context import get_controller


class OpenProjectTool(BaseTool):
    """打开 CST 项目。复用现有控制器的 open_project。"""

    name = "open_project"

    def run(self, project_path: str = "", controller: Any = None, **kwargs: Any) -> ToolResult:
        """
        Args:
            project_path: 项目路径（.cst 文件或包含 .cst 的目录）
            controller: 可选，未传则从上下文获取
        """
        ctrl = controller or get_controller()
        if ctrl is None:
            return ToolResult(
                status=ToolStatus.FAILED,
                tool_name=self.name,
                message="未注入 CST 控制器",
                error="controller not set, call tools.cst_context.set_controller() first",
            )
        if not project_path:
            return ToolResult(
                status=ToolStatus.FAILED,
                tool_name=self.name,
                message="project_path 不能为空",
                error="project_path is required",
            )
        try:
            ok = ctrl.open_project(project_path)
            if ok:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    tool_name=self.name,
                    message=f"已打开项目: {project_path}",
                    data={"project_path": project_path, "opened": True},
                )
            return ToolResult(
                status=ToolStatus.FAILED,
                tool_name=self.name,
                message="打开项目失败",
                data={"project_path": project_path},
                error="open_project returned False",
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILED,
                tool_name=self.name,
                message=str(e),
                data={"project_path": project_path},
                error=str(e),
            )
