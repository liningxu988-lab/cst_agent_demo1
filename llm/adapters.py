"""
适配器：将旧 ai_client 接入新 LLM 结构化流程。
不破坏现有 DeepSeek 接入方式，可逐步迁移。
"""

from typing import Any, Dict, List, Optional

from .models import LLMActionPlan
from .response_parser import parse_legacy_design_result


class DeepSeekToLLMAdapter:
    """
    将 scripts.ai_client.DeepSeekClient 的 analyze_design 返回值
    适配为 LLMActionPlan，供 agent 使用。
    """

    def __init__(self, ai_client: Any):
        """
        Args:
            ai_client: DeepSeekClient 实例（或兼容接口）
        """
        self.ai_client = ai_client

    def plan_for_design(
        self,
        design_task: Dict[str, Any],
        current_params: Dict[str, float],
        current_results: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> LLMActionPlan:
        """
        调用旧 analyze_design，将返回结果转为 LLMActionPlan。
        """
        result = self.ai_client.analyze_design(
            design_task=design_task,
            current_params=current_params,
            current_results=current_results,
            history=history,
        )
        return parse_legacy_design_result(result)
