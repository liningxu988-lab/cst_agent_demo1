"""
S-Parameter Optimizer Skill。
S11 优化迭代，复用 set_parameter、run_solver、read_s11。
"""

from typing import Any, Dict

from skills.base_skill import BaseSkill, SkillMeta


class SParamOptimizerSkill(BaseSkill):
    """S 参数优化 Skill"""

    meta = SkillMeta(
        name="sparam_optimizer",
        description="S11 目标优化，迭代调参直至达标或达最大迭代次数",
        tools=["set_parameter", "run_solver", "read_s11"],
        scenarios=["s11_optimization", "antenna_tuning", "reflection_tuning"],
    )

    def run(self, context: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        """
        执行单轮 S 参数优化。
        kwargs: params, targets, ...
        内部复用 tools，不重复实现仿真逻辑。
        """
        registry = context.get("tool_registry")
        params = kwargs.get("params", {})
        targets = kwargs.get("targets", {})

        if not registry:
            return {"success": False, "error": "tool_registry not in context"}

        r1 = registry.run("set_parameter", params=params)
        if r1.status.value == "failed":
            return {"success": False, "step": "set_parameter", "error": r1.error}

        r2 = registry.run("run_solver", wait_complete=True)
        if r2.status.value == "failed":
            return {"success": False, "step": "run_solver", "error": r2.error}

        r3 = registry.run("read_s11")
        if r3.status.value == "failed":
            return {"success": False, "step": "read_s11", "error": r3.error}

        data = r3.data or {}
        s11_min = data.get("s11_min_dB", 0)
        freq_at_min = data.get("freq_at_min_GHz", 0)
        freq_min = float(targets.get("freq_min_GHz", 2.4))
        freq_max = float(targets.get("freq_max_GHz", 2.5))
        s11_threshold = float(targets.get("s11_max_dB", -10.0))

        all_ok = (s11_min <= s11_threshold) and (freq_min <= freq_at_min <= freq_max)

        return {
            "success": True,
            "s11_min_dB": s11_min,
            "freq_at_min_GHz": freq_at_min,
            "all_ok": all_ok,
            "params_used": params,
        }
