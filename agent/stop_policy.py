"""
StopPolicy：判断是否停止或换路线。
支持“换路线而非直接停止”机制。
"""

from dataclasses import dataclass
from typing import Optional

from .models import EvaluationResult


@dataclass
class StopDecision:
    """停止/换路线决策"""
    should_stop: bool
    reason: str
    switch_route: bool = False
    next_route: Optional[str] = None


class StopPolicy:
    """
    停止策略。
    根据评估结果、迭代次数判断：结束、换路线、或继续。
    """

    def should_stop(
        self,
        evaluation: EvaluationResult,
        iteration: int,
        max_iterations: int,
        execution_failed: bool = False,
        routes_available: bool = True,
    ) -> StopDecision:
        """
        判断是否停止或换路线。

        Args:
            evaluation: 本轮评估结果
            iteration: 当前迭代次数
            max_iterations: 最大迭代次数
            execution_failed: 执行是否失败
            routes_available: 是否还有可换路线

        Returns:
            StopDecision: 含 switch_route、next_route
        """
        if execution_failed:
            return StopDecision(should_stop=True, reason="执行失败")

        if evaluation.all_ok:
            return StopDecision(should_stop=True, reason="设计已达标")

        if iteration >= max_iterations:
            return StopDecision(should_stop=True, reason=f"已达最大迭代次数 {max_iterations}")

        return StopDecision(should_stop=False, reason="继续迭代")

    def decide(
        self,
        evaluation: EvaluationResult,
        iteration: int,
        max_iterations: int,
        execution_failed: bool = False,
        current_hypothesis: Optional[dict] = None,
    ) -> StopDecision:
        """
        完整决策：优先尝试换路线，无路可换时再停止。
        """
        if execution_failed:
            return StopDecision(should_stop=True, reason="执行失败")

        if evaluation.all_ok:
            return StopDecision(should_stop=True, reason="设计已达标")

        if iteration >= max_iterations:
            return StopDecision(should_stop=True, reason=f"已达最大迭代次数 {max_iterations}")

        hypothesis = current_hypothesis or {}
        route = hypothesis.get("route", "continue_tune")
        structure_type = hypothesis.get("structure_type", "single_pec")

        if evaluation.suggest_route_change:
            if route == "continue_tune" and structure_type == "single_pec":
                return StopDecision(
                    should_stop=False,
                    reason="连续无改善，建议切换结构",
                    switch_route=True,
                    next_route="switch_structure",
                )
            if route == "continue_tune" and structure_type == "three_layer":
                return StopDecision(
                    should_stop=True,
                    reason="已尝试切换结构仍无改善，停止",
                )
            return StopDecision(
                should_stop=True,
                reason="无更多路线可换，停止",
            )

        return StopDecision(should_stop=False, reason="继续迭代")
