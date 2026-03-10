"""
Agent 结构化输出模型。
所有输出必须结构化，禁止自由文本驱动执行。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Action:
    """单步动作"""
    tool: str
    kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionPlan:
    """执行计划。planner 输出，executor 执行。"""
    actions: List[Action] = field(default_factory=list)
    route: str = "continue_tune"  # continue_tune | switch_structure | param_sweep | stop_route

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actions": [{"tool": a.tool, "kwargs": a.kwargs} for a in self.actions],
            "route": self.route,
        }


@dataclass
class EvaluationResult:
    """evaluator 输出"""
    score: float
    all_ok: bool
    s11_min_dB: float
    freq_at_min_GHz: float
    details: Dict[str, Any] = field(default_factory=dict)
    next_params: Dict[str, float] = field(default_factory=dict)
    no_improvement_count: int = 0
    suggest_route_change: bool = False
