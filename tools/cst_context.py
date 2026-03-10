"""
CST 控制器上下文。
供 Tool 适配层获取当前 CST 控制器实例，由 cst_runner 或 Agent 在启动时注入。
"""

from typing import Any, Optional

# 全局控制器引用，由调用方通过 set_controller() 注入
_controller: Optional[Any] = None


def set_controller(ctrl: Any) -> None:
    """注入 CST 控制器实例。"""
    global _controller
    _controller = ctrl


def get_controller() -> Optional[Any]:
    """获取当前 CST 控制器。未注入时返回 None。"""
    return _controller


def clear_controller() -> None:
    """清除控制器引用（用于测试或资源释放）。"""
    global _controller
    _controller = None
