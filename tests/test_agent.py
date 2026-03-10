"""
Agent 主循环最小测试。
"""

import tempfile
import unittest
from pathlib import Path

from tools import set_controller, get_registry
from scripts.cst_controller import FakeCSTController
from agent import Orchestrator, Planner, Executor, Evaluator, StopPolicy
from agent.models import Action, ActionPlan, EvaluationResult
from state import StateStore


class TestAgent(unittest.TestCase):
    """Agent 模块测试"""

    def setUp(self):
        ctrl = FakeCSTController()
        ctrl.connect()
        set_controller(ctrl)
        self.tmp = tempfile.mkdtemp()

    def test_planner_init_phase(self):
        """Planner INIT 阶段生成完整动作链"""
        from state import TaskState
        from state.models import RunPhase

        task = TaskState(
            task_id="t1",
            phase=RunPhase.INIT,
            project_path="test.cst",
            current_params={"patch_length": 12.0},
            targets={"freq_min_GHz": 2.4},
        )
        plan = Planner().plan(task)
        self.assertEqual(len(plan.actions), 4)
        self.assertEqual(plan.actions[0].tool, "open_project")
        self.assertEqual(plan.actions[1].tool, "set_parameter")
        self.assertEqual(plan.actions[2].tool, "run_solver")
        self.assertEqual(plan.actions[3].tool, "read_s11")

    def test_executor(self):
        """Executor 执行计划"""
        plan = ActionPlan(actions=[Action("set_parameter", {"params": {"x": 1}})])
        results = Executor().execute(plan)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].tool_name, "set_parameter")

    def test_evaluator(self):
        """Evaluator 评分"""
        from tools.base import ToolResult, ToolStatus

        results = [
            ToolResult(
                ToolStatus.SUCCESS,
                "read_s11",
                data={"s11_min_dB": -12.0, "freq_at_min_GHz": 2.45},
            ),
        ]
        ev = Evaluator().evaluate(results, {"freq_min_GHz": 2.4, "freq_max_GHz": 2.5, "s11_max_dB": -10.0})
        self.assertTrue(ev.all_ok)
        self.assertGreater(ev.score, 0)

    def test_evaluator_no_improvement(self):
        """Evaluator 连续无改善检测"""
        from tools.base import ToolResult, ToolStatus

        results = [
            ToolResult(ToolStatus.SUCCESS, "read_s11", data={"s11_min_dB": -8, "freq_at_min_GHz": 2.45}),
        ]
        recent = [55.0, 54.0, 53.0]
        ev = Evaluator().evaluate(results, {"freq_min_GHz": 2.4, "freq_max_GHz": 2.5, "s11_max_dB": -10.0}, recent_scores=recent)
        self.assertTrue(ev.suggest_route_change)
        self.assertGreaterEqual(ev.no_improvement_count, 3)

    def test_stop_policy(self):
        """StopPolicy 判断"""
        ev_ok = EvaluationResult(score=90, all_ok=True, s11_min_dB=-12, freq_at_min_GHz=2.45)
        ev_not = EvaluationResult(score=50, all_ok=False, s11_min_dB=-8, freq_at_min_GHz=2.45)
        policy = StopPolicy()
        self.assertTrue(policy.should_stop(ev_ok, 1, 10).should_stop)
        self.assertFalse(policy.should_stop(ev_not, 1, 10).should_stop)
        self.assertTrue(policy.should_stop(ev_not, 10, 10).should_stop)

    def test_stop_policy_switch_route(self):
        """StopPolicy 换路线决策"""
        ev = EvaluationResult(score=30, all_ok=False, s11_min_dB=-8, freq_at_min_GHz=2.45, suggest_route_change=True)
        policy = StopPolicy()
        d = policy.decide(ev, 5, 10, current_hypothesis={"route": "continue_tune", "structure_type": "single_pec"})
        self.assertTrue(d.switch_route)
        self.assertEqual(d.next_route, "switch_structure")

    def test_orchestrator_one_iteration(self):
        """Orchestrator 单轮运行"""
        store = StateStore(Path(self.tmp))
        orch = Orchestrator(state_store=store)
        result = orch.run(
            task_id="test_run",
            project_path="x.cst",
            initial_params={"patch_length": 12.0, "patch_width": 10.0},
            targets={"freq_min_GHz": 2.4, "freq_max_GHz": 2.5, "s11_max_dB": -10.0},
            max_iterations=1,
            resume=False,
        )
        self.assertIn("task_id", result)
        self.assertIn("iteration", result)


if __name__ == "__main__":
    unittest.main()
