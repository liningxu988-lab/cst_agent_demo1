"""
工具基类与统一返回类型。
所有 Agent 工具必须返回 ToolResult，禁止自由文本直接驱动执行。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ToolStatus(str, Enum):
    """工具执行状态"""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ToolResult:
    """
    统一工具返回结构。
    所有工具必须返回此类型，便于 Agent 解析与状态持久化。
    """
    status: ToolStatus
    tool_name: str
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "tool_name": self.tool_name,
            "message": self.message,
            "data": self.data,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ToolResult":
        return cls(
            status=ToolStatus(d.get("status", "failed")),
            tool_name=d.get("tool_name", ""),
            message=d.get("message", ""),
            data=d.get("data", {}),
            error=d.get("error"),
        )


class BaseTool:
    """工具基类"""
    name: str = "base"

    def run(self, **kwargs: Any) -> ToolResult:
        """执行工具，返回 ToolResult。子类必须实现。"""
        raise NotImplementedError
