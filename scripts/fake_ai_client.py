"""
模拟 AI 客户端（用于测试，不调用真实 API）
"""

import json
from typing import Any, Dict, List


class FakeDeepSeekClient:
    """模拟 DeepSeek 客户端，用于测试程序流程"""

    def __init__(self, *args, **kwargs):
        print("[FakeAI] 初始化模拟 AI 客户端（不调用真实 API）")
        self.iteration_count = 0

    def analyze_design(
        self,
        design_task: Dict[str, Any],
        current_params: Dict[str, float],
        current_results: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        基于简单规则模拟 AI 决策
        """
        self.iteration_count += 1

        s_params = current_results.get("s_params", {})
        s_summary = s_params.get("summary", {}) if isinstance(s_params, dict) else {}
        s11_min = float(s_summary.get("s11_min_dB", -999))
        freq_at_min = float(s_summary.get("freq_at_min_GHz", 0))

        goals = design_task.get("goals", {})
        freq_range = goals.get("freq_range_GHz", [2.4, 2.5])
        freq_min = float(freq_range[0])
        freq_max = float(freq_range[1])
        s11_threshold = float(goals.get("s11_max_dB", -10.0))

        s11_ok = s11_min <= s11_threshold
        freq_ok = freq_min <= freq_at_min <= freq_max

        if s11_ok and freq_ok:
            return {
                "stop_decision": {"stop": True, "reason": "设计已满足所有指标要求"},
                "parameter_plan": {"changes": {}, "rationale": "无需调参"},
                "result_plan": {"channels": ["s_params"], "focus": "确认最终指标"},
                "analysis": f"S11={s11_min:.2f}dB 满足要求，谐振频率={freq_at_min:.3f}GHz 在目标范围内",
            }

        new_params = {}
        if s11_min > s11_threshold:
            current_width = current_params.get("patch_width", 10.0)
            new_params["patch_width"] = round(current_width + 0.5, 2)
        if freq_at_min < freq_min:
            current_length = current_params.get("patch_length", 12.0)
            new_params["patch_length"] = round(current_length - 0.5, 2)
        elif freq_at_min > freq_max:
            current_length = current_params.get("patch_length", 12.0)
            new_params["patch_length"] = round(current_length + 0.5, 2)

        return {
            "stop_decision": {
                "stop": False,
                "reason": f"S11={s11_min:.2f}dB 不满足要求，或频率 {freq_at_min:.3f}GHz 不在目标范围内",
            },
            "parameter_plan": {
                "changes": new_params,
                "rationale": "基于简单规则调整参数以逼近目标",
            },
            "result_plan": {"channels": ["s_params"], "focus": "优先改善S参数匹配"},
            "analysis": "基于简单规则调整参数以逼近目标",
        }

    def analyze_cst_error(
        self,
        design_task: Dict[str, Any],
        error_report: Dict[str, Any],
        current_params: Dict[str, float],
        port_plan: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """模拟：根据错误类型返回简单修复方案。"""
        stage = error_report.get("stage", "")
        msg = error_report.get("message", "")
        cst = error_report.get("cst_report", {})

        # 端口相关错误
        if "port" in msg.lower() or "excitation" in msg.lower():
            return {
                "retry": True,
                "reasoning": "端口或激励设置可能有问题，尝试使用 Full 坐标的 waveguide port",
                "fix_plan": {
                    "parameter_changes": {},
                    "port_plan": {
                        "waveguide_port": {
                            "orientation": "zmin",
                            "coordinates": "Full",
                            "number_of_modes": 1,
                            "label": "port1",
                        }
                    },
                    "solver_hint": "",
                    "boundary_hint": "",
                },
            }

        # 参数/建模错误：微调参数
        if "parameter" in stage.lower() or "rebuild" in msg.lower():
            changes = {}
            for k in ["patch_length", "patch_width"]:
                if k in current_params and isinstance(current_params[k], (int, float)):
                    changes[k] = round(float(current_params[k]) * 0.98, 2)
            if not changes:
                changes = {"patch_width": max(5.0, float(current_params.get("patch_width", 10)) - 0.5)}
            return {
                "retry": True,
                "reasoning": "参数设置或重建失败，尝试微调参数后重试",
                "fix_plan": {
                    "parameter_changes": changes,
                    "port_plan": port_plan or {},
                    "solver_hint": "",
                    "boundary_hint": "",
                },
            }

        # 默认：重试一次，不改参数
        return {
            "retry": True,
            "reasoning": "未知错误，尝试保持当前配置重试",
            "fix_plan": {
                "parameter_changes": {},
                "port_plan": port_plan or {},
                "solver_hint": "",
                "boundary_hint": "",
            },
        }
