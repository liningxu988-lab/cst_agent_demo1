"""
LLM 消息构建。
构建 system / user 消息，约束输出为 JSON。
"""

import json
from typing import Any, Dict, List, Optional


class MessageBuilder:
    """消息构建器"""

    PLANNER_SYSTEM = """你是一个 CST 电磁仿真与天线设计专家。你的任务是输出**结构化 JSON**，不得输出自然语言执行指令。

你必须严格返回以下 JSON 格式，不要输出其他文字：
```json
{
  "stop": true/false,
  "reason": "停止或继续的原因",
  "actions": [
    {"tool": "set_parameter", "kwargs": {"params": {"参数名": 数值}}},
    {"tool": "run_solver", "kwargs": {"wait_complete": true}},
    {"tool": "read_s11", "kwargs": {}}
  ],
  "parameter_changes": {"参数名": 数值}
}
```

允许的 tool：open_project, set_parameter, run_solver, read_s11。
规则：
1. 只输出 JSON，不要输出 markdown 或其他说明。
2. parameter_changes 与 actions 中 set_parameter 的 params 应一致。
3. stop=true 表示停止迭代；stop=false 时 actions 必须包含 set_parameter、run_solver、read_s11。
4. 参数值必须为数字，不得越界。"""

    def build_planner_messages(
        self,
        goals: Dict[str, Any],
        current_params: Dict[str, float],
        current_results: Dict[str, Any],
        history: Optional[List[Dict[str, Any]]] = None,
        param_bounds: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        """构建 planner 调用的 messages。"""
        user_content = (
            "设计目标(JSON):\n"
            f"{json.dumps(goals, indent=2, ensure_ascii=False)}\n\n"
            "当前参数:\n"
            f"{json.dumps(current_params, indent=2, ensure_ascii=False)}\n\n"
            "当前仿真结果:\n"
            f"{json.dumps(current_results, indent=2, ensure_ascii=False)}\n\n"
            "参数边界:\n"
            f"{json.dumps(param_bounds or {}, indent=2, ensure_ascii=False)}\n\n"
            "最近历史(最多3轮):\n"
            f"{json.dumps((history or [])[-3:], indent=2, ensure_ascii=False)}\n\n"
            "请输出 JSON。"
        )
        return [
            {"role": "system", "content": self.PLANNER_SYSTEM},
            {"role": "user", "content": user_content},
        ]

    def build_custom_messages(
        self,
        system_prompt: str,
        user_content: str,
    ) -> List[Dict[str, str]]:
        """构建自定义 messages。"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
