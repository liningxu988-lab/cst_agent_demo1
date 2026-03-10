"""
JSON 轻量修复与校验。
当模型输出 JSON 不合法时，自动做修复尝试。
"""

import json
import re
from typing import Any, Optional, Tuple


def repair_json(raw: str) -> Tuple[str, bool]:
    """
    尝试修复常见 JSON 格式问题。

    Args:
        raw: 原始字符串

    Returns:
        (修复后字符串, 是否已修复)
    """
    text = raw.strip()
    repaired = False

    # 1. 去除 markdown 代码块
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
        repaired = True

    # 2. 去除首尾非 JSON 字符（如说明文字）
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]
        repaired = repaired or (start > 0 or end < len(text))

    # 3. 修复尾随逗号（JSON 不允许）
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    if "," in text and (", }" in text or ", ]" in text):
        repaired = True

    # 4. 单引号转双引号（简单情况）
    if "'" in text and '"' not in text:
        text = text.replace("'", '"')
        repaired = True

    # 5. 去除控制字符
    text = "".join(c for c in text if ord(c) >= 32 or c in "\n\t")
    if len(text) != len(raw):
        repaired = True

    return text, repaired


def parse_json(raw: str) -> Tuple[Optional[dict], Optional[str]]:
    """
    解析 JSON，失败时尝试修复后重试。

    Args:
        raw: 原始字符串

    Returns:
        (解析结果 dict，None 表示成功；或 None，错误信息)
    """
    text = raw.strip()
    err_msg = None

    try:
        return json.loads(text), None
    except json.JSONDecodeError as e:
        err_msg = str(e)

    repaired, _ = repair_json(raw)
    if repaired != raw.strip():
        try:
            return json.loads(repaired), None
        except json.JSONDecodeError as e2:
            err_msg = f"修复后仍失败: {e2}"

    return None, err_msg or "JSON 解析失败"


def validate_action_plan(d: dict) -> dict:
    """
    校验并补全 ActionPlan 结构。
    缺失字段用默认值填充。
    """
    out = dict(d)
    if "stop" not in out:
        out["stop"] = False
    if "reason" not in out:
        out["reason"] = ""
    if "actions" not in out:
        out["actions"] = []
    if "parameter_changes" not in out:
        out["parameter_changes"] = out.get("parameter_plan", {}).get("changes", {}) or {}
    actions = out.get("actions", [])
    if not isinstance(actions, list):
        out["actions"] = []
    else:
        out["actions"] = [
            {"tool": a.get("tool", ""), "kwargs": a.get("kwargs", {}) if isinstance(a, dict) else {}}
            for a in actions
            if isinstance(a, dict) and a.get("tool")
        ]
    return out
