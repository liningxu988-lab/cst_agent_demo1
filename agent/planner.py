"""
Planner：根据历史与状态在多个策略间选择，生成结构化 ActionPlan。
支持：继续微调、切换结构、参数扫描（预留）、停止路线。
"""

from typing import List

from .models import Action, ActionPlan
from state import RunPhase, TaskState


class Planner:
    """
    规划器。
    根据 tried_actions、failed_actions、current_hypothesis、evaluation 建议
    选择策略并生成动作序列。不直接执行工具。
    """

    ROUTES = ("continue_tune", "switch_structure", "param_sweep", "stop_route")
    ALLOWED_TOOLS = {"open_project", "set_parameter", "run_solver", "read_s11"}

    def plan(
        self,
        task_state: TaskState,
        suggest_route_change: bool = False,
        no_improvement_count: int = 0,
    ) -> ActionPlan:
        """
        根据任务状态与评估建议生成执行计划。

        Args:
            task_state: 当前任务状态
            suggest_route_change: evaluator 建议换路线
            no_improvement_count: 连续无改善轮数

        Returns:
            ActionPlan: 含 route 与 actions
        """
        phase = task_state.phase
        hypothesis = task_state.current_hypothesis or {}
        route = hypothesis.get("route", "continue_tune")
        structure_type = hypothesis.get("structure_type", "single_pec")

        # 仅当处于 continue_tune 时根据建议换路线；若已为 switch_structure 则执行切换
        if suggest_route_change and no_improvement_count >= 2 and route == "continue_tune":
            if structure_type == "single_pec":
                route = "switch_structure"
                structure_type = "three_layer"
            else:
                route = "stop_route"

        actions: List[Action] = []

        if route == "stop_route":
            return ActionPlan(actions=[], route="stop_route")

        if phase == RunPhase.INIT:
            if task_state.project_path:
                actions.append(Action("open_project", {"project_path": task_state.project_path}))
            actions.append(Action("set_parameter", {"params": task_state.current_params}))
            actions.append(Action("run_solver", {"wait_complete": True}))
            actions.append(Action("read_s11", {}))
            return ActionPlan(actions=actions, route="continue_tune")

        if route == "switch_structure":
            params = dict(task_state.current_params)
            params["structure_type"] = structure_type
            if structure_type == "three_layer":
                params.setdefault("substrate_height", 1.6)
                params.setdefault("dielectric_er", 4.4)
            actions.append(Action("set_parameter", {"params": params}))
            actions.append(Action("run_solver", {"wait_complete": True}))
            actions.append(Action("read_s11", {}))
            return ActionPlan(actions=actions, route="switch_structure")

        if route == "param_sweep":
            # 预留：参数扫描，最小实现同 continue_tune
            actions.append(Action("set_parameter", {"params": task_state.current_params}))
            actions.append(Action("run_solver", {"wait_complete": True}))
            actions.append(Action("read_s11", {}))
            return ActionPlan(actions=actions, route="param_sweep")

        # continue_tune
        actions.append(Action("set_parameter", {"params": task_state.current_params}))
        actions.append(Action("run_solver", {"wait_complete": True}))
        actions.append(Action("read_s11", {}))
        return ActionPlan(actions=actions, route="continue_tune")
