"""
LLM 模块最小测试。
不调用真实 API，仅测试解析与修复逻辑。
"""

import unittest

from llm.json_repair import parse_json, repair_json, validate_action_plan
from llm.response_parser import parse_action_plan, parse_legacy_design_result
from llm.models import LLMActionPlan


class TestLLM(unittest.TestCase):
    """LLM 模块测试"""

    def test_repair_json_markdown(self):
        """修复 markdown 代码块"""
        raw = '说明：请参考\n```json\n{"a": 1}\n```'
        repaired, changed = repair_json(raw)
        self.assertTrue(changed)
        self.assertIn('"a": 1', repaired)

    def test_parse_json_repair(self):
        """解析并修复 JSON"""
        raw = '```json\n{"stop": false, "actions": []}\n```'
        data, err = parse_json(raw)
        self.assertIsNone(err)
        self.assertEqual(data.get("stop"), False)

    def test_parse_action_plan(self):
        """解析 ActionPlan"""
        raw = '{"stop": false, "reason": "继续", "actions": [{"tool": "set_parameter", "kwargs": {"params": {"x": 1}}}], "parameter_changes": {"x": 1}}'
        plan, err = parse_action_plan(raw)
        self.assertIsNone(err)
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].tool, "set_parameter")

    def test_parse_action_plan_with_trailing_comma(self):
        """解析带尾随逗号的 JSON"""
        raw = '{"stop": false, "actions": [{"tool": "read_s11", "kwargs": {}},], "parameter_changes": {}}'
        plan, err = parse_action_plan(raw)
        self.assertIsNone(err)

    def test_validate_action_plan(self):
        """校验并补全 ActionPlan"""
        d = {"stop": True}
        out = validate_action_plan(d)
        self.assertIn("actions", out)
        self.assertIn("parameter_changes", out)
        self.assertEqual(out["reason"], "")

    def test_parse_legacy_design_result(self):
        """兼容旧 ai_client 返回格式"""
        legacy = {
            "stop_decision": {"stop": False, "reason": "继续"},
            "parameter_plan": {"changes": {"patch_length": 11.5}},
        }
        plan = parse_legacy_design_result(legacy)
        self.assertFalse(plan.stop)
        self.assertEqual(plan.parameter_changes.get("patch_length"), 11.5)
        self.assertGreater(len(plan.actions), 0)


if __name__ == "__main__":
    unittest.main()
