"""
Kiko AI 助手：自然语言解析、S 参数说明、意图识别
"""

import json
import os
from typing import Any, Dict, List, Optional

# S 参数说明（供 AI 与用户理解）
S_PARAM_HINTS = """
S 参数说明（反射单元常用）：
- S11：端口1反射系数，回波损耗（dB），越负越好，-10dB 表示约 90% 功率被吸收/反射匹配
- S21：端口1到端口2传输系数，插入损耗
- S12：端口2到端口1传输系数
- S22：端口2反射系数
- 对于反射单元，通常关注 S11（反射/匹配特性）
"""


class KikoAI:
    """Kiko 专用 AI：解析用户自然语言，提取建模参数与意图。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
    ):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or self._load_key_from_config()
        self.base_url = base_url
        self.model = model
        if not self.api_key or self.api_key == "your-api-key-here":
            self.client = None
        else:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                self.client = None

    def _load_key_from_config(self) -> Optional[str]:
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f).get("deepseek_api_key")
        except Exception:
            pass
        return None

    def parse_user_intent(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        解析用户自然语言，提取：频率、结构参数、意图、S 参数需求。
        Returns:
            {
                "freq_center_GHz": float or None,
                "freq_min_GHz": float, "freq_max_GHz": float,
                "params": {"patch_length": 12, "patch_width": 10, ...},
                "intent": "model"|"simulate"|"optimize"|"query"|"unknown",
                "need_freq": bool,
                "s_params_focus": ["S11"] or ["S11","S21"] etc,
                "reply": "给用户的简短回复"
            }
        """
        context = context or {}
        if self.client is None:
            return self._fallback_parse(user_input)

        system = f"""你是 Kiko，CST 反射单元建模助手。根据用户自然语言，提取建模与仿真参数。

{S_PARAM_HINTS}

固定建模条件：Background（已配置）、Boundaries（FloquetPort，x/y unit cell，z expanded open），zmax=中心频率半波长。
求解频率需用户指定；若用户未提供，need_freq=true，reply 中礼貌提醒输入中心频率（GHz）。

支持的结构类型：single_pec=单层 PEC 贴片；three_layer=PEC 地板+介质基板+PEC 贴片（需 substrate_height、dielectric_er）。

必须严格返回 JSON：
{{
  "freq_center_GHz": 数值或null,
  "freq_min_GHz": 数值,
  "freq_max_GHz": 数值,
  "params": {{"patch_length": 12, "patch_width": 10, "substrate_height": 1.6, "dielectric_er": 4.4, ...}},
  "structure_plan": {{"structure_type": "single_pec|three_layer", "params": {{...}}}},
  "intent": "model|simulate|optimize|query|unknown",
  "need_freq": true/false,
  "s_params_focus": ["S11"],
  "reply": "给用户的简短回复，中文"
}}

规则：
1. 从用户描述中提取频率（如 2.45GHz、2.4-2.5GHz）
2. 提取结构参数，可包含 patch_length、patch_width、substrate_height、dielectric_er、dielectric_tand
3. 若用户提到介质板、三层结构、PEC-介质-PEC，则 structure_plan.structure_type 为 three_layer
4. intent: model=新建/建模, simulate=仿真, optimize=优化, query=查询结果
5. 只输出 JSON，不要其他文字。"""

        user_content = f"用户输入：{user_input}\n\n当前上下文：{json.dumps(context, ensure_ascii=False)}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)
            return self._normalize_intent(result)
        except Exception as e:
            return self._fallback_parse(user_input, str(e))

    def _normalize_intent(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """规范化解析结果。"""
        out = {
            "freq_center_GHz": raw.get("freq_center_GHz"),
            "freq_min_GHz": float(raw.get("freq_min_GHz", 2.4)),
            "freq_max_GHz": float(raw.get("freq_max_GHz", 2.5)),
            "params": raw.get("params") or {},
            "structure_plan": raw.get("structure_plan") or {},
            "intent": str(raw.get("intent", "unknown")).lower(),
            "need_freq": bool(raw.get("need_freq", False)),
            "s_params_focus": raw.get("s_params_focus") or ["S11"],
            "reply": raw.get("reply", "已收到。"),
        }
        if out["freq_center_GHz"] is not None:
            out["freq_center_GHz"] = float(out["freq_center_GHz"])
        if out["freq_center_GHz"] is None and not out["need_freq"]:
            out["freq_center_GHz"] = (out["freq_min_GHz"] + out["freq_max_GHz"]) / 2.0
        return out

    def _fallback_parse(self, user_input: str, err: str = "") -> Dict[str, Any]:
        """无 API 时的简单规则解析。"""
        s = user_input.lower()
        params = {}
        freq = None
        if "2.45" in user_input or "2.45ghz" in s:
            freq = 2.45
        elif "2.4" in user_input:
            freq = 2.4
        elif "3ghz" in s or "3 ghz" in s:
            freq = 3.0
        import re
        m = re.search(r"(\d+\.?\d*)\s*[x×]\s*(\d+\.?\d*)", user_input, re.I)
        if m:
            params["patch_length"] = float(m.group(1))
            params["patch_width"] = float(m.group(2))
        m2 = re.search(r"贴片\s*(\d+\.?\d*)\s*[x×,，]\s*(\d+\.?\d*)", user_input)
        if m2:
            params["patch_length"] = float(m2.group(1))
            params["patch_width"] = float(m2.group(2))
        if not params:
            params = {"patch_length": 12.0, "patch_width": 10.0}
        need_freq = freq is None and ("频率" in user_input or "ghz" in s or "仿真" in user_input or "建模" in user_input)
        return {
            "freq_center_GHz": freq,
            "freq_min_GHz": (freq - 0.05) if freq else 2.4,
            "freq_max_GHz": (freq + 0.05) if freq else 2.5,
            "params": params,
            "intent": "model" if "建模" in user_input or "设计" in user_input else "simulate",
            "need_freq": need_freq,
            "s_params_focus": ["S11"],
            "reply": "请提供中心频率（GHz）" if need_freq else f"已解析：频率{freq or '待定'}GHz，参数{params}",
        }

    def explain_s_params(self, s_results: Dict[str, Any]) -> str:
        """根据 S 参数结果生成用户可读说明。"""
        summary = (s_results.get("s_params") or {}).get("summary") or {}
        channels = (s_results.get("s_params") or {}).get("channels") or {}
        lines = []
        if summary:
            s11_min = summary.get("s11_min_dB")
            freq_at = summary.get("freq_at_min_GHz")
            bw = summary.get("bandwidth_10dB_MHz")
            if s11_min is not None:
                lines.append(f"S11 最小值：{s11_min:.2f} dB")
            if freq_at is not None:
                lines.append(f"谐振频率：{freq_at:.3f} GHz")
            if bw is not None:
                lines.append(f"10dB 带宽：{bw:.1f} MHz")
        if channels:
            lines.append(f"已获取 S 参数：{list(channels.keys())}")
        return "；".join(lines) if lines else "暂无 S 参数结果"
