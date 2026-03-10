"""
DeepSeek AI 客户端模块
用于调用 DeepSeek API 进行设计决策
"""

import json
import os
from typing import Any, Dict, List, Optional


class DeepSeekClient:
    """DeepSeek API 客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
    ):
        """
        初始化 DeepSeek 客户端

        Args:
            api_key: API 密钥，如果不提供则从环境变量或配置文件读取
            base_url: API 基础 URL，默认使用 DeepSeek 官方地址
            model: 模型名称，默认使用 deepseek-chat
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or self._load_key_from_config()
        self.base_url = base_url
        self.model = model

        # 延迟导入 openai 库
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        except ImportError:
            raise RuntimeError(
                "需要安装 openai 库: pip install openai"
            )

        if not self.api_key:
            raise RuntimeError(
                "未提供 DeepSeek API Key。请:\n"
                "1. 在 config.json 中填写 api_key\n"
                "2. 或设置环境变量 DEEPSEEK_API_KEY"
            )

    def _load_key_from_config(self) -> Optional[str]:
        """从配置文件读取 API Key"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return config.get("deepseek_api_key")
        except Exception:
            pass
        return None

    def analyze_design(
        self,
        design_task: Dict[str, Any],
        current_params: Dict[str, float],
        current_results: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        多目标分析与调参决策（S参数/方向图）。

        Returns:
            {
              "stop_decision": {"stop": bool, "reason": str},
              "parameter_plan": {"changes": {"param": value}, "rationale": str},
              "result_plan": {"channels": ["s_params","radiation"], "focus": str},
              "analysis": str
            }
        """
        role_profile = design_task.get(
            "ai_role_profile",
            "你是一个天线与电磁领域的专家，具有充足的电磁仿真经验以及CST软件的建模与仿真经验，擅长超表面、天线罩、天线设计与调参。",
        )
        goals = design_task.get("goals", {})
        user_requirements = design_task.get("user_requirements", "")
        enabled_channels = design_task.get("enabled_result_channels", ["s_params"])
        param_bounds = design_task.get("parameter_bounds", {})

        # 构建 Prompt（简化：仅 S 参数）
        system_prompt = f"""{role_profile}

你需要基于当前仿真结果，输出下一轮调参计划。当前仿真仅使用频域求解器，返回全部 S 参数（S11、S12、S21、S22 等）
current_results.s_params.channels 包含各通道的 frequencies_GHz、magnitude_dB、phase_deg；summary 包含 s11_min_dB、freq_at_min_GHz、bandwidth_10dB_MHz。

必须严格返回 JSON，格式如下：
{{
  "stop_decision": {{"stop": true/false, "reason": "..." }},
  "parameter_plan": {{
    "changes": {{"参数名": 数值}},
    "rationale": "..."
  }},
  "structure_plan": {{
    "structure_type": "single_pec|three_layer",
    "params": {{"patch_length": 12, "patch_width": 10, "substrate_height": 1.6, "dielectric_er": 4.4, ...}}
  }},
  "result_plan": {{
    "channels": ["s_params"],
    "focus": "本轮优先关注项"
  }},
  "analysis": "详细分析"
}}

规则：
1. changes 可包含任意可调参数，不限于当前已有参数；你可自由添加 substrate_height、dielectric_er、dielectric_tand 等。
2. structure_plan 可选：若需改变模型结构（如单层 PEC→三层 PEC-介质-PEC），在 structure_plan 中指定 structure_type 和 params。
3. structure_type: single_pec=单层 PEC 贴片；three_layer=PEC 地板+介质基板+PEC 贴片，需 patch_length、patch_width、substrate_height、dielectric_er。
4. 如提供 parameter_bounds，参数不能越界。
5. 可综合 S11、S12、S21、S22 等全部 S 参数进行分析。
6. 只输出 JSON，不要输出其他文字。"""

        user_content = (
            "设计任务(JSON):\n"
            f"{json.dumps(goals, indent=2, ensure_ascii=False)}\n\n"
            "用户自然语言需求:\n"
            f"{user_requirements}\n\n"
            "已启用结果通道:\n"
            f"{json.dumps(enabled_channels, ensure_ascii=False)}\n\n"
            "参数边界:\n"
            f"{json.dumps(param_bounds, indent=2, ensure_ascii=False)}\n\n"
            "当前参数:\n"
            f"{json.dumps(current_params, indent=2, ensure_ascii=False)}\n\n"
            "当前仿真结果:\n"
            f"{json.dumps(current_results, indent=2, ensure_ascii=False)}\n\n"
            "最近历史(最多3轮):\n"
            f"{json.dumps(history[-3:], indent=2, ensure_ascii=False)}"
        )

        # 调用 API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        # 解析响应
        content = response.choices[0].message.content
        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"AI 返回结果解析失败: {content}") from e

        # 兼容与校验
        if "stop_decision" not in result:
            result["stop_decision"] = {
                "stop": bool(result.get("stop", False)),
                "reason": result.get("reason", "未提供原因"),
            }
        if "parameter_plan" not in result:
            result["parameter_plan"] = {"changes": result.get("new_params", {}), "rationale": result.get("analysis", "")}
        if "result_plan" not in result:
            result["result_plan"] = {"channels": enabled_channels, "focus": "默认读取已启用通道"}
        if "analysis" not in result:
            result["analysis"] = result.get("parameter_plan", {}).get("rationale", "")

        # 允许 AI 添加新参数，仅过滤非数值
        changes = result.get("parameter_plan", {}).get("changes", {})
        filtered = {}
        for key, value in changes.items():
            if isinstance(value, (int, float)) and not key.startswith("_"):
                filtered[key] = value
        result["parameter_plan"]["changes"] = filtered

        return result

    def analyze_cst_error(
        self,
        design_task: Dict[str, Any],
        error_report: Dict[str, Any],
        current_params: Dict[str, float],
        port_plan: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        分析 CST 错误报告，由 AI 决定修复方案并决定是否重试。

        Returns:
            {
              "retry": bool,
              "reasoning": str,
              "fix_plan": {
                "parameter_changes": {"param": value},
                "port_plan": {...},
                "solver_hint": "Transient|Frequency Domain|...",
                "boundary_hint": str
              }
            }
        """
        role_profile = design_task.get(
            "ai_role_profile",
            "你是一个天线与电磁领域的专家，具有充足的电磁仿真经验以及CST软件的建模与仿真经验，擅长超表面、天线罩、天线设计与调参。",
        )
        param_bounds = design_task.get("parameter_bounds", {})
        goals = design_task.get("goals", {})

        system_prompt = f"""{role_profile}

你正在接管 CST 建模与仿真的错误修复。当 CST 返回错误或仿真失败时，你需要根据错误报告分析原因，给出修复方案。
当前系统仅使用 HF Frequency Domain 频域求解器，仅提取 S 参数。

必须严格返回 JSON，格式如下：
{{
  "retry": true/false,
  "reasoning": "错误原因分析与修复思路",
  "fix_plan": {{
    "parameter_changes": {{"参数名": 数值}},
    "port_plan": {{}},
    "solver_hint": "HF Frequency Domain|空表示不改变",
    "boundary_hint": "若需修改边界条件的建议，否则空字符串"
  }}
}}

规则：
1. 仔细阅读 cst_report 中的 output_txt、model_log 等日志，定位具体错误（如端口未定义、网格失败、频率范围不当等）。
2. parameter_changes 只能包含 design_task 中已有的可调参数，且不能越界。
3. solver_hint 仅支持 "HF Frequency Domain" 或空字符串。
4. retry=false 表示你认为无法通过参数修复，应停止。
5. 只输出 JSON，不要输出其他文字。"""

        user_content = (
            "设计目标(JSON):\n"
            f"{json.dumps(goals, indent=2, ensure_ascii=False)}\n\n"
            "参数边界:\n"
            f"{json.dumps(param_bounds, indent=2, ensure_ascii=False)}\n\n"
            "当前参数:\n"
            f"{json.dumps(current_params, indent=2, ensure_ascii=False)}\n\n"
            "当前端口计划:\n"
            f"{json.dumps(port_plan, indent=2, ensure_ascii=False)}\n\n"
            "CST 错误报告:\n"
            f"{json.dumps(error_report, indent=2, ensure_ascii=False)}\n\n"
            "最近历史(最多2条):\n"
            f"{json.dumps(history[-2:], indent=2, ensure_ascii=False)}"
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"AI 错误分析解析失败: {content}") from e

        if "fix_plan" not in result:
            result["fix_plan"] = {}
        if "retry" not in result:
            result["retry"] = bool(result.get("parameter_changes") or result.get("port_plan"))

        # 过滤 parameter_changes 到已有参数
        changes = result.get("fix_plan", {}).get("parameter_changes", {})
        filtered = {}
        for key, value in changes.items():
            if key in current_params:
                filtered[key] = value
        result.setdefault("fix_plan", {})["parameter_changes"] = filtered

        return result


def quick_test():
    """快速测试 AI 客户端"""
    client = DeepSeekClient()

    # 模拟数据
    design_task = {
        "goals": {"s11_max_dB": -10.0, "freq_range_GHz": [2.4, 2.5]},
        "enabled_result_channels": ["s_params"],
    }
    current_params = {"patch_length": 12.0, "patch_width": 10.0}
    current_results = {
        "s_params": {
            "channels": {"S11": {"frequencies_GHz": [2.4, 2.45, 2.5], "magnitude_dB": [-9, -8.5, -9]}},
            "summary": {"s11_min_dB": -8.5, "freq_at_min_GHz": 2.35, "bandwidth_10dB_MHz": 50},
        }
    }
    history = []

    result = client.analyze_design(design_task, current_params, current_results, history)
    print("AI 决策结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    quick_test()
