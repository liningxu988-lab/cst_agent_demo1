"""
任务与设计领域模型。
用于 Agent 结构化决策，禁止自由文本直接驱动执行。
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class DesignTarget:
    """设计目标"""
    freq_min_GHz: float = 0.0
    freq_max_GHz: float = 0.0
    s11_max_dB: float = -10.0
    extra: Dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.extra is None:
            self.extra = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "freq_min_GHz": self.freq_min_GHz,
            "freq_max_GHz": self.freq_max_GHz,
            "s11_max_dB": self.s11_max_dB,
            **self.extra,
        }


@dataclass
class DesignParams:
    """设计参数"""
    params: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.params)


@dataclass
class DesignTask:
    """设计任务"""
    task_id: str
    params: DesignParams
    targets: DesignTarget
    max_iterations: int = 10
    meta: Dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.meta is None:
            self.meta = {}


@dataclass
class AgentDecision:
    """
    Agent 结构化决策。
    禁止自由文本直接驱动执行，必须解析为具体动作。
    """
    action: str  # 如: update_params, run_sim, read_result, finish, retry
    params: Optional[Dict[str, Any]] = None
    reason: str = ""
    extra: Dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.extra is None:
            self.extra = {}
