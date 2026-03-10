"""
Orchestrator：串起 plan -> execute -> evaluate -> persist 完整流程。
支持换路线机制。
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from state import StateStore, TaskState, get_state_store
from state.models import RunPhase

from .evaluator import Evaluator
from .executor import Executor
from .models import EvaluationResult
from .planner import Planner
from .stop_policy import StopPolicy


class Orchestrator:
    """
    编排器。
    主循环：plan -> execute -> evaluate -> persist。
    支持 switch_route 换路线。
    """

    def __init__(
        self,
        planner: Optional[Planner] = None,
        executor: Optional[Executor] = None,
        evaluator: Optional[Evaluator] = None,
        stop_policy: Optional[StopPolicy] = None,
        state_store: Optional[StateStore] = None,
    ) -> None:
        self.planner = planner or Planner()
        self.executor = executor or Executor()
        self.evaluator = evaluator or Evaluator()
        self.stop_policy = stop_policy or StopPolicy()
        self.state_store = state_store or get_state_store()

    def run(
        self,
        task_id: str,
        project_path: str = "",
        initial_params: Optional[Dict[str, float]] = None,
        targets: Optional[Dict[str, Any]] = None,
        max_iterations: int = 10,
        resume: bool = True,
    ) -> Dict[str, Any]:
        """运行主循环。"""
        task = self._load_or_init_task(
            task_id, project_path, initial_params, targets, max_iterations, resume
        )
        if task is None:
            return {"success": False, "error": "无法加载或初始化任务"}

        evaluation: Optional[EvaluationResult] = None
        last_iteration = 0
        recent_scores: List[float] = []

        while True:
            if task.phase in (RunPhase.DONE, RunPhase.FAILED):
                break

            plan = self.planner.plan(
                task,
                suggest_route_change=evaluation.suggest_route_change if evaluation else False,
                no_improvement_count=evaluation.no_improvement_count if evaluation else 0,
            )

            if not plan.actions:
                if plan.route == "stop_route":
                    self.state_store.mark_task_done(task.task_id, success=False)
                    return self._build_result(task, evaluation, last_iteration, "路线停止")
                break

            results = self.executor.execute(plan)
            execution_failed = any(r.status.value == "failed" for r in results)

            evaluation = self.evaluator.evaluate(
                results, task.targets, task.current_params, recent_scores[-5:]
            )
            recent_scores.append(evaluation.score)

            iteration = task.current_iteration + 1
            last_iteration = iteration

            tried = list(task.tried_actions or [])
            tried.append({"route": plan.route, "params": dict(task.current_params)})
            if execution_failed:
                failed = list(task.failed_actions or [])
                failed.append({"route": plan.route, "params": dict(task.current_params)})
            else:
                failed = task.failed_actions or []

            best_route = task.best_route
            if not execution_failed and (best_route is None or evaluation.score > best_route.get("score", 0)):
                best_route = {
                    "structure_type": task.current_hypothesis.get("structure_type", "single_pec"),
                    "params": dict(task.current_params),
                    "score": evaluation.score,
                }

            self.state_store.save_iteration_record(
                task_id=task.task_id,
                iteration=iteration,
                params=task.current_params,
                result_snapshot=self._build_result_snapshot(results),
                evaluation={
                    "score": evaluation.score,
                    "all_ok": evaluation.all_ok,
                    "s_params_ok": evaluation.all_ok,
                    "details": evaluation.details,
                },
            )
            self.state_store.update_task_route_state(
                task_id,
                tried_actions=tried,
                failed_actions=failed,
                best_route=best_route,
            )

            if not execution_failed and evaluation.all_ok:
                self.state_store.save_best_result(
                    task.task_id, iteration, task.current_params,
                    evaluation.s11_min_dB, evaluation.freq_at_min_GHz, all_ok=True,
                )

            decision = self.stop_policy.decide(
                evaluation, iteration, task.max_iterations, execution_failed, task.current_hypothesis
            )

            if decision.should_stop:
                self.state_store.mark_task_done(
                    task.task_id, success=evaluation.all_ok and not execution_failed
                )
                return self._build_result(task, evaluation, iteration, decision.reason)

            if decision.switch_route and decision.next_route:
                hypothesis = dict(task.current_hypothesis or {})
                hypothesis["route"] = decision.next_route
                if decision.next_route == "switch_structure":
                    hypothesis["structure_type"] = "three_layer"
                self.state_store.update_task_route_state(task.task_id, current_hypothesis=hypothesis)
                params = task.best_route.get("params", task.current_params) if task.best_route else task.current_params
                self.state_store.update_task_params(task.task_id, params)
            else:
                self.state_store.update_task_params(task.task_id, evaluation.next_params)

            task = self.state_store.get_active_task()
            if task is None:
                return {"success": False, "error": "任务状态丢失"}

        return self._build_result(task, evaluation, last_iteration, "无动作")

    def _load_or_init_task(
        self,
        task_id: str,
        project_path: str,
        initial_params: Optional[Dict[str, float]],
        targets: Optional[Dict[str, Any]],
        max_iterations: int,
        resume: bool,
    ) -> Optional[TaskState]:
        if resume:
            active = self.state_store.get_active_task()
            if active and active.task_id == task_id and active.phase not in (RunPhase.DONE, RunPhase.FAILED):
                return active
        task = self.state_store.init_task(
            task_id=task_id,
            project_path=project_path,
            initial_params=initial_params,
            targets=targets,
            max_iterations=max_iterations,
        )
        if task:
            self.state_store.update_task_route_state(
                task_id,
                current_hypothesis={"route": "continue_tune", "structure_type": "single_pec"},
            )
        return self.state_store.get_active_task()

    def _build_result_snapshot(self, results: list) -> Dict[str, Any]:
        snapshot = {"success": True, "results": {}, "errors": []}
        for r in results:
            if r.tool_name == "read_s11" and r.status.value == "success":
                snapshot["results"]["s_params"] = {"success": True, "summary": r.data}
            if r.status.value == "failed":
                snapshot["success"] = False
                snapshot["errors"].append(r.error or r.message)
        return snapshot

    def _build_result(
        self,
        task: TaskState,
        evaluation: Optional[EvaluationResult],
        iteration: int,
        reason: str,
    ) -> Dict[str, Any]:
        eval_info = {}
        if evaluation:
            eval_info = {
                "score": evaluation.score,
                "s11_min_dB": evaluation.s11_min_dB,
                "freq_at_min_GHz": evaluation.freq_at_min_GHz,
            }
        return {
            "success": evaluation.all_ok if evaluation else False,
            "task_id": task.task_id,
            "iteration": iteration,
            "reason": reason,
            "final_params": task.current_params,
            "best_result": task.best_result.to_dict() if task.best_result else None,
            "best_route": task.best_route,
            "evaluation": eval_info,
        }
