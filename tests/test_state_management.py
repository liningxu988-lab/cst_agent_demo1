"""
任务状态管理层测试。
"""

import tempfile
import unittest
from pathlib import Path

from state import (
    BestResultSummary,
    IterationRecord,
    RunPhase,
    StateStore,
    TaskState,
    get_state_store,
)


class TestStateManagement(unittest.TestCase):
    """任务状态管理测试"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = StateStore(Path(self.tmp))

    def test_init_task(self):
        """初始化任务状态"""
        task = self.store.init_task(
            task_id="run_001",
            project_path="templates/test.cst",
            initial_params={"patch_length": 12.0},
            targets={"freq_min_GHz": 2.4, "s11_max_dB": -10.0},
            max_iterations=10,
        )
        self.assertEqual(task.task_id, "run_001")
        self.assertEqual(task.phase, RunPhase.INIT)
        self.assertEqual(task.current_params["patch_length"], 12.0)
        self.assertEqual(task.current_iteration, 0)

    def test_get_active_task(self):
        """读取活动任务"""
        self.store.init_task(task_id="run_002", initial_params={"a": 1})
        active = self.store.get_active_task()
        self.assertIsNotNone(active)
        self.assertEqual(active.task_id, "run_002")

    def test_save_iteration_record(self):
        """保存迭代记录"""
        self.store.init_task(task_id="run_003", initial_params={"x": 1})
        self.store.save_iteration_record(
            task_id="run_003",
            iteration=1,
            params={"x": 2},
            result_snapshot={"success": True, "results": {}, "errors": []},
            evaluation={"s_params_ok": True, "all_ok": False, "details": {}},
        )
        active = self.store.get_active_task()
        self.assertEqual(len(active.iteration_records), 1)
        self.assertEqual(active.iteration_records[0].params["x"], 2)
        self.assertEqual(active.current_iteration, 1)

    def test_save_best_result(self):
        """保存最佳结果"""
        self.store.init_task(task_id="run_004", initial_params={})
        self.store.save_best_result(
            task_id="run_004",
            iteration=1,
            params={"p": 10},
            s11_min_dB=-12.0,
            freq_at_min_GHz=2.45,
            all_ok=True,
        )
        active = self.store.get_active_task()
        self.assertIsNotNone(active.best_result)
        self.assertEqual(active.best_result.s11_min_dB, -12.0)

    def test_save_best_result_only_improves(self):
        """最佳结果仅在新结果更优时更新"""
        self.store.init_task(task_id="run_005", initial_params={})
        self.store.save_best_result(
            task_id="run_005",
            iteration=1,
            params={"p": 10},
            s11_min_dB=-12.0,
            freq_at_min_GHz=2.45,
        )
        self.store.save_best_result(
            task_id="run_005",
            iteration=2,
            params={"p": 11},
            s11_min_dB=-8.0,
            freq_at_min_GHz=2.45,
        )
        active = self.store.get_active_task()
        self.assertEqual(active.best_result.s11_min_dB, -12.0)
        self.assertEqual(active.best_result.iteration, 1)

    def test_interrupt_recovery(self):
        """中断恢复：从 current_iteration 继续"""
        self.store.init_task(task_id="run_006", initial_params={"v": 1})
        self.store.save_iteration_record(
            task_id="run_006",
            iteration=1,
            params={"v": 2},
            result_snapshot={"success": True, "results": {}, "errors": []},
            evaluation={"all_ok": False, "details": {}},
        )
        recovered = self.store.get_active_task()
        self.assertEqual(recovered.current_iteration, 1)
        self.assertEqual(recovered.current_params["v"], 2)

    def test_mark_task_done(self):
        """标记任务完成"""
        self.store.init_task(task_id="run_007", initial_params={})
        self.store.mark_task_done(task_id="run_007", success=True)
        active = self.store.get_active_task()
        self.assertEqual(active.phase, RunPhase.DONE)


if __name__ == "__main__":
    unittest.main()
