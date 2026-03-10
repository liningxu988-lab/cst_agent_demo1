"""
Evaluator：分析执行结果，给出本轮评价。
基于目标频点和 S11 评分，含连续无改善检测。
"""

from typing import Any, Dict, List, Optional

from tools.base import ToolResult

from .models import EvaluationResult


class Evaluator:
    """
    评估器。
    从 read_s11 的 ToolResult 中提取 S11 数据，与 targets 对比评分。
    支持连续无改善检测，触发 suggest_route_change。
    """

    NO_IMPROVEMENT_THRESHOLD = 3

    def evaluate(
        self,
        tool_results: List[ToolResult],
        targets: Dict[str, Any],
        current_params: Optional[Dict[str, float]] = None,
        recent_scores: Optional[List[float]] = None,
    ) -> EvaluationResult:
        """
        评估执行结果。

        Args:
            tool_results: executor 返回的 ToolResult 列表
            targets: 设计目标
            current_params: 当前参数
            recent_scores: 最近 N 轮 score，用于无改善检测

        Returns:
            EvaluationResult: 含 no_improvement_count、suggest_route_change
        """
        freq_min = float(targets.get("freq_min_GHz", 2.4))
        freq_max = float(targets.get("freq_max_GHz", 2.5))
        s11_threshold = float(targets.get("s11_max_dB", -10.0))

        s11_min_dB = 0.0
        freq_at_min_GHz = 0.0
        read_ok = False

        for r in tool_results:
            if r.tool_name == "read_s11" and r.status.value == "success":
                data = r.data or {}
                s11_min_dB = float(data.get("s11_min_dB", 0))
                freq_at_min_GHz = float(data.get("freq_at_min_GHz", 0))
                read_ok = True
                break

        if not read_ok:
            return EvaluationResult(
                score=0.0,
                all_ok=False,
                s11_min_dB=0.0,
                freq_at_min_GHz=0.0,
                details={"error": "read_s11 failed or not in results"},
                no_improvement_count=0,
                suggest_route_change=False,
            )

        s11_ok = s11_min_dB <= s11_threshold
        freq_ok = freq_min <= freq_at_min_GHz <= freq_max
        all_ok = s11_ok and freq_ok

        score = self._compute_score(s11_min_dB, freq_at_min_GHz, s11_threshold, freq_min, freq_max)

        no_improvement_count, suggest_route_change = self._detect_no_improvement(
            score, recent_scores or []
        )

        current = dict(current_params or {})
        next_params = self._suggest_next_params(
            s11_min_dB, freq_at_min_GHz, freq_min, freq_max, s11_threshold, current
        )

        return EvaluationResult(
            score=score,
            all_ok=all_ok,
            s11_min_dB=s11_min_dB,
            freq_at_min_GHz=freq_at_min_GHz,
            details={
                "s11_ok": s11_ok,
                "freq_ok": freq_ok,
                "s11_threshold": s11_threshold,
                "freq_range": [freq_min, freq_max],
            },
            next_params=next_params,
            no_improvement_count=no_improvement_count,
            suggest_route_change=suggest_route_change,
        )

    def _detect_no_improvement(
        self, current_score: float, recent_scores: List[float]
    ) -> tuple[int, bool]:
        """连续无改善检测。"""
        if not recent_scores:
            return 0, False
        scores = recent_scores + [current_score]
        count = 0
        best = scores[0]
        for s in scores[1:]:
            if s <= best:
                count += 1
            else:
                count = 0
                best = s
        suggest = count >= self.NO_IMPROVEMENT_THRESHOLD
        return count, suggest

    def _compute_score(
        self,
        s11_min_dB: float,
        freq_at_min_GHz: float,
        s11_threshold: float,
        freq_min: float,
        freq_max: float,
    ) -> float:
        """简单评分：0-100。"""
        s11_score = 50.0
        if s11_min_dB <= s11_threshold:
            s11_score = 50 + min(25, (s11_threshold - s11_min_dB) * 2)
        else:
            s11_score = max(0, 50 + (s11_min_dB - s11_threshold) * 5)

        freq_center = (freq_min + freq_max) / 2
        freq_span = freq_max - freq_min
        freq_dist = abs(freq_at_min_GHz - freq_center)
        freq_score = max(0, 50 - (freq_dist / max(freq_span * 0.5, 0.01)) * 25)

        return min(100.0, max(0.0, (s11_score + freq_score) / 2))

    def _suggest_next_params(
        self,
        s11_min_dB: float,
        freq_at_min_GHz: float,
        freq_min: float,
        freq_max: float,
        s11_threshold: float,
        current_params: Dict[str, float],
    ) -> Dict[str, float]:
        """简单规则：根据频率偏移建议下一轮参数。"""
        delta = 0.3
        params = dict(current_params)
        pl = params.get("patch_length", 10.0)
        pw = params.get("patch_width", 8.0)
        freq_center = (freq_min + freq_max) / 2
        if freq_at_min_GHz < freq_min:
            pl += delta
        elif freq_at_min_GHz > freq_max:
            pl -= delta
        if s11_min_dB > s11_threshold:
            pw += delta
        return {"patch_length": pl, "patch_width": pw}
