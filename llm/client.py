"""
LLM 调用封装。
保持与 ai_client.py 兼容，通过适配器方式逐步迁移。
"""

import json
import os
from typing import Any, Dict, List, Optional

from .message_builder import MessageBuilder
from .response_parser import parse_action_plan


class LLMClient:
    """
    LLM 客户端。
    约束模型输出 JSON，不允许直接输出自然语言执行指令。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
    ):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or self._load_key_from_config()
        self.base_url = base_url
        self.model = model
        self._client = None
        self.message_builder = MessageBuilder()

    def _load_key_from_config(self) -> Optional[str]:
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f).get("deepseek_api_key")
        except Exception:
            pass
        return None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                raise RuntimeError("需要安装 openai 库: pip install openai")
        return self._client

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        调用 chat completions API。
        默认使用 response_format={"type": "json_object"} 约束输出 JSON。
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format is None:
            response_format = {"type": "json_object"}
        kwargs["response_format"] = response_format

        resp = self._get_client().chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    def plan_for_design(
        self,
        goals: Dict[str, Any],
        current_params: Dict[str, float],
        current_results: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None,
        param_bounds: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        调用 LLM 生成设计调参计划，返回结构化 ActionPlan。

        Returns:
            [{"tool": str, "kwargs": dict}, ...] 或解析失败时抛出。
        """
        messages = self.message_builder.build_planner_messages(
            goals, current_params, current_results, history, param_bounds
        )
        raw = self.chat(messages)
        plan, err = parse_action_plan(raw)
        if err:
            raise RuntimeError(f"LLM 输出解析失败: {err}")
        if plan.stop:
            return []
        return [{"tool": a.tool, "kwargs": a.kwargs} for a in plan.actions]


def create_from_config(config: Optional[Dict[str, Any]] = None) -> LLMClient:
    """从配置创建 LLMClient，与 cst_runner 的 config 兼容。"""
    cfg = config if isinstance(config, dict) else {}
    return LLMClient(
        api_key=cfg.get("deepseek_api_key", "") or cfg.get("api_key") or os.getenv("DEEPSEEK_API_KEY"),
        base_url=cfg.get("deepseek_base_url", "https://api.deepseek.com"),
        model=cfg.get("deepseek_model", "deepseek-chat"),
    )
