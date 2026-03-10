"""
状态存储。
读写 run_state/ 目录，支持多轮迭代记录与中断恢复。
优先使用 JSON 文件，字段命名清晰。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import BestResultSummary, IterationRecord, RunPhase, RunState, TaskState


class StateStore:
    """状态存储"""

    ACTIVE_TASK_FILE = "active_task.json"

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else Path("run_state")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _active_path(self) -> Path:
        return self.base_dir / self.ACTIVE_TASK_FILE

    def _task_path(self, task_id: str) -> Path:
        return self.base_dir / f"{task_id}.json"

    # -----------------------------------------------------------------------
    # 任务状态管理
    # -----------------------------------------------------------------------

    def init_task(
        self,
        task_id: str,
        project_path: str = "",
        initial_params: Optional[Dict[str, float]] = None,
        targets: Optional[Dict[str, Any]] = None,
        max_iterations: int = 10,
        meta: Optional[Dict[str, Any]] = None,
    ) -> TaskState:
        """
        初始化任务状态。
        创建新 TaskState 并写入 active_task.json。
        """
        state = TaskState(
            task_id=task_id,
            phase=RunPhase.INIT,
            project_path=project_path or "",
            current_params=dict(initial_params or {}),
            targets=dict(targets or {}),
            max_iterations=max_iterations,
            iteration_records=[],
            best_result=None,
            current_iteration=0,
            meta=dict(meta or {}),
        )
        self._save_task_state(state)
        return state

    def get_active_task(self) -> Optional[TaskState]:
        """
        读取当前活动任务。
        用于中断恢复：加载 active_task.json，从 current_iteration 继续。
        """
        path = self._active_path()
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return TaskState.from_dict(json.load(f))
        except (json.JSONDecodeError, KeyError) as e:
            return None

    def save_iteration_record(
        self,
        task_id: str,
        iteration: int,
        params: Dict[str, float],
        result_snapshot: Dict[str, Any],
        evaluation: Dict[str, Any],
        ai_decision: Optional[Dict[str, Any]] = None,
    ) -> Optional[TaskState]:
        """
        保存每轮迭代记录。
        追加到 iteration_records，更新 current_params、current_iteration。
        若为活动任务则同步更新 active_task.json。
        """
        record = IterationRecord(
            iteration=iteration,
            params=params,
            result_snapshot=result_snapshot,
            evaluation=evaluation,
            ai_decision=ai_decision,
        )
        state = self._load_task_by_id_or_active(task_id)
        if state is None:
            return None
        state.iteration_records.append(record)
        state.current_params = params
        state.current_iteration = iteration
        state.phase = RunPhase.PARAM_UPDATE
        from datetime import datetime

        state.updated_at = datetime.now()
        self._save_task_state(state)
        return state

    def save_best_result(
        self,
        task_id: str,
        iteration: int,
        params: Dict[str, float],
        s11_min_dB: float,
        freq_at_min_GHz: float,
        bandwidth_10dB_MHz: float = 0.0,
        all_ok: bool = False,
    ) -> Optional[TaskState]:
        """
        保存当前最佳结果。
        仅当新结果优于已有 best_result 时更新（s11 更小为优）。
        """
        state = self._load_task_by_id_or_active(task_id)
        if state is None:
            return None
        best = BestResultSummary(
            iteration=iteration,
            params=params,
            s11_min_dB=s11_min_dB,
            freq_at_min_GHz=freq_at_min_GHz,
            bandwidth_10dB_MHz=bandwidth_10dB_MHz,
            all_ok=all_ok,
        )
        if state.best_result is None or s11_min_dB < state.best_result.s11_min_dB:
            state.best_result = best
            from datetime import datetime

            state.updated_at = datetime.now()
            self._save_task_state(state)
        return state

    def update_task_phase(self, task_id: str, phase: str) -> Optional[TaskState]:
        """更新任务阶段。phase 为 RunPhase.value 或 enum。"""
        state = self._load_task_by_id_or_active(task_id)
        if state is None:
            return None
        state.phase = RunPhase(phase) if isinstance(phase, str) else phase
        from datetime import datetime

        state.updated_at = datetime.now()
        self._save_task_state(state)
        return state

    def mark_task_done(self, task_id: str, success: bool = True) -> Optional[TaskState]:
        """标记任务完成。"""
        return self.update_task_phase(task_id, RunPhase.DONE.value if success else RunPhase.FAILED.value)

    def update_task_params(self, task_id: str, params: Dict[str, float]) -> Optional[TaskState]:
        """更新任务当前参数（用于下一轮迭代）。"""
        state = self._load_task_by_id_or_active(task_id)
        if state is None:
            return None
        state.current_params = dict(params)
        from datetime import datetime
        state.updated_at = datetime.now()
        self._save_task_state(state)
        return state

    def update_task_route_state(
        self,
        task_id: str,
        tried_actions: Optional[List[Dict[str, Any]]] = None,
        failed_actions: Optional[List[Dict[str, Any]]] = None,
        best_route: Optional[Dict[str, Any]] = None,
        current_hypothesis: Optional[Dict[str, Any]] = None,
    ) -> Optional[TaskState]:
        """更新路线相关状态（自由度扩展）。"""
        state = self._load_task_by_id_or_active(task_id)
        if state is None:
            return None
        if tried_actions is not None:
            state.tried_actions = list(tried_actions)
        if failed_actions is not None:
            state.failed_actions = list(failed_actions)
        if best_route is not None:
            state.best_route = dict(best_route)
        if current_hypothesis is not None:
            state.current_hypothesis = dict(current_hypothesis)
        from datetime import datetime
        state.updated_at = datetime.now()
        self._save_task_state(state)
        return state

    def _load_task_by_id_or_active(self, task_id: Optional[str]) -> Optional[TaskState]:
        """按 task_id 或 active 加载。task_id 存在则优先从 {task_id}.json 读，否则从 active 读。"""
        if task_id:
            path = self._task_path(task_id)
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return TaskState.from_dict(json.load(f))
                except (json.JSONDecodeError, KeyError):
                    pass
        active = self.get_active_task()
        if active and task_id and active.task_id != task_id:
            return None
        return active

    def _save_task_state(self, state: TaskState) -> Path:
        """保存 TaskState 到 active_task.json 及 {task_id}.json。"""
        data = state.to_dict()
        active_path = self._active_path()
        with open(active_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        task_path = self._task_path(state.task_id)
        with open(task_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return active_path

    # -----------------------------------------------------------------------
    # 兼容旧 RunState 接口
    # -----------------------------------------------------------------------

    def _path(self, run_id: str) -> Path:
        return self._task_path(run_id)

    def save(self, state: RunState) -> Path:
        """保存 RunState（兼容旧接口）"""
        path = self._path(state.run_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
        return path

    def load(self, run_id: str) -> Optional[RunState]:
        """加载 RunState（兼容旧接口）"""
        path = self._path(run_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return RunState.from_dict(json.load(f))

    def exists(self, run_id: str) -> bool:
        """检查 run_id 对应状态是否存在"""
        return self._path(run_id).exists()


# 默认实例
_store: Optional[StateStore] = None


def get_state_store(base_dir: Optional[Path] = None) -> StateStore:
    """获取状态存储实例"""
    global _store
    if _store is None:
        _store = StateStore(base_dir)
    return _store
