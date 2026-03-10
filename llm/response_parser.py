"""
LLM 响应解析。
将模型输出的 JSON 解析为结构化 ActionPlan / EvaluationResult。
"""

from typing import Any, Dict, Optional, Tuple

from .json_repair import parse_json, validate_action_plan
from .models import LLMAction, LLMActionPlan


def parse_action_plan(raw: str) -> Tuple[Optional[LLMActionPlan], Optional[str]]:
    """
    解析 LLM 输出为 LLMActionPlan。

    Args:
        raw: 模型返回的原始文本

    Returns:
        (LLMActionPlan, None) 成功；或 (None, 错误信息)
    """
    data, err = parse_json(raw)
    if err:
        return None, err

    if not isinstance(data, dict):
        return None, "输出不是 JSON 对象"

    data = validate_action_plan(data)

    actions = []
    for a in data.get("actions", []):
        if isinstance(a, dict) and a.get("tool"):
            actions.append(LLMAction(tool=str(a["tool"]), kwargs=dict(a.get("kwargs", {}))))
    param_changes = data.get("parameter_changes", {})
    if isinstance(param_changes, dict):
        param_changes = {k: float(v) for k, v in param_changes.items() if isinstance(v, (int, float)) and not str(k).startswith("_")}

    return LLMActionPlan(
        stop=bool(data.get("stop", False)),
        reason=str(data.get("reason", "")),
        actions=actions,
        parameter_changes=param_changes,
    ), None


def parse_legacy_design_result(data: Dict[str, Any]) -> LLMActionPlan:
    """
    将旧 ai_client.analyze_design 返回格式兼容为 LLMActionPlan。
    用于适配器迁移。
    """
    stop_decision = data.get("stop_decision", {})
    stop = bool(stop_decision.get("stop", False))
    reason = str(stop_decision.get("reason", ""))
    param_plan = data.get("parameter_plan", {})
    changes = param_plan.get("changes", data.get("parameter_changes", {}))
    if isinstance(changes, dict):
        changes = {k: float(v) for k, v in changes.items() if isinstance(v, (int, float)) and not str(k).startswith("_")}

    actions = []
    if changes:
        actions.append(LLMAction("set_parameter", {"params": changes}))
    actions.append(LLMAction("run_solver", {"wait_complete": True}))
    actions.append(LLMAction("read_s11", {}))

    return LLMActionPlan(stop=stop, reason=reason, actions=actions, parameter_changes=changes)
