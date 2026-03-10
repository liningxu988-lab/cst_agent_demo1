"""
LLM 结构化输出数据模型。
约束模型输出 JSON，不允许直接输出自然语言执行指令。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMAction:
    """LLM 输出的单步动作"""
    tool: str
    kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMActionPlan:
    """
    LLM 输出的 ActionPlan 结构。
    与 agent.models.ActionPlan 兼容，可转换。
    """
    stop: bool = False
    reason: str = ""
    actions: List[LLMAction] = field(default_factory=list)
    parameter_changes: Dict[str, float] = field(default_factory=dict)

    def to_agent_plan(self) -> "ActionPlan":
        """转换为 agent.ActionPlan"""
        from agent.models import Action, ActionPlan
        return ActionPlan(actions=[Action(a.tool, a.kwargs) for a in self.actions])


@dataclass
class LLMEvaluationResult:
    """
    LLM 输出的评估/决策结构。
    与 agent.models.EvaluationResult 兼容。
    """
    score: float = 0.0
    all_ok: bool = False
    s11_min_dB: float = 0.0
    freq_at_min_GHz: float = 0.0
    stop: bool = False
    reason: str = ""
    next_params: Dict[str, float] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
