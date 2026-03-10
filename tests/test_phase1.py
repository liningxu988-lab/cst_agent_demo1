"""
Phase 1 最小测试用例。
运行: python -m tests.test_phase1
"""

import tempfile
import unittest
from pathlib import Path


class TestPhase1(unittest.TestCase):
    """Phase 1 模块测试"""

    def test_tool_result_roundtrip(self):
        """ToolResult 序列化/反序列化"""
        from tools.base import ToolResult, ToolStatus

        r = ToolResult(
            status=ToolStatus.SUCCESS,
            tool_name="test_tool",
            message="ok",
            data={"key": "value"},
        )
        d = r.to_dict()
        r2 = ToolResult.from_dict(d)
        self.assertEqual(r2.status, r.status)
        self.assertEqual(r2.tool_name, r.tool_name)
        self.assertEqual(r2.data, r.data)

    def test_tool_registry(self):
        """ToolRegistry 注册与调用"""
        from tools.base import BaseTool, ToolResult, ToolStatus
        from tools.registry import get_registry

        class DummyTool(BaseTool):
            name = "dummy"

            def run(self, **kwargs):
                return ToolResult(ToolStatus.SUCCESS, self.name, data=kwargs)

        reg = get_registry()
        reg.register(DummyTool())
        self.assertIn("dummy", reg.list_tools())
        res = reg.run("dummy", x=1)
        self.assertEqual(res.status, ToolStatus.SUCCESS)
        self.assertEqual(res.data.get("x"), 1)

        res_missing = reg.run("nonexistent")
        self.assertEqual(res_missing.status, ToolStatus.FAILED)

    def test_run_state_roundtrip(self):
        """RunState 序列化/反序列化"""
        from state.models import RunPhase, RunState

        state = RunState(
            run_id="test_001",
            phase=RunPhase.PARAM_SET,
            params={"a": 1},
            targets={"s11_max_dB": -10},
            current_iteration=2,
        )
        d = state.to_dict()
        state2 = RunState.from_dict(d)
        self.assertEqual(state2.run_id, state.run_id)
        self.assertEqual(state2.phase, state.phase)
        self.assertEqual(state2.params, state.params)
        self.assertEqual(state2.current_iteration, state.current_iteration)

    def test_state_store(self):
        """StateStore 读写"""
        from state.models import RunPhase, RunState
        from state.state_store import StateStore

        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(Path(tmp))
            state = RunState(run_id="store_test", phase=RunPhase.INIT, params={})
            path = store.save(state)
            self.assertTrue(path.exists())
            loaded = store.load("store_test")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.run_id, state.run_id)

    def test_design_task(self):
        """DesignTask 与 AgentDecision"""
        from domain.task_models import AgentDecision, DesignParams, DesignTarget, DesignTask

        task = DesignTask(
            task_id="t1",
            params=DesignParams(params={"patch_length": 12.0}),
            targets=DesignTarget(freq_min_GHz=2.4, freq_max_GHz=2.5, s11_max_dB=-10),
        )
        self.assertEqual(task.params.to_dict()["patch_length"], 12.0)
        self.assertEqual(task.targets.freq_min_GHz, 2.4)

        dec = AgentDecision(action="update_params", params={"patch_length": 11.0}, reason="tune")
        self.assertEqual(dec.action, "update_params")
        self.assertEqual(dec.params["patch_length"], 11.0)


if __name__ == "__main__":
    unittest.main()
