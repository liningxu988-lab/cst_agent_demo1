"""
运行状态数据模型。
所有状态写入 run_state/，支持多轮迭代记录与中断恢复。
与 CST 单元优化任务兼容。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class RunPhase(str, Enum):
    """运行阶段"""
    INIT = "init"
    PARAM_SET = "param_set"
    SIM_RUN = "sim_run"
    RESULT_READ = "result_read"
    AI_ANALYZE = "ai_analyze"
    PARAM_UPDATE = "param_update"
    DONE = "done"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# 迭代记录与最佳结果
# ---------------------------------------------------------------------------


@dataclass
class BestResultSummary:
    """当前最佳结果摘要。用于中断恢复时快速获取最优参数。"""
    iteration: int
    params: Dict[str, float]
    s11_min_dB: float
    freq_at_min_GHz: float
    bandwidth_10dB_MHz: float = 0.0
    all_ok: bool = False
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration": self.iteration,
            "params": self.params,
            "s11_min_dB": self.s11_min_dB,
            "freq_at_min_GHz": self.freq_at_min_GHz,
            "bandwidth_10dB_MHz": self.bandwidth_10dB_MHz,
            "all_ok": self.all_ok,
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BestResultSummary":
        return cls(
            iteration=int(d.get("iteration", 0)),
            params=dict(d.get("params", {})),
            s11_min_dB=float(d.get("s11_min_dB", 0)),
            freq_at_min_GHz=float(d.get("freq_at_min_GHz", 0)),
            bandwidth_10dB_MHz=float(d.get("bandwidth_10dB_MHz", 0)),
            all_ok=bool(d.get("all_ok", False)),
            updated_at=datetime.fromisoformat(d["updated_at"]) if d.get("updated_at") else datetime.now(),
        )


@dataclass
class IterationRecord:
    """
    单轮迭代记录。
    与 cst_runner 的 iteration_record 结构兼容。
    """
    iteration: int
    params: Dict[str, float]
    result_snapshot: Dict[str, Any]
    evaluation: Dict[str, Any]
    ai_decision: Optional[Dict[str, Any]] = None
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration": self.iteration,
            "params": self.params,
            "result_snapshot": self.result_snapshot,
            "evaluation": self.evaluation,
            "ai_decision": self.ai_decision,
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "IterationRecord":
        return cls(
            iteration=int(d.get("iteration", 0)),
            params=dict(d.get("params", {})),
            result_snapshot=dict(d.get("result_snapshot", {})),
            evaluation=dict(d.get("evaluation", {})),
            ai_decision=d.get("ai_decision"),
            updated_at=datetime.fromisoformat(d["updated_at"]) if d.get("updated_at") else datetime.now(),
        )


@dataclass
class TaskState:
    """
    任务状态。
    支持多轮迭代记录、最佳结果追踪、中断恢复。
    扩展：tried_actions、failed_actions、best_route、current_hypothesis 以支持多路线决策。
    """
    task_id: str
    phase: RunPhase
    project_path: str = ""
    current_params: Dict[str, float] = field(default_factory=dict)
    targets: Dict[str, Any] = field(default_factory=dict)
    max_iterations: int = 10
    iteration_records: List[IterationRecord] = field(default_factory=list)
    best_result: Optional[BestResultSummary] = None
    current_iteration: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    meta: Dict[str, Any] = field(default_factory=dict)
    # 自由度扩展
    tried_actions: List[Dict[str, Any]] = field(default_factory=list)
    failed_actions: List[Dict[str, Any]] = field(default_factory=list)
    best_route: Optional[Dict[str, Any]] = None
    current_hypothesis: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "phase": self.phase.value,
            "project_path": self.project_path,
            "current_params": self.current_params,
            "targets": self.targets,
            "max_iterations": self.max_iterations,
            "iteration_records": [r.to_dict() for r in self.iteration_records],
            "best_result": self.best_result.to_dict() if self.best_result else None,
            "current_iteration": self.current_iteration,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "meta": self.meta,
            "tried_actions": self.tried_actions,
            "failed_actions": self.failed_actions,
            "best_route": self.best_route,
            "current_hypothesis": self.current_hypothesis,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TaskState":
        best = d.get("best_result")
        return cls(
            task_id=str(d.get("task_id", "unknown")),
            phase=RunPhase(d.get("phase", "init")),
            project_path=str(d.get("project_path", "")),
            current_params=dict(d.get("current_params", {})),
            targets=dict(d.get("targets", {})),
            max_iterations=int(d.get("max_iterations", 10)),
            iteration_records=[IterationRecord.from_dict(r) for r in d.get("iteration_records", [])],
            best_result=BestResultSummary.from_dict(best) if best else None,
            current_iteration=int(d.get("current_iteration", 0)),
            created_at=datetime.fromisoformat(d["created_at"]) if d.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(d["updated_at"]) if d.get("updated_at") else datetime.now(),
            meta=dict(d.get("meta", {})),
            tried_actions=list(d.get("tried_actions", [])),
            failed_actions=list(d.get("failed_actions", [])),
            best_route=d.get("best_route"),
            current_hypothesis=dict(d.get("current_hypothesis", {})),
        )


# ---------------------------------------------------------------------------
# 兼容旧 RunState / IterationState（保留供迁移）
# ---------------------------------------------------------------------------


@dataclass
class IterationState:
    """单次迭代状态（旧模型，保留兼容）"""
    iteration: int
    phase: RunPhase
    params: Dict[str, Any] = field(default_factory=dict)
    result_data: Optional[Dict[str, Any]] = None
    ai_message: Optional[str] = None
    error: Optional[str] = None
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class RunState:
    """完整运行状态（旧模型，保留兼容）"""
    run_id: str
    phase: RunPhase
    params: Dict[str, Any] = field(default_factory=dict)
    targets: Dict[str, Any] = field(default_factory=dict)
    iterations: List[IterationState] = field(default_factory=list)
    current_iteration: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "phase": self.phase.value,
            "params": self.params,
            "targets": self.targets,
            "iterations": [
                {
                    "iteration": it.iteration,
                    "phase": it.phase.value,
                    "params": it.params,
                    "result_data": it.result_data,
                    "ai_message": it.ai_message,
                    "error": it.error,
                    "updated_at": it.updated_at.isoformat(),
                }
                for it in self.iterations
            ],
            "current_iteration": self.current_iteration,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RunState":
        return cls(
            run_id=d.get("run_id", "unknown"),
            phase=RunPhase(d.get("phase", "init")),
            params=d.get("params", {}),
            targets=d.get("targets", {}),
            iterations=[
                IterationState(
                    iteration=it.get("iteration", 0),
                    phase=RunPhase(it.get("phase", "init")),
                    params=it.get("params", {}),
                    result_data=it.get("result_data"),
                    ai_message=it.get("ai_message"),
                    error=it.get("error"),
                    updated_at=datetime.fromisoformat(it["updated_at"]) if it.get("updated_at") else datetime.now(),
                )
                for it in d.get("iterations", [])
            ],
            current_iteration=d.get("current_iteration", 0),
            created_at=datetime.fromisoformat(d["created_at"]) if d.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(d["updated_at"]) if d.get("updated_at") else datetime.now(),
            meta=d.get("meta", {}),
        )
