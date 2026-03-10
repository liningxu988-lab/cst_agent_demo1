"""
CST Tool 适配层最小测试。
使用 FakeCSTController 验证工具链，不依赖真实 CST。
"""

import unittest

from tools.base import ToolStatus
from tools.cst_context import clear_controller, set_controller
from tools.registry import get_registry


class TestCSTTools(unittest.TestCase):
    """CST 工具适配层测试"""

    def setUp(self):
        from scripts.cst_controller import FakeCSTController

        self.fake = FakeCSTController()
        self.fake.connect()
        set_controller(self.fake)

    def tearDown(self):
        clear_controller()

    def test_open_project(self):
        """open_project 工具"""
        reg = get_registry()
        res = reg.run("open_project", project_path="test.cst")
        self.assertEqual(res.status, ToolStatus.SUCCESS)
        self.assertTrue(res.data.get("opened"))

    def test_set_parameter(self):
        """set_parameter 工具"""
        reg = get_registry()
        res = reg.run("set_parameter", params={"patch_length": 12.0, "patch_width": 10.0})
        self.assertEqual(res.status, ToolStatus.SUCCESS)
        self.assertIn("patch_length", res.data.get("params", {}))

    def test_run_solver(self):
        """run_solver 工具"""
        reg = get_registry()
        res = reg.run("run_solver", wait_complete=True, timeout=5)
        self.assertEqual(res.status, ToolStatus.SUCCESS)

    def test_read_s11(self):
        """read_s11 工具"""
        reg = get_registry()
        res = reg.run("read_s11")
        self.assertEqual(res.status, ToolStatus.SUCCESS)
        self.assertIn("s11_min_dB", res.data)
        self.assertIn("freq_at_min_GHz", res.data)

    def test_full_chain(self):
        """完整调用链：open -> set -> run -> read"""
        reg = get_registry()
        r1 = reg.run("open_project", project_path="test.cst")
        self.assertEqual(r1.status, ToolStatus.SUCCESS)

        r2 = reg.run("set_parameter", params={"patch_length": 12.0})
        self.assertEqual(r2.status, ToolStatus.SUCCESS)

        r3 = reg.run("run_solver", wait_complete=True, timeout=5)
        self.assertEqual(r3.status, ToolStatus.SUCCESS)

        r4 = reg.run("read_s11")
        self.assertEqual(r4.status, ToolStatus.SUCCESS)
        self.assertIsNotNone(r4.data.get("s11_min_dB"))

    def test_tool_without_controller(self):
        """未注入控制器时返回 FAILED"""
        clear_controller()
        reg = get_registry()
        res = reg.run("open_project", project_path="test.cst")
        self.assertEqual(res.status, ToolStatus.FAILED)
        self.assertIn("controller", res.error or "")


if __name__ == "__main__":
    unittest.main()
