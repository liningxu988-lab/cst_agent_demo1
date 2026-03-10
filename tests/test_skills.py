"""
Skills 模块最小测试。
"""

import unittest

from tools import set_controller, get_registry
from scripts.cst_controller import FakeCSTController
from skills import load_all_skills, get_skill_by_scenario


class TestSkills(unittest.TestCase):
    """Skills 测试"""

    def setUp(self):
        ctrl = FakeCSTController()
        ctrl.connect()
        set_controller(ctrl)

    def test_load_all_skills(self):
        """加载所有 Skill"""
        skills = load_all_skills()
        self.assertIn("unit_cell_builder", skills)
        self.assertIn("sparam_optimizer", skills)

    def test_unit_cell_builder_meta(self):
        """Unit Cell Builder 元信息"""
        skills = load_all_skills()
        s = skills["unit_cell_builder"]
        self.assertEqual(s.name, "unit_cell_builder")
        self.assertIn("set_parameter", s.tools)
        self.assertIn("reflection_unit", s.scenarios)

    def test_sparam_optimizer_run(self):
        """SParam Optimizer 执行"""
        skills = load_all_skills()
        ctx = {"tool_registry": get_registry()}
        r = skills["sparam_optimizer"].run(ctx, params={"patch_length": 12.0}, targets={"freq_min_GHz": 2.4, "freq_max_GHz": 2.5, "s11_max_dB": -10.0})
        self.assertTrue(r["success"])
        self.assertIn("s11_min_dB", r)

    def test_get_skill_by_scenario(self):
        """按场景查找"""
        skills = load_all_skills()
        s = get_skill_by_scenario(skills, "s11_optimization")
        self.assertIsNotNone(s)
        self.assertEqual(s.name, "sparam_optimizer")


if __name__ == "__main__":
    unittest.main()
